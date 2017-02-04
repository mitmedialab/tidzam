import numpy as np
import math
import sys, optparse

import tensorflow as tf
import tflearn

import vizualisation as vizu
import models.vgg as models
import data as tiddata

config = tf.ConfigProto(
        device_count = {'GPU': 0}
    )
dropout = 1



class AnalyzerVGG:
    def __init__(self, checkpoint_dir, label_dictionary,session=False):
        self.label_dic = label_dictionary
        self.dataw = 150
        self.datah = 186
        self.checkpoint_dir = checkpoint_dir

        # Open an session
        if session is False:
            self.session = tf.Session(config=config)
        else:
            self.session = session
        self.load()

    # Load the network
    def load(self):
        #Create input places
        self.vgg = models.VGG([self.dataw, self.datah], len(self.label_dic))

        adam = tflearn.Adam(learning_rate=0.001, beta1=0.99)
        net = tflearn.regression(self.vgg.out, optimizer=adam, batch_size=128)

        self.model = tflearn.DNN(net, session=self.session,
            tensorboard_dir= self.checkpoint_dir,
            tensorboard_verbose=0)

        self.session.run(tf.global_variables_initializer())
        try:
            print('Loading : ' + self.checkpoint_dir)
            self.model.load(self.checkpoint_dir, create_new_session=False)
        except:
            print('Unable to load model: ' + self.checkpoint_dir)
            quit()

        self.session.run(tf.global_variables_initializer())

    # Function called by the streamer to predic its current sample
    def run(self, Sxx, fs, t, sound_obj):
        Sxx = np.reshape(Sxx, [1, Sxx.shape[0]*Sxx.shape[1]] )
        res = self.model.predict(Sxx)
        a = np.argmax(res)
        print(self.label_dic[a])


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.set_defaults(play=False,dic=False,nn="checkpoints/")
    parser.add_option("-p", "--play", action="store", type="string", dest="play")
    parser.add_option("-d", "--dic", action="store", type="string", dest="dic")
    parser.add_option("-n", "--nn", action="store", type="string", dest="nn")
    (options, args) = parser.parse_args()

    if options.play and options.dic and options.nn:
        label_dic = np.load(options.dic + "_labels_dic.npy")
        player = AnalyzerVGG(options.nn, label_dic)
        tiddata.play_spectrogram_from_stream(options.play,
                show=True, callable_objects = [player])
    else:
        print('Wrong options : ')
