from __future__ import division

import tensorflow as tf
from tensorflow.contrib.tensorboard.plugins import projector
import data as tiddata
import numpy as np
import math

# Build Metadata file for tensorflow Embedding Vizualisation
# For each row in Y, right its classes number in out_file file
def build_metadatafile(Y, out_file='database/metadata.tsv'):
    names = [a for a in range(0,Y.shape[1])]
    metadata_file = open(out_file, 'a')
    for i in range(Y.shape[0]):
        metadata_file.write('%d\n' % (np.argmax(Y[i])))
    metadata_file.close()

def feed_embeddings(embedding_var, dataset_t, Pout, Pin,
            nb_embeddings=1,
            sess=False,
            checkpoint_dir='checkpoints/'):
    if sess is False:
        sess = tf.get_default_session()
    # Clean previous embedding for this place
    with open(checkpoint_dir+'/metadata-'+embedding_var.name.replace('/','-')+'.tsv', "w"):
        pass
    # Feed the network and stoire results
    dataset_t.split_dataset(p=1.0)
    bx, by = dataset_t.next_batch_train(batch_size=nb_embeddings)
    res = sess.run(Pout,feed_dict={Pin: bx} )
    embedding_var.assign(res)
    build_metadatafile(by, out_file=checkpoint_dir+'/metadata-'+embedding_var.name.replace('/','-')+'.tsv')

    embeddings_writer = tf.train.SummaryWriter(checkpoint_dir)
    config_projector = projector.ProjectorConfig()
    embedding = config_projector.embeddings.add()
    embedding.tensor_name = embedding_var.name
    embedding.metadata_path = checkpoint_dir+'/metadata-'+embedding_var.name.replace('/','-')+'.tsv'
    projector.visualize_embeddings(embeddings_writer, config_projector)

def print_kernel_filters(conv_layer): # [5, 5, 1, 32]
    with tf.name_scope('Visualize_filters') as scope:
        print('* Visualize_filters ' + conv_layer.name)
        W_kernels = conv_layer.W
        kernel_size = W_kernels.get_shape()[0].__int__()
        nb_kernel = W_kernels.get_shape()[3].__int__()
        img_size = int(math.ceil(math.sqrt(nb_kernel)))
        dim_features = W_kernels.get_shape()[2].__int__()

        # Add padding to feed the image if need
        nb_pad = img_size * img_size - nb_kernel
        Wpad= tf.zeros([kernel_size, kernel_size, dim_features , 1])
        for i in range(0,nb_pad):
            W_kernels = tf.concat(3, [W_kernels, Wpad])
        W_c = tf.split(3, img_size**2, W_kernels)

        # Build the image
        W_row = []
        for i in range (0, img_size):
            W_row.append(tf.concat(0, W_c[i*img_size: (i+1)*img_size ]))
        W_d = tf.concat(1, W_row)
        W_e = tf.reshape(W_d, [dim_features, img_size * kernel_size, img_size * kernel_size, 1])
        Wtag = tf.placeholder(tf.string, None)

        return W_e
