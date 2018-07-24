from __future__ import division

import numpy as np
import math
import os

import tensorflow as tf
from tensorflow.contrib.tensorboard.plugins import projector
from App import App

class Embedding:
    def __init__(self, name, input, ouput, dropout, projector, nb_embeddings, checkpoint_dir):
        self.input = input
        self.ouput = ouput
        self.dropout = dropout
        self.checkpoint_dir = checkpoint_dir
        self.nb_embeddings = nb_embeddings
        self.config_projector = projector

        self.embedding_var = tf.get_variable(name,
                shape=[nb_embeddings, self.ouput.shape[1]],
                trainable=False)
        self.assign        = self.embedding_var.assign(self.ouput)

        self.embedding = self.config_projector.embeddings.add()
        self.embedding.tensor_name = self.embedding_var.name
        self.embedding.metadata_path = os.path.abspath(self.checkpoint_dir)+'/metadata-' + \
                        self.embedding_var.name.replace('/','-')+'.tsv'

    def evaluate(self, batch_x, batch_y, session, dic=None):
        App.log(0, "* Generation of #" +str(batch_x.shape[0])+ " embeddings for " + self.embedding_var.name)
        try:
                session.run( [self.assign.op], feed_dict={self.input: batch_x, self.dropout: 1.0})
                self.build_metadatafile(batch_y, dic=dic, out_file=self.checkpoint_dir+'/metadata-'+self.embedding_var.name.replace('/','-')+'.tsv')
        except:
                App.log(0, "Embeddings computation error")

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

class Summaries:
    def __init__(self, net, nb_classes):
        self.net        = net
        self.sunnaries_op = []

        App.log(0, "Build summaries")
        correct_prediction = tf.equal(tf.argmax(self.net.labels, 1), tf.argmax(self.net.out, 1))
        self.accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
        #correct_prediction = tf.equal(tf.round(tf.nn.sigmoid(self.net.out)), tf.round(self.net.labels))

        #all_labels_true = tf.reduce_min(tf.cast(correct_prediction, tf.float32), 1)
        #self.accuracy = tf.reduce_mean(all_labels_true)
        self.accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))


        tf.summary.scalar('accuracy', self.accuracy)
        tf.summary.scalar('Cost', self.net.cost)
        tf.summary.scalar('dropout_probability', self.net.keep_prob)

        precision, precision_op = tf.metrics.precision(
                    tf.argmax(self.net.labels,1),
                    tf.argmax(self.net.out,1))
        tf.summary.scalar('Precision', precision)
        self.sunnaries_op.append(precision_op)

        recall, recall_op = tf.metrics.recall(
                    tf.argmax(self.net.labels,1),
                    tf.argmax(self.net.out,1))
        tf.summary.scalar('Recall', recall)
        self.sunnaries_op.append(recall_op)

        confusion = tf.confusion_matrix(
                    tf.argmax(self.net.labels,1),
                    tf.argmax(self.net.out,1),
                    num_classes=nb_classes,
                    dtype=tf.float32)
        tf.summary.image('Confusion', tf.reshape(confusion, [1, nb_classes, nb_classes, 1]))

    def evaluate(self, batch_x, batch_y, session):
        session.run( [self.sunnaries_op],
            feed_dict={
                    self.net.input: batch_x,
                    self.net.labels:batch_y,
                    self.net.keep_prob: 1.0
                    })

    def build_kernel_filters_summaries(self,conv_layers):
            try:
                for conv in conv_layers :
                    App.log(0, '* Load filter kernel printer for ' + conv.name)
                    kernel_size  = conv.get_shape()[0].__int__()
                    nb_kernel    = conv.get_shape()[3].__int__()
                    img_size     = int(math.ceil(math.sqrt(nb_kernel)))
                    dim_features = conv.get_shape()[2].__int__()

                    # Add padding to feed the image if need
                    nb_pad = img_size * img_size - nb_kernel
                    Wpad= tf.zeros([kernel_size, kernel_size, dim_features , 1])
                    for i in range(0,nb_pad):
                        conv = tf.concat([conv, Wpad], 3)
                    W_c = tf.split(conv, img_size**2, 3)

                    # Build the image
                    W_row = []
                    for i in range (0, img_size):
                        W_row.append(tf.concat(W_c[i*img_size: (i+1)*img_size ],0))
                    W_d = tf.concat(W_row, 1)
                    img = tf.reshape(W_d, [dim_features, img_size * kernel_size, img_size * kernel_size, 1])
                    Wtag = tf.placeholder(tf.string, None)

                    nb_kernel = conv.get_shape()[3].__int__()
                    tf.summary.image("Visualize_kernels of " + str(conv.name), img,
                        max_outputs=nb_kernel)
            except Exception as ex:
                App.log(0, "No kernel map generated.")
                App.log(0, ex)
