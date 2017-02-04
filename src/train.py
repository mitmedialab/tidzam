from __future__ import print_function

import sys, optparse
import numpy as np
import math

import tensorflow as tf
import tflearn

import vizualisation as vizu
import models.vgg as models

import data as tiddata

parser = optparse.OptionParser()
parser.add_option("-d", "--dataset",
    action="store", type="string", dest="dataset",
    help='Define the dataset to train.')

parser.add_option("--load",
    action="store", type="string", dest="load",
    help='Folder to load a previous training session.')

parser.add_option("-o", "--out",
    action="store", type="string", dest="out",
    default="/tmp/tflearn_logs/vgg-model/",
    help='Define output folder to store the neural network and checkpoints.')

parser.add_option("--training-iterations",
    action="store", type="int", dest="training_iters",default=200,
    help='Number of training iterations (Default: 200 batchsize).')

parser.add_option("--batchsize",
    action="store", type="int", dest="batch_size",default=128,
    help='Set the learning rate (Default: 0.001).')

parser.add_option("--embeddings",
    action="store", type="int", dest="nb_embeddings", default=1,
    help='Embeddings Batchise Packets to compute (default: 1).')

(options, args) = parser.parse_args()

config = tf.ConfigProto(
        device_count = {'GPU': 0}
    )

###################################

# Load data
data_size=[150,186]
dataset = tiddata.Dataset(options.dataset, p=0.8, data_size=data_size)

# TF Variables to save outputs embedding computations.
with tf.variable_scope("embeddings"):
    embed1 = tf.get_variable("pred",
        [ options.nb_embeddings* options.batch_size, dataset.n_classes])

with tf.Session(config=config) as sess:
    # Load a network model
    vgg = models.VGG(data_size, dataset.n_classes)
    train_writer = tf.train.SummaryWriter(options.out + "/" + vgg.name+"/")

    # Define optimizer and cost function
    adam = tflearn.Adam(learning_rate=0.001, beta1=0.99)
    net = tflearn.regression(vgg.out, optimizer=adam, batch_size=options.batch_size)

    model = tflearn.DNN(net, session=sess,
        tensorboard_dir= options.out + "/",
        tensorboard_verbose=0)

    if options.load:
        try:
            model.load(options.load + "/" + vgg.name)
        except:
            print('Unable to load model: ' + options.load)
    else:
        sess.run(tf.global_variables_initializer())

    step = 1
    while step < options.training_iters:
        batch_x, batch_y            = dataset.next_batch_train(batch_size = options.batch_size)
        batch_test_x, batch_test_y  = dataset.next_batch_test(batch_size = options.batch_size)

        model.fit(batch_x, batch_y, n_epoch=1, validation_set=(batch_test_x, batch_test_y),
              show_metric=True, run_id=vgg.name)

        print("* Generation of #" +str(options.nb_embeddings*options.batch_size)+ " embeddings for " + embed1.name)
        if options.nb_embeddings > 0:
            print("** Loading "+options.dataset+"_labels.npy" )
            dataset_t = tiddata.Dataset(options.dataset, data_size=(dataset.dataw,dataset.datah))
            vizu.feed_embeddings(train_writer, embed1, dataset_t, vgg.out, vgg.input,
                    nb_embeddings=options.nb_embeddings,sess=sess,
                    checkpoint_dir=options.out + "/" + vgg.name+"/" )

        print("Saving in " + options.out + "/" + vgg.name)
        model.save(options.out + "/" + vgg.name)
        step = step + 1
