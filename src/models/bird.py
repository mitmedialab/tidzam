import tensorflow as tf
import tflearn

class DNN:
    def __init__(self,data_size, n_classes):
        self.name = "birds"
        self.show_kernel_map = []

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
        self.conv1 = tflearn.conv_2d(net, 128, 5, activation='relu', regularizer='L2', name="conv1")
        self.conv2 = tflearn.conv_2d(self.conv1, 128, 5, activation='relu', regularizer='L2', name="conv2")

        self.show_kernel_map.append(self.conv1)
        self.show_kernel_map.append(self.conv2)
        # Pooling 1
        self.pool1 = tflearn.layers.conv.max_pool_2d (self.conv2, 2, strides=2, padding='same', name='pool1')
        #self.drop1 = tflearn.layers.core.dropout (self.pool1, 0.5, name='Dropout2')
        # Conv 3 - 4
        self.conv3 = tflearn.conv_2d(self.pool1, 128, 5, activation='relu', regularizer='L2', name="conv3")
        self.conv4 = tflearn.conv_2d(self.conv3, 128, 5, activation='relu', regularizer='L2', name="conv4")
        self.show_kernel_map.append(self.conv3)
        self.show_kernel_map.append(self.conv4)
        # Pooling 1
        self.pool2 = tflearn.layers.conv.max_pool_2d (self.conv4, 2, strides=2, padding='same', name='pool2')
        # Conv 3 - 4
        # Fully Connected
        self.fc1 = tflearn.fully_connected(self.pool2, 2048, activation='relu', name="fc1")
        self.drop2 = tflearn.layers.core.dropout (self.fc1, 0.5, name='Dropout1')

        self.fc2 = tflearn.fully_connected(self.drop2, 2048, activation='relu', name="fc2")
        self.drop3 = tflearn.layers.core.dropout (self.fc2, 0.5, name='Dropout2')

        self.out = tflearn.fully_connected(self.drop3, n_classes, activation='linear', name="out")
