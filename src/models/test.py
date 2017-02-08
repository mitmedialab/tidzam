import tensorflow as tf
import tflearn

class DNN:
    def __init__(self,data_size, n_classes):
        self.name = "DNN"
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
        self.conv1 = tflearn.conv_2d(net, 32, 5, activation='relu', regularizer='L2', name="conv1")
        # Pooling 1
        self.pool1 = tflearn.layers.conv.max_pool_2d (self.conv1, 2, strides=2, padding='same', name='pool1')
        # Conv 3 - 4
        # Fully Connected
        self.fc1 = tflearn.fully_connected(self.pool1, 128, activation='relu', name="fc1")
        self.drop1 = tflearn.layers.core.dropout (self.fc1, 0.5, name='Dropout1')
        self.out = tflearn.fully_connected(self.drop1, n_classes, activation='linear', name="out")
