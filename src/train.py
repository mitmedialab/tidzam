from __future__ import print_function

import sys, optparse
import numpy as np
import math

import tensorflow as tf

import vizualisation as vizu
import data as tiddata
import model as net

usage = "usage: %prog --train=dataset --out=folder_dest [options]"
parser = optparse.OptionParser(usage=usage)
parser.add_option("-t", "--train",
    action="store", type="string", dest="train",
    help='Define the dataset to train.')

parser.add_option("-o", "--out",
    action="store", type="string", dest="out",
    help='Define output folder to store the neural network and checkpoints.')

parser.add_option("--embeddings",
    action="store", type="int", dest="nb_embeddings", default=0,
    help='Number of embeddings to generate (default: 0).')

parser.add_option("--display-step",
    action="store", type="int", dest="display_step", default=5,
    help='Period to compute cost and accuracy functions (Default: 5).')

parser.add_option("--saving-step",
    action="store", type="int", dest="saving_period",default=5,
    help='Period to save the session (Default: 5).')

parser.add_option("--learning-rate",
    action="store", type="float", dest="learning_rate",default=0.001,
    help='Set the learning rate (Default: 0.001).')

parser.add_option("--dropout",
    action="store", type="float", dest="dropout",default=0.75,
    help='Set the dropout probability rate (Default: 0.75).')

parser.add_option("--batchsize",
    action="store", type="int", dest="batch_size",default=128,
    help='Set the learning rate (Default: 0.001).')

(options, args) = parser.parse_args()

# Build a dataset from a folder containing wav files
if options.train:
    if options.out is False:
        print("You must specified an output folder to save the neural networks.")
        quit()
    dataset_file = options.train
    checkpoint_dir = options.out

print("Display step %d" % options.display_step)

# Load and prepare dataset
print("Loading "+dataset_file+"_labels.npy" )
dataset = tiddata.Dataset(dataset_file,
        p=0.8,
        data_size=(150,186))

# Training parameters
training_iters = 200

############################ Configurations
config = tf.ConfigProto(
        device_count = {'GPU': 0}
    )

############################ INPUTS
with tf.name_scope('input'):
    X = tf.placeholder(tf.float32, [None, dataset.n_input])
    y = tf.placeholder(tf.float32, [None, dataset.n_classes])
    keep_prob = tf.placeholder(tf.float32)

############################  Model
with tf.name_scope('VGG'):
    global_step = tf.Variable(0, trainable=False, name='global_step')
    pred, biases, weights = net.vgg(X, options.dropout, dataset.n_classes,
            data_size=(dataset.dataw, dataset.datah))

    # Define loss and optimizer
    with tf.name_scope('Optimizer'):
        cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y))
        optimizer = tf.train.AdamOptimizer(learning_rate=options.learning_rate).minimize(cost, global_step=global_step)
        correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

    tf.summary.scalar('dropout', keep_prob)
    tf.summary.scalar('cross_entropy', cost)
    tf.summary.scalar('accuracy', accuracy)

############################ EMBEDDINGS
# TF Variables to save outputs embedding computations.
with tf.variable_scope("embeddings"):
    embed1 = tf.get_variable("pred", [ options.nb_embeddings* options.batch_size, dataset.n_classes])


############################ SESSION
with tf.Session(config=config) as sess:
    sess.run(tf.global_variables_initializer())
    step = 1

    # Try to restore previous session
    ckpt = tf.train.get_checkpoint_state(checkpoint_dir + "/")
    if ckpt and ckpt.model_checkpoint_path:
        saver = tf.train.Saver(max_to_keep=2)
        saver.restore(sess, ckpt.model_checkpoint_path)
        step = int(tf.train.global_step(sess, global_step))
        print("Previous session loaded")
    else:
        print("\nNew session\n-----------\n")

    # Build summaries
    merged = tf.summary.merge_all()
    train_writer = tf.train.SummaryWriter(checkpoint_dir + '/', sess.graph)
    saver = tf.train.Saver(max_to_keep=2)

    while step < training_iters:
        batch_x, batch_y = dataset.next_batch_train(batch_size = options.batch_size)

        # Run optimization op (backprop)
        print("* Run optimization ")
        sess.run(optimizer, feed_dict={X: batch_x, y: batch_y,
                                       keep_prob: options.dropout})

        # Calculate batch loss and accuracy
        if step % options.display_step == 0:
            print("* Compute cost, accurancy and summaries ")
            run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
            run_metadata = tf.RunMetadata()
            summary, loss, acc = sess.run([merged, cost, accuracy],
                            feed_dict={X: batch_x, y: batch_y, keep_prob: 1.},
                            options=run_options,
                            run_metadata=run_metadata
                            )
            train_writer.add_run_metadata(run_metadata, 'step%d' % step)
            train_writer.add_summary(summary, step)

            # Feed embeddings
            print("* Generation of #" +str(options.nb_embeddings)+ " embeddings for " + embed1.name)
            if options.nb_embeddings > 0:
                print("** Loading "+dataset_file+"_labels.npy" )
                dataset_t = tiddata.Dataset(dataset_file,
                        data_size=(dataset.dataw,dataset.datah))
                vizu.feed_embeddings(train_writer, embed1, dataset_t, pred, X,
                        nb_embeddings=options.nb_embeddings,
                        checkpoint_dir=checkpoint_dir)
                print("** Build." )

        # Session saving
        if step % options.saving_period == 0 or training_iters - step == 1:
            saver.save(sess, checkpoint_dir + '/VGG.ckpt', global_step= 1 + step)
            print("* Session saved.")

        print("=> Iter " + str(step*options.batch_size) + ", Minibatch Loss= " + \
              "{:.6f}".format(loss) + ", Training Accuracy= " + \
              "{:.5f}".format(acc))
        print("=============================")
        step += 1
    print("Optimization Finished!")

    # Calculate accuracy for 256 mnist test images
    print("Testing Accuracy:")
    dataset.cur_batch_test = 0
    for step in range (0, int(dataset.batch_test_count())-1 ):
        batch_x, batch_y = dataset.next_batch_test()
        print(sess.run(accuracy, feed_dict={X: batch_x, y: batch_y, keep_prob: 1.}))
