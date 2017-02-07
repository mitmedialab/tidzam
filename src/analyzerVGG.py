import numpy as np
import math
import sys, optparse

import soundfile as sf
import tensorflow as tf
import tflearn

import vizualisation as vizu
import models.vgg as models
import data as tiddata

import sounddevice as sd

config = tflearn.config.init_graph (
    num_cores=3,
    gpu_memory_fraction=0.75,
    soft_placement=False)
dropout = 1

class AnalyzerVGG:
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

        self.vgg = models.VGG([self.dataw, self.datah], len(self.label_dic))
        self.model = tflearn.DNN(self.vgg.out,
            session=self.session,
            tensorboard_dir= self.checkpoint_dir + "/",
            tensorboard_verbose=0)
        self.session.run(tf.global_variables_initializer())

        try:
            print('Loading : ' + self.checkpoint_dir + "/" + self.vgg.name)
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
            if a < 5:
                classe = 'unknow'
            else:
                classe = str(self.label_dic[ np.argmax(res[channel]) ])
            print( "channel " + str(channel) + ' | ' + classe + ' (' + str(a) + ')')

            # Save the file on the disk
            sf.write (wav_folder + '/+' + classe + '(' + str(channel) + ')_' + time +'.wav',
                sound_obj[0][:,channel], sound_obj[1])

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
