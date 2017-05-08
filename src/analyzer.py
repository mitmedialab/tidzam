import numpy as np
import math
import sys
import glob, os
from datetime import *
import time

import threading
import tensorflow as tf
import tflearn
import importlib
import socketio

import redis
import time
import pickle
import json


import vizualisation as vizu
import data as tiddata

config = tflearn.config.init_graph (
    num_cores=1,
    gpu_memory_fraction=0.75,
    soft_placement=False)

class Classifier:
    def __init__(self,folder):
        self.dataw = 150
        self.datah = 186
        self.nn_folder = folder
        self.history   = None

        self.label_dic = np.load(folder + "/labels.dic.npy").astype(str)

        # Get Neural Net name
        path = self.nn_folder.split('/')
        name_file = path[len(path) - 1 ]
        if name_file == '':
            name_file = path[len(path) - 2 ]

        # import the model
        sys.path.append('./')
        exec("import "+self.nn_folder.replace("/",".")+".model as model")

        # Create a new graph and load it in a new session
        g = tf.Graph()
        with g.as_default() as g:
            network = eval("model.DNN([self.dataw, self.datah], len(self.label_dic))")
            self.name = network.name

            with tf.Session( graph = g ) as sess:
                self.classifier = tflearn.DNN(network.out,
                    tensorboard_dir= self.nn_folder + "/",
                    tensorboard_verbose=0)

                sess.run(tf.global_variables_initializer())

        try:
            print('Loading : ' + self.nn_folder + "." + network.name)
            self.classifier.load(self.nn_folder + "/" + network.name, create_new_session=False)

            # Add Softmax layer for decision function
            self.classifier.net = tflearn.activations.softmax (self.classifier.net)
            self.classifier.predictor = tflearn.Evaluator([self.classifier.net],
                                   session=self.classifier.session,model=None)
        except:
            print('Unable to load model: ' + self.nn_folder)
            quit()

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
            time_relative = "0:0:0:0ms"
            if stream == self.old_stream:
                time_relative = "0:0:0:500ms"
            self.old_stream = stream

        # From audio file, compute relative time from beginning
        else:
            self.count_run = self.count_run + 1
            time_relative = str(int(self.count_run * 0.5 * (1-overlap) / 3600)) + ":" + \
                    str( int((self.count_run * 0.5 * (1-overlap) % 3600)/60)) + ":" + \
                    str( int(self.count_run * 0.5 * (1-overlap) % 3600 % 60)) + ":" + \
                    str( int( ((self.count_run * 0.5 * (1-overlap) % 3600 % 60) * 1000) % 1000) ) + "ms"

        # Extract the datetime from the filename
        date = stream.split("/")
        date = date[len(date)-1].split(".")[0].split("-")
        date.pop(0)
        date = ''.join(date)
        date = datetime.strptime(date, "%Y%m%d%H%M%S")
        sample_time = time_relative.replace("ms","").split(":")
        sample_time = timedelta(
                hours=int(sample_time[0]),
                minutes=int(sample_time[1]),
                seconds=int(sample_time[2]),
                milliseconds=int(sample_time[3]))
        sample_timestamp = (date + sample_time).isoformat()


        classes = []
        label_dic = []
        res = []
        # GENERAL CLASSIFIER
        for nn in self.classifiers:
            if nn.name[:8] == 'selector':
                res_general       = nn.classifier.predict(Sxxs)

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
                    res_expert = nn.classifier.predict([Sxxs[channel,:]])[0]

                    if nn.history is None:
                        nn.history = res_expert

                    res_average = list(np.mean([res_expert, nn.history ], axis=0))
                    a = np.argmax(res_average)
                    a = np.argsort(res_average)

                    if res_average[a[len(a)-1]] - res_average[a[len(a)-2]] > 0.2:
                        classes[channel] = classes[channel] + '-' + str(nn.label_dic[ a[len(a)-1] ]) #+ ' ('  + str(a) + ')'

                    if overlap > 0:
                        res[channel] += res_expert

                    nn.history = res_expert

                # Fill in with zeros for all other expert classifiers
                elif nn.name != 'selector':
                    res[channel] += list(np.zeros(len(nn.label_dic)) )

            if self.debug > 1:
                print(sample_timestamp + "\tchannel" + str(channel+1) + '\t' + classes[channel])

        # BUILD AND TRANSMIT RESULT
        for obj in self.callable_objects:
            obj.execute(res, classes, label_dic, sound_obj, sample_timestamp)
