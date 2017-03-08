from __future__ import print_function

import sys, optparse
import numpy as np
import shutil
import math
import os

from tensorflow.contrib.tensorboard.plugins import projector
import tensorflow as tf
import tflearn
from sklearn import *

import vizualisation as vizu
from models import *

import data as tiddata


print("TensorFlow "+ tf.__version__)
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
dataset     = tiddata.Dataset(opts.dataset, p=0.8)
dataset_t   = tiddata.Dataset(opts.dataset)

from tflearn.data_utils import pad_sequences
#dataset.data_train = pad_sequences(dataset.data_train, maxlen=dataset.dataw*dataset.datah, value=0.)
#dataset.data_test = pad_sequences(dataset.data_test, maxlen=dataset.dataw*dataset.datah, value=0.)

print("Sample size: " + str(dataset.dataw) + 'x' + str(dataset.datah))

# Check limit of generable embeddings
opts.nb_embeddings = min(opts.nb_embeddings, dataset.data.shape[0])

###################################
# Build graphs and session
###################################
with tf.variable_scope("embeddings"):
    embed1 = tf.get_variable("pred", [ opts.nb_embeddings, dataset.n_classes], trainable=False)

with tf.name_scope('Accurancy-Score'):
    precision = tf.Variable(0.0, trainable=False)
    recall = tf.Variable(0.0, trainable=False)
    f1 = tf.Variable(0.0, trainable=False)
    matrix_conf = tf.get_variable("matric_conf", [1, dataset.n_classes, dataset.n_classes,1], trainable=False)

with tf.Session(config=config) as sess:

    ### Load the network model
    print("Loading Neural Network:  models/" + opts.dnn + ".py")
    net = eval(opts.dnn + ".DNN([dataset.dataw, dataset.datah], dataset.n_classes)")

    ## Build summaries
    with tf.name_scope('Stats'):
        tf.summary.scalar('Precision', precision)
        tf.summary.scalar('Recall', recall)
        tf.summary.scalar('F1', f1)
        tf.summary.image("Confusion Matrix", matrix_conf)

    try:
        for conv in net.show_kernel_map:
            img = vizu.print_kernel_filters(conv)
            nb_kernel = conv.get_shape()[3].__int__()
            tf.summary.image("Visualize_kernels of " + str(conv.name), img,
                max_outputs=nb_kernel)

        with tf.name_scope('Build_audio_from_filters') as scope:
            nb_kernel = net.conv1.get_shape()[3].__int__()
            W_c = tf.split(net.conv1, nb_kernel, 3)
            tf.summary.audio("Visualize_audio", W_c[0][0], 48100,
                max_outputs=6)
    except:
        print("No kernel map generated.")

    merged = tf.summary.merge_all()
    writer = tf.summary.FileWriter(opts.out + "/" + net.name + "")

    ### Define optimizer and cost function
    cost = tflearn.regression( net.out,
        optimizer='adam',
        learning_rate=opts.learning_rate,
        #loss='binary_crossentropy')
        loss='softmax_categorical_crossentropy')

    ### Init the trainer
    trainer = tflearn.DNN(cost,
        session=sess,
        tensorboard_dir= opts.out + "/",
        tensorboard_verbose=2)


    # Build the graph
    sess.run(tf.global_variables_initializer())


    ### Load a previous session
    #if opts.load:
    if not os.path.exists(opts.out + "/"):
        print("Create output folder : " + opts.out + "/")
        os.makedirs(opts.out + "/")
    else :
        try:
            print('Loading: ' + opts.out + "/" + net.name)
            trainer.load(opts.out + "/" + net.name, create_new_session=False)
        except:
            print("The destination folder contains a previous session.\nDo you want to erase it ? [y/N]")
            a = input()
            if a == 'y':
                shutil.rmtree(opts.out)
            else:
                print('Unable to load network: ' + opts.out)
                quit()



    ### Run the training process
    step = 1
    writer.close()
    while step < opts.training_iters:
        print("Load batchs")
        batch_x, batch_y            = dataset.next_batch_train(batch_size=opts.batch_size)
        batch_test_x, batch_test_y  = dataset.next_batch_test(batch_size=opts.batch_size)

        if opts.nb_embeddings > 0 and step % opts.EMBEDDINGS_STEP == 0 and step > 1:
            tflearn.is_training(False, session=sess)
            print("--\nSummaries and Embeddings")

            y_pred = trainer.predict(batch_test_x)
            y_pred = np.argmax(y_pred,1)
            y_true = np.argmax(batch_test_y,1)
            sess.run( [
                precision.assign(metrics.precision_score(y_true, y_pred, average='micro')),
                recall.assign(metrics.recall_score(y_true, y_pred, average='micro')),
                f1.assign(metrics.f1_score(y_true, y_pred, average='micro')),
                matrix_conf.assign(np.reshape(metrics.confusion_matrix(y_true, y_pred), [1, dataset.n_classes, dataset.n_classes , 1]))
                ])

            print("* Kernel feature map rendering")
            merged_res  = sess.run([merged], feed_dict={ net.input: batch_x} )
            writer.reopen()
            writer.add_summary(merged_res[0], step)
            writer.close()

            print("* Generation of #" +str(opts.nb_embeddings)+ " embeddings for " + embed1.name)
            vizu.feed_embeddings(embed1, dataset_t, net.out, net.input,
                        nb_embeddings=opts.nb_embeddings,
                        checkpoint_dir=opts.out + "/" + net.name,
                        embeddings_writer=writer)

        tflearn.is_training(True, session=sess)
        trainer.fit(batch_x, batch_y, n_epoch=1, validation_set=(batch_test_x, batch_test_y),
              show_metric=True, run_id=net.name)


        print("Saving in " + opts.out + "/" + net.name + "\n--")
        trainer.save(opts.out + "/" + net.name)

        if step == 1:
            # Save the label dictionnary in out file
            np.save(opts.out + "/labels.dic", dataset.labels_dic)

        step = step + 1
