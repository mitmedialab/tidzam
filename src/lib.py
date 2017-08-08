import tensorflow as tf

def weight_variable(shape):
  initial = tf.truncated_normal(shape, stddev=0.1)
  tf.summary.histogram("W", initial)
  return tf.Variable(initial, "W")

def bias_variable(shape):
  initial = tf.constant(0.1, shape=shape)
  tf.summary.histogram("b", initial)
  return tf.Variable(initial, "b")

def conv2d(x, nb_kernel, kernel_size=5, stride=1):
    W         = weight_variable([kernel_size, kernel_size, int(x.shape[3]), nb_kernel])
    b         = bias_variable([nb_kernel])
    return [tf.nn.relu(tf.nn.conv2d(x, W, strides=[stride, stride, stride, stride], padding='SAME') + b), W, b]

def max_pool_2x2(x):
  return tf.nn.max_pool(x, ksize=[1, 2, 2, 1],
                        strides=[1, 2, 2, 1], padding='SAME')

def fc_flat(x):
    return tf.reshape(x, [-1, int(x.shape[1] * x.shape[2] * x.shape[3]) ])

def fc(x, size):
    W = weight_variable( [ int(x.shape[1]), size] )
    b = bias_variable( [size] )
    h = tf.matmul(x, W) + b
    tf.summary.histogram("pre-activation", h)
    return h, W, b
