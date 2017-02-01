from __future__ import print_function

import sys, optparse
import numpy as np
import math

import tensorflow as tf

import vizualisation as vizu
import data as tiddata
import model as net


parser = optparse.OptionParser()
parser.set_defaults(train=False, out=False)
parser.add_option("-t", "--train", action="store", type="string", dest="train",
        help='Define the dataset to train.')
parser.add_option("-o", "--out", action="store", type="string", dest="out",
        help='Define output folder to store the neural network and checkpoints.')

(options, args) = parser.parse_args()

# Build a dataset from a folder containing wav files
if options.train:
    if options.out is False:
        print("You must specified an output folder to save the neural networks.")
        quit()
    dataset_file = options.train
    checkpoint_dir = options.out

else:
    print('You must specified the dataset to learn with --train=')
    quit()

# Load and prepare dataset
dataset = tiddata.Dataset(dataset_file,
        p=0.8,
        data_size=(150,186))

# Training parameters
learning_rate = 0.001
dropout = 0.75 # Dropout, probability to keep units
batch_size = 128
training_iters = 200

# Configurations
display_step = 5
saving_period = 5
embeddings = True
config = tf.ConfigProto(
        device_count = {'GPU': 0}
    )

with tf.name_scope('input'):
    X = tf.placeholder(tf.float32, [None, dataset.n_input])
    y = tf.placeholder(tf.float32, [None, dataset.n_classes])
    keep_prob = tf.placeholder(tf.float32)

### Model
with tf.name_scope('VGG'):
    tf.summary.scalar('dropout_keep_probability', keep_prob)
    global_step = tf.Variable(0, trainable=False, name='global_step')
    pred, biases, weights = net.vgg(X, dropout, dataset.n_classes,
            data_size=(dataset.dataw, dataset.datah))

    # Define loss and optimizer
    with tf.name_scope('Optimizer'):
        cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y))
        optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost, global_step=global_step)
        correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

    tf.summary.scalar('cross_entropy', cost)
    tf.summary.scalar('accuracy', accuracy)

    # Initializing the variables
init = tf.global_variables_initializer()

# Launch the graph
with tf.Session(config=config) as sess:
    sess.run(init)
    step = 1

    # Try to restore previous session
    ckpt = tf.train.get_checkpoint_state(checkpoint_dir + "/")
    if ckpt and ckpt.model_checkpoint_path:
        saver = tf.train.Saver(max_to_keep=2)
        saver.restore(sess, ckpt.model_checkpoint_path)
        step = int(tf.train.global_step(sess, global_step))
        print("Previous session loaded")
    else:
        print("New session")

    # Build summaries
    merged = tf.summary.merge_all()
    train_writer = tf.train.SummaryWriter(checkpoint_dir + '/', sess.graph)

    while step < training_iters:
        batch_x, batch_y = dataset.next_batch_train(batch_size = batch_size)

        # Run optimization op (backprop)
        sess.run(optimizer, feed_dict={X: batch_x, y: batch_y,
                                       keep_prob: dropout})

        # Calculate batch loss and accuracy
        if step % display_step == 0:
            run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
            run_metadata = tf.RunMetadata()
            summary, loss, acc = sess.run([merged, cost, accuracy],
                            feed_dict={X: batch_x, y: batch_y, keep_prob: 1.},
                            options=run_options,
                            run_metadata=run_metadata
                            )

            train_writer.add_run_metadata(run_metadata, 'step%d' % step)
            train_writer.add_summary(summary, step)

            print("Iter " + str(step*batch_size) + ", Minibatch Loss= " + \
                  "{:.6f}".format(loss) + ", Training Accuracy= " + \
                  "{:.5f}".format(acc))

            # Feed embeddings
            if embeddings is True:
                dataset_t = tiddata.Dataset(dataset_file,
                        data_size=(dataset.dataw,dataset.datah))
                vizu.feed_embeddings(dataset_t, pred, X,
                        checkpoint_dir=checkpoint_dir,
                        embedding_name='pred')

        # Session saving
        if step % saving_period == 0 or training_iters - step == 1:
            try:
                saver.save(sess, checkpoint_dir + '/VGG.ckpt', global_step= 1 + step)
            except NameError:
                saver = tf.train.Saver(max_to_keep=2)
                saver.save(sess, checkpoint_dir + '/VGG.ckpt', global_step= 1 + step)
            print("Session saved.")

        step += 1
    print("Optimization Finished!")

    # Calculate accuracy for 256 mnist test images
    print("Testing Accuracy:")
    dataset.cur_batch_test = 0
    for step in range (0, int(dataset.batch_test_count())-1 ):
        batch_x, batch_y = dataset.next_batch_test()
        print(sess.run(accuracy, feed_dict={X: batch_x, y: batch_y, keep_prob: 1.}))
