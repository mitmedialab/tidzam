import numpy as np
import math
import sys, optparse
import glob, os
from datetime import *
import time

import tensorflow as tf
import tflearn
import importlib

import vizualisation as vizu
import data as tiddata

print("TensorFlow "+ tf.__version__)

config = tflearn.config.init_graph (
    num_cores=1,
    gpu_memory_fraction=0.75,
    soft_placement=False)

class Classifier:
    def __init__(self,folder):
        self.dataw = 150
        self.datah = 186
        self.nn_folder = folder
        self.label_dic = np.load(folder + "/labels.dic.npy").astype(str)

        # Get Neural Net name
        path = self.nn_folder.split('/')
        name_file = path[len(path) - 1 ]
        if name_file == '':
            name_file = path[len(path) - 2 ]

        # import the model
        sys.path.append('./')
        exec("import "+self.nn_folder.replace("/",".")+".model as model")

        # Create a new graph and load it in a new session
        g = tf.Graph()
        with g.as_default() as g:
            network = eval("model.DNN([self.dataw, self.datah], len(self.label_dic))")
            self.name = network.name

            with tf.Session( graph = g ) as sess:
                self.classifier = tflearn.DNN(network.out,
                    tensorboard_dir= self.nn_folder + "/",
                    tensorboard_verbose=0)

                sess.run(tf.global_variables_initializer())

        try:
            print('Loading : ' + self.nn_folder + "." + network.name)
            self.classifier.load(self.nn_folder + "/" + network.name, create_new_session=False)

            # Add Softmax layer for decision function
            self.classifier.net = tflearn.activations.softmax (self.classifier.net)
            self.classifier.predictor = tflearn.Evaluator([self.classifier.net],
                                   session=self.classifier.session,model=None)
        except:
            print('Unable to load model: ' + self.nn_folder)
            quit()

class Analyzer:
    def __init__(self, nn_folder,session=False, callable_objects=[]):
        self.nn_folder = nn_folder
        self.count_run = -1
        self.old_stream = ""
        self.callable_objects = callable_objects
        self.load()


    # Load the network
    def load(self):
        # For each neural network
        self.classifiers = []
        for f in glob.glob(self.nn_folder + "/*"):
            if os.path.isdir(f) and "__pycache__" not in f :
                self.classifiers.append(Classifier(f))

        if len(self.classifiers) < 1:
            print("No classifier found in: " + self.nn_folder)
            quit()

    # Function called by the streamer to predic its current sample
    def execute(self, Sxxs, fs, t, sound_obj, overlap=0.5, stream=None):

        # Compute GMT Timestamp for current sampe
        self.count_run = self.count_run + 1
        # From Real-Time Stream
        if stream == "rt":
            stream = time.strftime("generated/today-%Y-%m-%d-%H-%M-%S.ogg")
            time_relative = "0:0:0:0ms"
            if stream == self.old_stream:
                time_relative = "0:0:0:500ms"
            self.old_stream = stream

        # From audio file, compute relative time from beginning
        else:
            time_relative = str(int(self.count_run * 0.5 * (1-overlap) / 3600)) + ":" + \
                    str( int((self.count_run * 0.5 * (1-overlap) % 3600)/60)) + ":" + \
                    str( int(self.count_run * 0.5 * (1-overlap) % 3600 % 60)) + ":" + \
                    str( int( ((self.count_run * 0.5 * (1-overlap) % 3600 % 60) * 1000) % 1000) ) + "ms"

        # Extract the datetime from the filename
        date = stream.split("/")
        date = date[len(date)-1].split(".")[0].split("-")
        date.pop(0)
        date = ''.join(date)
        date = datetime.strptime(date, "%Y%m%d%H%M%S")
        sample_time = time_relative.replace("ms","").split(":")
        sample_time = timedelta(
                hours=int(sample_time[0]),
                minutes=int(sample_time[1]),
                seconds=int(sample_time[2]),
                milliseconds=int(sample_time[3]))
        sample_timestamp = (date + sample_time).isoformat()

        print("----------------------------------- " + sample_timestamp)

        classes = []
        label_dic = []
        res = []
        # GENERAL CLASSIFIER
        for nn in self.classifiers:
            if nn.name == 'selector':
                res       = nn.classifier.predict(Sxxs)
                label_dic += list(nn.label_dic)
                for channel in range(0, Sxxs.shape[0]):
                    out_classes = ""
                    a = np.argmax(res[channel])
                    if res[channel][a] > 0.5: # If the neural network is confiant more than 50%
                        out_classes = str(nn.label_dic[a])
                    else:
                        out_classes = 'unknow'
                    classes.append(out_classes)
                break

        # EXPERT CLASSIFIER
        for channel in range(0, Sxxs.shape[0]):
            for nn in self.classifiers:
                # Complete the dictionnary with other classifier
                if nn.name != 'selector' and channel == 0:
                    label_dic += list(nn.label_dic)

                # Request the expert classifier for the detected classe
                pred = classes[channel].split('-')
                if nn.name == pred[0]:
                    res_expert = nn.classifier.predict([Sxxs[channel,:]])[0]
                    res[channel] += list(res_expert)
                    a = np.argmax(res_expert)
                    if  res_expert[a] > 0.5:
                        classes[channel] = classes[channel] + '-' + str(nn.label_dic[ a ]) #+ ' ('  + str(a) + ')'

                # Fill in with zeros for all other expert classifiers
                else:
                    res[channel] += list(np.zeros(len(nn.label_dic)) )
            print( "channel " + str(channel) + ' | ' + classes[channel])

        # BUILD AND TRANSMIT RESULT
        for obj in self.callable_objects:
            obj.execute(res, classes, label_dic, sound_obj, sample_timestamp)

