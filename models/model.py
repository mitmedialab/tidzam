import tensorflow as tf
import src.lib as tl

class DNN:
    def __init__(self,data_size, n_classes):
        self.name = "selector"
        self.show_kernel_map = []

        with tf.name_scope('Input'):
            self.input = tf.placeholder(tf.float32, shape=[None, data_size[0] * data_size[1] ], name="x-input")

        with tf.name_scope('Labels'):
            self.labels = tf.placeholder(tf.float32, shape=[None, n_classes], name="y-input")

        with tf.name_scope('DropOut'):
            self.keep_prob = tf.placeholder(tf.float32)

        with tf.name_scope('model'):
            net = tf.reshape(self.input, shape=[-1, data_size[0], data_size[1], 1])

            with tf.variable_scope("CONV_1"):
                [conv1, W, b] = tl.conv2d(net, 121, 20)
                R1 = tf.nn.l2_loss(W)
                self.show_kernel_map.append(W) # Create the feature map

            with tf.variable_scope("POOL_1"):
                pool1 = tl.max_pool_2x2(conv1)

            with tf.variable_scope("CONV_2"):
                [conv2, W, b] = tl.conv2d(pool1, 16, 10)
                R2 = tf.nn.l2_loss(W)
                self.show_kernel_map.append(W) # Create the feature map

            with tf.variable_scope("POOL_2"):
                pool2 = tl.max_pool_2x2(conv2)

            with tf.variable_scope("FC_1"):
                flat1 = tl.fc_flat(pool2)
                h, W, b =  tl.fc(flat1, 1024)
                R3 = tf.nn.l2_loss(W)
                fc1   = tf.nn.relu(h)

            with tf.variable_scope("DROPOUT_1"):
                drop1 = tf.nn.dropout(fc1, self.keep_prob)

            with tf.variable_scope("FC_2"):
                h, W, b =  tl.fc(drop1, 1024)
                R4 = tf.nn.l2_loss(W)
                fc2   = tf.nn.relu( h )

            with tf.variable_scope("DROPOUT_2"):
                drop2 = tf.nn.dropout(fc2, self.keep_prob)

            with tf.variable_scope("OUT"):
                self.out, W, b = tl.fc(drop2, n_classes)

        with tf.name_scope('Cost'):
            self.cost  = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(
                labels=self.labels,
                logits=self.out) )

            self.cost = self.cost + 0.01 * (R1 + R2 + R3 + R4)
