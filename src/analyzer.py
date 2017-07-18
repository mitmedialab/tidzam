import numpy as np
import math
import sys
import glob, os
from datetime import *
import time

import threading
import tensorflow as tf
import importlib
import socketio

import redis
import time
import pickle
import json


import vizualisation as vizu
import data as tiddata

config = tf.ConfigProto (allow_soft_placement=True)

class Classifier:
    def __init__(self,folder):
        self.dataw = 150
        self.datah = 186
        self.nn_folder = folder
        self.history   = None
        self.label_dic = np.load(folder + "/labels_dic.npy").astype(str)

        # Get Neural Net name
        path = self.nn_folder.split('/')
        name_file = path[len(path) - 1 ]
        if name_file == '':
            name_file = path[len(path) - 2 ]

        # import the model
        sys.path.append('./')
        exec("import "+self.nn_folder.replace("/",".")+".model as model")

        g = tf.Graph()
        with g.as_default() as g:
            self.model = eval( "model.DNN([self.dataw,self.datah], len(self.label_dic))" )
            self.name = self.model.name

            self.sess = tf.InteractiveSession(config=config, graph=g)
            self.sess.run( tf.global_variables_initializer() )

            # Load the session of the neural network
            ckpt = tf.train.get_checkpoint_state(folder + "/model/")
            if ckpt and ckpt.model_checkpoint_path:
                saver = tf.train.Saver(max_to_keep=2)
                saver.restore(self.sess, ckpt.model_checkpoint_path)
                print("Network loaded: " + folder)
            else:
                print("Not Neural Network found in " + checkpoint_dir)
                quit()

            # Add the final softmax decision function
            self.net = tf.nn.softmax (self.model.out)

    def predict(self, batch):
        return self.sess.run([self.net], feed_dict={self.model.input:batch, self.model.keep_prob: 1.0})[0]


class Analyzer(threading.Thread):
    def __init__(self, nn_folder,session=False, callable_objects=[], debug=0):
        threading.Thread.__init__(self)

        self.debug = debug
        self.nn_folder = nn_folder
        self.count_run = -1
        self.old_stream = ""
        self.callable_objects = callable_objects

        self.history = None

        # Configuration for socket.io from Redis PubSub
        self.stopFlag = threading.Event()
        self.sio_redis = redis.StrictRedis().pubsub()
        self.sio_redis.subscribe("socketio")

        print("======== TENSOR FLOW ========")
        print("TensorFlow "+ tf.__version__)
        self.load()
        self.start()

    # Load the network
    def load(self):
        # For each neural network
        self.classifiers = []
        for f in glob.glob(self.nn_folder + "/*"):
            if os.path.isdir(f) and "__pycache__" not in f :
                self.classifiers.append(Classifier(f))

        if len(self.classifiers) < 1:
            print("No classifier found in: " + self.nn_folder)
            quit()

    # Loop to receive socket io msg from redis pubsub
    def run(self):
        while not self.stopFlag.wait(0.1):
            msg = self.sio_redis.get_message()
            if msg:
                try:
                    if msg['type']=="message":
                        data = str(pickle.loads(msg["data"])["data"]).replace("'",'"')
                        obj = json.loads(data)
                        if type(obj) is not list:
                            if obj.get('sys'):
                                # If the source is change, we reset the counter
                                if obj["sys"].get("source"):
                                    self.count_run = 0
                except:
                    print("** Analyzer ** Error on redis message" + data)

    # Function called by the streamer to predic its current sample
    def execute(self, Sxxs, fs, t, sound_obj, overlap=0, stream=None):
        # Compute GMT Timestamp for current sampe

        # If Real-Time Stream stream, change date for current date
        if "http" in stream:
            stream = time.strftime("generated/today-%Y-%m-%d-%H-%M-%S.opus")
            hours = minutes = seconds = milliseconds = 0
            #time_relative = "0:0:0:0ms"
            if stream == self.old_stream:
                milliseconds = 500
                #time_relative = "0:0:0:500ms"
            self.old_stream = stream

        # From audio file, compute relative time from beginning
        else:
            self.count_run = self.count_run + 1
            hours   = int(self.count_run * 0.5 * (1-overlap) / 3600)
            minutes = int((self.count_run * 0.5 * (1-overlap) % 3600)/60)
            seconds = int(self.count_run * 0.5 * (1-overlap) % 3600 % 60)
            milliseconds = int( ((self.count_run * 0.5 * (1-overlap) % 3600 % 60) * 1000) % 1000)

        sample_time = timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds)

        # Extract the datetime from the filename
        try:
            date = stream.split("/")
            date = date[len(date)-1].split(".")[0].split("-")
            date.pop(0)
            date = ''.join(date)
            date = datetime.strptime(date, "%Y%m%d%H%M%S")
        except:
            date = datetime(1970, 1, 1, 0, 0, 0, 0)
        sample_timestamp = (date + sample_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]



        classes = []
        label_dic = []
        res = []
        # GENERAL CLASSIFIER
        for nn in self.classifiers:
            if nn.name[:8] == 'selector':
                res_general       = nn.predict(Sxxs)

                if nn.history is None:
                    nn.history = res_general

                label_dic += list(nn.label_dic)
                for channel in range(0, Sxxs.shape[0]):
                    res.append(res_general[channel])
                    # Qverage current classifier output with previous (to reduce fault positive)
                    if overlap > 0:
                        res[channel] = list(np.mean([res_general[channel], nn.history[channel] ], axis=0))

                    out_classes = ""
                    a = np.argmax(res[channel])
                    a = np.argsort(res[channel])
                    # If the trusting interval between two first options is bigger that 20%
                    if res[channel][a[len(a)-1]] - res[channel][a[len(a)-2]] > 0.2:
                        out_classes = str(nn.label_dic[a[len(a)-1]])
                    else:
                        out_classes = 'unknow'
                    classes.append(out_classes)
                break
        nn.history = res_general

        # EXPERT CLASSIFIER
        for channel in range(0, Sxxs.shape[0]):
            for nn in self.classifiers:
                # Complete the dictionnary with other classifier
                if nn.name != 'selector' and channel == 0:
                    label_dic += list(nn.label_dic)


                # Request the expert classifier for the detected classe
                pred = classes[channel].split('-')
                if nn.name == pred[0]:
                    res_expert = nn.predict([Sxxs[channel,:]])[0]

                    if nn.history is None:
                        nn.history = res_expert

                    # Average with previous samples
                    if overlap > 0:
                        res_average = list(np.mean([res_expert, nn.history ], axis=0))
                    else:
                        res_average = res_expert

                    # Decision functions
                    a = np.argmax(res_average)
                    a = np.argsort(res_average)
                    if res_average[a[len(a)-1]] - res_average[a[len(a)-2]] > 0.3:
                        classes[channel] = classes[channel] + '-' + str(nn.label_dic[ a[len(a)-1] ]) #+ ' ('  + str(a) + ')'

                    # Store result and history
                    res[channel] += res_average
                    nn.history = res_expert

                # Fill in with zeros for all other expert classifiers
                elif nn.name != 'selector':
                    res[channel] += list(np.zeros(len(nn.label_dic)) )

            if self.debug > 1:
                print(sample_timestamp + "\t\tchannel" + str(channel+1) + '\t' + classes[channel])

        # BUILD AND TRANSMIT RESULT
        for obj in self.callable_objects:
            obj.execute(res, classes, label_dic, sound_obj, sample_timestamp)
