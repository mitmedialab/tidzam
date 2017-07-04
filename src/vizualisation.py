from __future__ import division

import tensorflow as tf
from tensorflow.contrib.tensorboard.plugins import projector
import data as tiddata
import numpy as np
import math

class Embedding:
    def __init__(self, Pin, Pout, embedding_var, checkpoint_dir):
        self.Pin = Pin
        self.Pout = Pout
        self.checkpoint_dir = checkpoint_dir
        self.embedding_var = embedding_var

        self.config_projector = projector.ProjectorConfig()
        self.embedding = self.config_projector.embeddings.add()
        self.embedding.tensor_name = self.embedding_var.name
        self.embedding.metadata_path = self.checkpoint_dir+'/metadata-'+embedding_var.name.replace('/','-')+'.tsv'

    def evaluate(self, dataset_t,  nb_embeddings, sess,dic=None):
        #dataset_t.split_dataset(p=0)
        bx, by = dataset_t.next_batch(batch_size=nb_embeddings)
        sess.run([self.embedding_var.assign(self.Pout)],feed_dict={self.Pin: bx})
        self.build_metadatafile(by, dic=dic, out_file=self.checkpoint_dir+'/metadata-'+self.embedding_var.name.replace('/','-')+'.tsv')

    def build_metadatafile(self, Y, dic=None, out_file='database/metadata.tsv'):
        # Clean previous embedding for this place
        with open(out_file, "w"):
            pass
        names = [a for a in range(0,Y.shape[1])]
        metadata_file = open(out_file, 'w')
        for i in range(Y.shape[0]):
            l = np.argmax(Y[i])
            if dic is None:
                metadata_file.write('%d\n' % (l))
            else:
                metadata_file.write('%s\n' % ( str(dic[int(l)]) ))
        metadata_file.close()

def print_kernel_filters(conv_layer):
    with tf.name_scope('Visualize_filters') as scope:
        print('* Load filter kernel printer for ' + conv_layer.name)

        kernel_size  = conv_layer.W.get_shape()[0].__int__()
        nb_kernel    = conv_layer.W.get_shape()[3].__int__()
        img_size     = int(math.ceil(math.sqrt(nb_kernel)))
        dim_features = conv_layer.W.get_shape()[2].__int__()

        # Add padding to feed the image if need
        nb_pad = img_size * img_size - nb_kernel
        Wpad= tf.zeros([kernel_size, kernel_size, dim_features , 1])
        for i in range(0,nb_pad):
            conv_layer.W = tf.concat([conv_layer.W, Wpad], 3)
        W_c = tf.split(conv_layer.W, img_size**2, 3)

        # Build the image
        W_row = []
        for i in range (0, img_size):
            W_row.append(tf.concat(W_c[i*img_size: (i+1)*img_size ],0))
        W_d = tf.concat(W_row, 1)
        W_e = tf.reshape(W_d, [dim_features, img_size * kernel_size, img_size * kernel_size, 1])
        Wtag = tf.placeholder(tf.string, None)
        return W_e