if __name__ == "__main__":
    usage = 'analyzer.py --nn=build/test --stream=stream.wav [--show, -h]'
    parser = optparse.OptionParser(usage=usage)
    parser.set_defaults(stream=False,dic=False,nn="build/default")

    parser.add_option("-s", "--stream", action="store", type="string", dest="stream",
        default=None,
        help="Input audio stream to analyze.")

    parser.add_option("-j", "--jack", action="store", type="string", dest="jack",
        default=None,
        help="Input audio stream from Jack audio mixer to analyze.")

    parser.add_option("-n", "--nn", action="store", type="string", dest="nn",
        help="Neural Network session to load.")

    parser.add_option("-o", "--out", action="store", type="string", dest="out",
        default=None,
        help="Output folder for audio sound extraction.")

    parser.add_option("--show", action="store_true", dest="show", default=False,
        help="Play the audio samples and show their spectrogram.")

    (opts, args) = parser.parse_args()



    if (opts.stream or opts.jack) and opts.nn:
        callable_objects = []
        if opts.out is not None:
            if opts.stream is not None:
                # Build folder to store wav file
                a = opts.stream.split('/')
                a = a[len(a)-1].split('.')[0]
                wav_folder = opts.out + '/' + a + '/'
            else:
                wav_folder = opts.out

            import connector_SampleExtractor as SampleExtractor
            extractor = SampleExtractor.SampleExtractor(['birds', 'cricket', 'nothing', 'rain'], wav_folder)
            callable_objects.append(extractor)

        import connector_socketio as socketio
        socket = socketio.create_socket("/")
        callable_objects.append(socket)

        analyzer = Analyzer(opts.nn, callable_objects=callable_objects)

        callable_objects = []
        callable_objects.append(analyzer)

        if opts.show is True:
            import analyzer_vizualizer as tv
            vizu     = tv.TidzamVizualizer()
            callable_objects.append(vizu)

        if opts.stream is not None:
            import input_audiofile as ca
            connector = ca.TidzamAudiofile(opts.stream,
                callable_objects = callable_objects,  overlap=0)

        elif opts.jack is not None:
            import input_jack as cj
            connector = cj.TidzamJack(opts.jack, callable_objects=callable_objects)

        connector.start()
        socket.start()
    else:
        print(parser.usage)
