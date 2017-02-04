import tensorflow as tf
import tflearn

class VGG:
    def __init__(self,data_size, n_classes):
        self.name = "VGG"
        self.img_prep = tflearn.ImagePreprocessing()
        # Zero Center (With mean computed over the whole dataset)
        self.img_prep.add_featurewise_zero_center()
        # STD Normalization (With std computed over the whole dataset)
        self.img_prep.add_featurewise_stdnorm()

        # Real-time data augmentation
        self.img_aug = tflearn.ImageAugmentation()
        self.img_aug.add_random_blur()


        # Define model
        self.input = tflearn.input_data(shape=[None, data_size[0]* data_size[1]])#,
                    #data_preprocessing=img_prep,
                    #data_augmentation=img_aug)

        net = tf.reshape(self.input, shape=[-1, data_size[0], data_size[1], 1])
        # Conv 1 - 2
        self.conv1 = tflearn.conv_2d(net, 64, 5, activation='relu', regularizer='L2', name="conv1")
        self.conv2 = tflearn.conv_2d(self.conv1, 64, 5, activation='relu', regularizer='L2', name="conv2")
        # Pooling 1
        self.pool1 = tflearn.layers.conv.max_pool_2d (self.conv2, 2, strides=2, padding='same', name='pool1')
        # Conv 3 - 4
        self.conv3 = tflearn.conv_2d(self.pool1, 64, 5, activation='relu', regularizer='L2', name="conv3")
        self.conv4 = tflearn.conv_2d(self.conv3, 64, 5, activation='relu', regularizer='L2', name="conv4")
        # Pooling 2
        self.pool2 = tflearn.layers.conv.max_pool_2d (self.conv4, 2, strides=2, padding='same', name='pool2')
        # Fully Connected
        self.fc1 = tflearn.fully_connected(self.pool2, 2048, name="fc1")
        self.fc2 = tflearn.fully_connected(self.fc1, 2048, name="fc2")
        self.out = tflearn.fully_connected(self.fc2, n_classes, activation='softmax', name="out")
