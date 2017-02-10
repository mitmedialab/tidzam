import numpy as np
import math
import sys, optparse

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

class Analyzer:
    def __init__(self, checkpoint_dir, label_dictionary,session=False):
        self.label_dic = label_dictionary
        self.dataw = 150
        self.datah = 186
        self.checkpoint_dir = checkpoint_dir
        self.count_run = -1

        # Open an session
        if session is False:
            self.session = tf.Session(config=config)
        else:
            self.session = session
        self.load()

    # Load the network
    def load(self):
        path = self.checkpoint_dir.split('/')
        a = path[len(path) - 1 ]
        if a == '':
            a = path[len(path) - 2 ]
        self.vgg = net = eval( a + ".DNN([self.dataw, self.datah], len(self.label_dic))")

        self.model = tflearn.DNN(self.vgg.out,
            session=self.session,
            tensorboard_dir= self.checkpoint_dir + "/",
            tensorboard_verbose=0)
        self.session.run(tf.global_variables_initializer())

        try:
            print('Loading : ' + self.checkpoint_dir + "." + self.vgg.name)
            self.model.load(self.checkpoint_dir + "/" + self.vgg.name, create_new_session=False)
        except:
            print('Unable to load model: ' + self.checkpoint_dir)
            quit()

    # Function called by the streamer to predic its current sample
    def run(self, Sxxs, fs, t, sound_obj, wav_folder="wav/"):
        self.count_run = self.count_run + 1
        time = str(int(self.count_run * 0.5) / 3600) + ":" + \
                str( int(self.count_run * 0.5 % 3600)/60) + ":" + \
                str( int(self.count_run * 0.5 % 3600 % 60)) + ":" + \
                str( int( ((self.count_run * 0.5 % 3600 % 60) * 1000) % 1000) ) + "ms"
        print("----------------------------------- " + time)

        res = self.model.predict(Sxxs)
        for channel in range(0, Sxxs.shape[0]):
            a = np.abs(np.max(res[channel]) / np.mean(res[channel]))
            if a < 2:
                classe = 'unknow'
            else:
                classe = str(self.label_dic[ np.argmax(res[channel]) ])
            print( "channel " + str(channel) + ' | ' + classe + ' (' + str(a) + ')')

            # Save the file on the disk
            sf.write (wav_folder + '/+' + classe + '(' + str(channel) + ')_' + time +'.wav',
                sound_obj[0][:,channel], sound_obj[1])

if __name__ == "__main__":
    usage = 'analyzer.py --nn=build/test --stream=stream.wav [--show, -h]'
    parser = optparse.OptionParser(usage=usage)
    parser.set_defaults(stream=False,dic=False,nn="build/default")

    parser.add_option("-s", "--stream", action="store", type="string", dest="stream",
        help="Input audio stream to analyze.")

    parser.add_option("-n", "--nn", action="store", type="string", dest="nn",
        help="Neural Network session to load.")

    parser.add_option("--show", action="store_true", dest="show", default=False,
        help="Play the audio samples and show their spectrogram.")

    (opts, args) = parser.parse_args()

    if opts.stream and opts.nn:
        labels_dic = np.load(opts.nn + "/labels.dic.npy")
        streamer = Analyzer(opts.nn, labels_dic)
        tiddata.play_spectrogram_from_stream(opts.stream,
                show=opts.show, callable_objects = [streamer])
    else:
        print(parser.usage)
