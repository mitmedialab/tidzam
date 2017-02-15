from __future__ import print_function

import sys, optparse
import numpy as np
import shutil
import math

from tensorflow.contrib.tensorboard.plugins import projector
import tensorflow as tf
import tflearn

import vizualisation as vizu
from models import *

import data as tiddata

###################################
### System configurations
###################################

usage="train.py --dataset=dataset_150x186 --out=save/ [OPTIONS]"
parser = optparse.OptionParser(usage=usage)
parser.add_option("-d", "--dataset",
    action="store", type="string", dest="dataset",
    help='Define the dataset to train.')

parser.add_option("-o", "--out",
    action="store", type="string", dest="out",
    default="/tmp/tflearn_logs",
    help='Define output folder to store the neural network and checkpoints.')

parser.add_option("--training-iterations",
    action="store", type="int", dest="training_iters",default=400,
    help='Number of training iterations (Default: 400 batchsize).')

parser.add_option("--batchsize",
    action="store", type="int", dest="batch_size",default=64,
    help='Size of the training batch (Default:64).')

parser.add_option("--embeddings",
    action="store", type="int", dest="nb_embeddings", default=50,
    help='Number of embeddings to compute (default: 50)..')

parser.add_option("--learning-rate",
    action="store", type="float", dest="learning_rate", default=0.001,
    help='Learning rate (default: 0.001).')

parser.add_option("--dnn",
    action="store", type="string", dest="dnn", default="default",
    help='DNN model to train (Default: ).')

parser.add_option("--embeddings-step",
    action="store", type="int", dest="EMBEDDINGS_STEP", default="1",
    help='Step period to compute embeddings and feature maps (Default: 1).')

(opts, args) = parser.parse_args()

###################################
# System configuration
###################################
config = tflearn.config.init_graph (
    num_cores=3,
    gpu_memory_fraction=0.75,
    soft_placement=False)

###################################
# Load the data
###################################
data_size=[150,186]
dataset     = tiddata.Dataset(opts.dataset, p=0.7, data_size=data_size)
dataset_t   = tiddata.Dataset(opts.dataset, data_size=(dataset.dataw,dataset.datah))

###################################
# Build graphs and session
###################################
with tf.variable_scope("embeddings"):
    embed1 = tf.get_variable("pred", [ opts.nb_embeddings, dataset.n_classes], trainable=False)

with tf.Session(config=config) as sess:

    ### Load the network model
    print("Loading Neural Network:  models/" + opts.dnn + ".py")
    net = eval(opts.dnn + ".DNN(data_size, dataset.n_classes)")

    ## Build summaries
    try:
        merged = None
        writer = tf.train.SummaryWriter(opts.out + "/" + net.name + "")

        for conv in net.show_kernel_map:
            img = vizu.print_kernel_filters(conv)
            nb_kernel = conv.get_shape()[3].__int__()
            tf.summary.image("Visualize_kernels of " + str(conv.name), img,
                max_outputs=nb_kernel)

        with tf.name_scope('Build_audio_from_filters') as scope:
            nb_kernel = net.conv1.get_shape()[3].__int__()
            W_c = tf.split(3, nb_kernel, net.conv1)
            tf.summary.audio("Visualize_audio", W_c[0][0], 48100,
                max_outputs=6)

        merged = tf.merge_all_summaries()
    except:
        print("No kernel map generated.")


    ### Define optimizer and cost function
    cost = tflearn.regression( net.out,
        optimizer='adam',
        learning_rate=opts.learning_rate,
        loss='softmax_categorical_crossentropy')


    ### Init the trainer
    trainer = tflearn.DNN(cost,
        session=sess,
        tensorboard_dir= opts.out + "/",
        tensorboard_verbose=3)


    # Build the graph
    sess.run(tf.global_variables_initializer())


    ### Load a previous session
    #if opts.load:
    try:
        print('Loading: ' + opts.out + "/" + net.name)
        trainer.load(opts.out + "/" + net.name, create_new_session=False)
    except:
        print("The destination folder contains a previous session.\nDo you want to erase it ? [y/N]")
        a = raw_input()
        if a == 'y':
            shutil.rmtree(opts.out)
        else:
            print('Unable to load network: ' + opts.out)
            quit()



    ### Run the training process
    step = 1
    while step < opts.training_iters:
        print("Load batchs")
        batch_x, batch_y            = dataset.next_batch_train(batch_size=opts.batch_size)
        batch_test_x, batch_test_y  = dataset.next_batch_test(batch_size=opts.batch_size)

        if opts.nb_embeddings > 0 and step % opts.EMBEDDINGS_STEP == 0 and step > 1:
            tflearn.is_training(False, session=sess)
            print("--\nSummaries and Embeddings")
            if merged is not None:
                print("* Kernel feature map rendering")
                merged_res  = sess.run([merged], feed_dict={ net.input: batch_x} )
                writer.add_summary(merged_res[0], step)

            print("* Generation of #" +str(opts.nb_embeddings)+ " embeddings for " + embed1.name)
            vizu.feed_embeddings(embed1, dataset_t, net.out, net.input,
                        nb_embeddings=opts.nb_embeddings,
                        checkpoint_dir=opts.out + "/" + net.name)

        tflearn.is_training(True, session=sess)
        trainer.fit(batch_x, batch_y, n_epoch=1, validation_set=(batch_test_x, batch_test_y),
              show_metric=True, run_id=net.name)

        print("Saving in " + opts.out + "/" + net.name + "\n--")
        trainer.save(opts.out + "/" + net.name)

        if step == 1:
            # Save the label dictionnary in out file
            np.save(opts.out + "/labels.dic", dataset.labels_dic)

        step = step + 1
