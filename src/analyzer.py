import numpy as np
import math
import sys, optparse
import glob, os

import soundfile as sf
import tensorflow as tf
import tflearn

import vizualisation as vizu
import models.vgg as models
import data as tiddata
from models import *

import sounddevice as sd

config = tflearn.config.init_graph (
    num_cores=1,
    gpu_memory_fraction=0.75,
    soft_placement=False)

class Classifier:
    def __init__(self,folder):
        self.dataw = 150
        self.datah = 186
        self.nn_folder = folder
        self.label_dic = np.load(folder + "/labels.dic.npy")

        # Get Neural Net name
        path = self.nn_folder.split('/')
        name_file = path[len(path) - 1 ]
        if name_file == '':
            name_file = path[len(path) - 2 ]

        # Create a new graph and load it in a new session
        g = tf.Graph()
        with g.as_default() as g:
            network = eval( name_file + ".DNN([self.dataw, self.datah], len(self.label_dic))")
            self.name = network.name

            with tf.Session( graph = g ) as sess:
                self.classifier = tflearn.DNN(network.out,
                    tensorboard_dir= self.nn_folder + "/",
                    tensorboard_verbose=0)

                sess.run(tf.global_variables_initializer())

        try:
            print('Loading : ' + self.nn_folder + "." + network.name)
            self.classifier.load(self.nn_folder + "/" + network.name, create_new_session=False)
        except:
            print('Unable to load model: ' + self.nn_folder)
            quit()

class Analyzer:
    def __init__(self, nn_folder,session=False, wav_folder="wav/"):
        self.nn_folder = nn_folder
        self.count_run = -1
        self.wav_folder = wav_folder
        self.load()

        print("WAV destination folder: " + wav_folder)

    # Load the network
    def load(self):
        # For each neural network
        self.classifiers = []
        for f in glob.glob(self.nn_folder + "/*"):
            self.classifiers.append(Classifier(f))

    # Function called by the streamer to predic its current sample
    def execute(self, Sxxs, fs, t, sound_obj, overlap=0.5):

        self.count_run = self.count_run + 1
        time = str(int(self.count_run * 0.5 * (1-overlap) / 3600)) + ":" + \
                str( int(self.count_run * 0.5 * (1-overlap) % 3600)/60) + ":" + \
                str( int(self.count_run * 0.5 * (1-overlap) % 3600 % 60)) + ":" + \
                str( int( ((self.count_run * 0.5 * (1-overlap) % 3600 % 60) * 1000) % 1000) ) + "ms"
        print("----------------------------------- " + time)

        classes = []
        for nn in self.classifiers:
            if nn.name == 'selector':
                res = nn.classifier.predict(Sxxs)
                for channel in range(0, Sxxs.shape[0]):
                    a = np.max(res[channel])

                    #if np.abs(a / np.mean(res[channel])) > 2 and a > 0:
                    #if np.abs(a) < 0.5:
                    if a > 0:
                        classes.append(str(nn.label_dic[ np.argmax(res[channel]) ]) ) #+ '-'+str(a))
                    else:
                        classes.append('unknow')
                    #    classes.append('unknow-') #+str(a))
                break

        for channel in range(0, Sxxs.shape[0]):
#            for nn in self.classifiers:
#                pred = classes[channel].split('-')
#                if nn.name == pred[0]:
#                    res = nn.classifier.predict([Sxxs[channel,:]])
#                    a = np.max(res)
#                    if  np.abs(a) < 0.5:
#                        classes[channel] = classes[channel] + '-' + str(nn.label_dic[ np.argmax(res) ]) #+ ' ('  + str(a) + ')'
#                    else:
#                        classes[channel] = classes[channel] + '-unknow ' #+ '(' + str(a) + ')'
#                    break

            print( "channel " + str(channel) + ' | ' + classes[channel])

            if classes[channel] == 'birds':
                sf.write (self.wav_folder + '/+' + classes[channel] + '(' + str(channel) + ')_' + time +'.wav',
                    sound_obj[0][:,channel], sound_obj[1])
#            # Save the file on the disk

#
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
        default="/tmp/wav",
        help="Output folder for audio sound extraction.")

    parser.add_option("--show", action="store_true", dest="show", default=False,
        help="Play the audio samples and show their spectrogram.")

    (opts, args) = parser.parse_args()

    import analyzer_vizualizer as tv

    if (opts.stream or opts.jack) and opts.nn:
        if opts.stream is not None:
            import connector_audiofile as ca
            # Build folder to store wav file
            a = opts.stream.split('/')
            a = a[len(a)-1].split('.')[0]
            wav_folder = opts.out + '/' + a + '/'

            if not os.path.exists(wav_folder):
                os.makedirs(wav_folder)

            analyzer = Analyzer(opts.nn, wav_folder=wav_folder)
            vizu     = tv.TidzamVizualizer()
            connector = ca.TidzamAudiofile(opts.stream,
                callable_objects = [analyzer, vizu],
                overlap=0)
            connector.start()


        elif opts.jack is not None:
            import connector_jack as cj

            if not os.path.exists(opts.out):
                os.makedirs(opts.out)

            analyzer = Analyzer(opts.nn, wav_folder=opts.out)
            vizu = tv.TidzamVizualizer()
            connector = cj.TidzamJack(opts.jack, callable_objects=[analyzer, vizu])
            connector.start()

            a = raw_input()
            vizu.stop()
            connector.stop()
            print('Program exited')
            os._exit(0)
    else:
        print(parser.usage)
