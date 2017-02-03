import numpy as np
import math
import sys, optparse

import tensorflow as tf

import vizualisation as vizu
import data as tiddata
import model as net

config = tf.ConfigProto(
        device_count = {'GPU': 0}
    )
dropout = 1

#Create input places
with tf.name_scope('input'):
    X = tf.placeholder(tf.float32, [None, 150*186])
    y = tf.placeholder(tf.float32, [None, 50])
    keep_prob = tf.placeholder(tf.float32)

### Build the Neural Net model
with tf.name_scope('VGG'):
    tf.summary.scalar('dropout_keep_probability', keep_prob)
    global_step = tf.Variable(0, trainable=False, name='global_step')
    pred, biases, weights = net.vgg(X, dropout, 50,
            data_size=(150,186))
    correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))
    tf.summary.scalar('accuracy', accuracy)

init = tf.global_variables_initializer()

# Create an runnable object for the streamer
class AnalyzerVGG:
    def __init__(self, checkpoint_dir, label_dictionary):
        self.label_dic = label_dictionary
        self.session = session = tf.InteractiveSession(config=config)
        self.session.run(init)

        # Load the session of the neural network
        ckpt = tf.train.get_checkpoint_state(checkpoint_dir + "/")
        if ckpt and ckpt.model_checkpoint_path:
            saver = tf.train.Saver(max_to_keep=2)
            saver.restore(self.session, ckpt.model_checkpoint_path)
            print("Previous session loaded")
        else:
            print("Not Neural Network found in " + checkpoint_dir)
            quit()

    # Function called by the streamer to predic its current sample
    def run(self, Sxx, fs, t, sound_obj):
        Sxx = np.reshape(Sxx, [1, Sxx.shape[0]*Sxx.shape[1]] )
        res = self.session.run(pred,feed_dict={X: Sxx} )
        a = np.argmax(res)
        print(self.label_dic[a])

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.set_defaults(play=False,dic=False,nn=False)
    parser.add_option("-p", "--play", action="store", type="string", dest="play")
    parser.add_option("-d", "--dic", action="store", type="string", dest="dic")
    parser.add_option("-n", "--nn", action="store", type="string", dest="nn")
    (options, args) = parser.parse_args()

    checkpoint_dir = "checkpoints"

    if options.play and options.dic and options.nn:
        label_dic = np.load(options.dic + "_labels_dic.npy")
        player = AnalyzerVGG(options.nn, label_dic)
        tiddata.play_spectrogram_from_stream(options.play,
                show=False, callable_objects = [player])
    else:
        print('Wrong options : ')
