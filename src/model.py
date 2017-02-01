from __future__ import division
import tensorflow as tf
import math

### TensorBoard
def variable_summaries(var):
    mean = tf.reduce_mean(var)
    tf.summary.scalar('mean', mean)
    with tf.name_scope('stddev'):
      stddev = tf.sqrt(tf.reduce_mean(tf.square(var - mean)))
    tf.summary.scalar('stddev', stddev)
    tf.summary.scalar('max', tf.reduce_max(var))
    tf.summary.scalar('min', tf.reduce_min(var))
    tf.summary.histogram('histogram', var)
###---------------------------------

# Create some wrappers for simplicity
def conv2d(x, W, b, strides=1):
#    with tf.name_scope('in'):
#        variable_summaries(x)
#    with tf.name_scope('weights'):
#        variable_summaries(W)
#    with tf.name_scope('biases'):
#        variable_summaries(b)

    # Conv2D wrapper, with bias and relu activation
    x = tf.nn.conv2d(x, W, strides=[1, strides, strides, 1], padding='SAME')
    x = tf.nn.bias_add(x, b)
    # Summaries
    with tf.name_scope('out'):
        out = tf.nn.relu(x)
    return out


def maxpool2d(x, k=2):
    # MaxPool2D wrapper
    return tf.nn.max_pool(x, ksize=[1, k, k, 1], strides=[1, k, k, 1],
                          padding='SAME')


# Create model
def vgg(x, dropout, n_classes, data_size=(92,638)):
    nb_pooling = 2
    k_pooling = 2
    a = int(math.ceil(data_size[0]/(k_pooling**nb_pooling))*math.ceil(data_size[1]/(k_pooling**nb_pooling)))

    weights = {
        # 5x5 conv, 1 input, 32 outputs
        'wc1': tf.Variable(tf.random_normal([6, 5, 1, 64]), name='kernel1'),
        # 5x5 conv, 32 inputs, 64 outputs
        'wc2': tf.Variable(tf.random_normal([5, 5, 64, 64]), name='kernel2'),
        'wc3': tf.Variable(tf.random_normal([6, 5, 64, 64]), name='kernel3'),
        # 5x5 conv, 32 inputs, 64 outputs
        'wc4': tf.Variable(tf.random_normal([5, 5, 64, 64]), name='kernel4'),
        # fully connected, 7*7*64 inputs, 1024 outputs
        'wd1': tf.Variable(tf.random_normal([a * 64, 2048]), name='layer1'),
        'wd2': tf.Variable(tf.random_normal([2048, 2048]), name='layer2'),
        # 1024 inputs, 10 outputs (class prediction)
        'out': tf.Variable(tf.random_normal([2048, n_classes]), name='layer_out')
    }

    biases = {
        'bc1': tf.Variable(tf.random_normal([64]), name='biases-K1'),
        'bc2': tf.Variable(tf.random_normal([64]), name='biases-K2'),
        'bc3': tf.Variable(tf.random_normal([64]), name='biases-K3'),
        'bc4': tf.Variable(tf.random_normal([64]), name='biases-K4'),
        'bd1': tf.Variable(tf.random_normal([2048]), name='biases-L1'),
        'bd2': tf.Variable(tf.random_normal([2048]), name='biases-L2'),
        'out': tf.Variable(tf.random_normal([n_classes]), name='biases-out')
    }
    # Reshape input picture
    with tf.name_scope('input'):
        x = tf.reshape(x, shape=[-1, data_size[0], data_size[1], 1])
        x = tf.nn.l2_normalize(x, 0)

    # Convolution Layer
    with tf.name_scope('conv1'):
        conv1 = conv2d(x, weights['wc1'], biases['bc1'])

    with tf.name_scope('conv2'):
        conv2 = conv2d(conv1, weights['wc2'], biases['bc2'])

    # Max Pooling (down-sampling)
    with tf.name_scope('pool1'):
        pool1 = maxpool2d(conv2, k=2)

    with tf.name_scope('conv3'):
        conv3 = conv2d(pool1, weights['wc3'], biases['bc3'])

    with tf.name_scope('conv4'):
        conv4 = conv2d(conv3, weights['wc4'], biases['bc4'])

    with tf.name_scope('pool2'):
        pool2 = maxpool2d(conv4, k=2)

    # Fully connected layer
    # Reshape conv2 output to fit fully connected layer input
    fc1 = tf.reshape(pool2, [-1, weights['wd1'].get_shape().as_list()[0]])
    # First layer
    with tf.name_scope('fc1'):
        fc1 = tf.add(tf.matmul(fc1, weights['wd1']), biases['bd1'])
        fc1 = tf.nn.relu(fc1)
    # Second layer
    with tf.name_scope('fc2'):
        fc2 = tf.add(tf.matmul(fc1, weights['wd2']), biases['bd2'])
        fc2 = tf.nn.relu(fc2)

    # Apply Dropout
    with tf.name_scope('dropout'):
        fc2 = tf.nn.dropout(fc2, dropout)

    # Output, class prediction
    with tf.name_scope('classes'):
        net = tf.add(tf.matmul(fc2, weights['out']), biases['out'])
    return net, biases, weights
