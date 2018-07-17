from __future__ import division
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

from App import App

gpu_options = tf.GPUOptions(
    per_process_gpu_memory_fraction=0.25,
    allow_growth=True
    )

config = tf.ConfigProto (allow_soft_placement=True,gpu_options=gpu_options)

class Classifier:
    def __init__(self,folder):
        self.nn_folder = folder
        self.history   = None
        self.cutoff    = None

        # Load the conf file
        try:
            with open(folder + "/conf.json") as json_file:
                conf_data = json.load(json_file)
        except:
            App.error(0, "No configuration file found for classifier " + folder)
            sys.exit()

        self.cutoff     = [conf_data["cutoff_down"],conf_data["cutoff_up"] ]
        self.label_dic  = conf_data["classes"]

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
            self.model = eval( 'model.DNN(conf_data["size"], len(self.label_dic))' )
            self.name = self.model.name

            self.sess = tf.InteractiveSession(config=config, graph=g)
            self.sess.run( tf.global_variables_initializer() )

            # Load the session of the neural network
            ckpt = tf.train.get_checkpoint_state(folder + "/model/")
            if ckpt and ckpt.model_checkpoint_path:
                saver = tf.train.Saver(max_to_keep=2)
                saver.restore(self.sess, ckpt.model_checkpoint_path)
                App.ok(0, "Classifier loaded: " + folder)
            else:
                App.error(0,"No Neural Network found in " + checkpoint_dir)
                quit()

            # Connect the neural net output
            self.net = self.model.output

    def predict(self, batch):
        res = self.sess.run([self.net], feed_dict={self.model.input:batch, self.model.keep_prob: 1.0})[0]
        return res


class Analyzer(threading.Thread):
    def __init__(self, nn_folder,session=False, callable_objects=[], debug=0):
        threading.Thread.__init__(self)

        self.debug = debug
        self.nn_folder = nn_folder
        self.count_run = -1
        self.starting_time = -1
        self.callable_objects = callable_objects

        self.history = None
        self.cutoff  = None

        # Configuration for socket.io from Redis PubSub
        self.stopFlag = threading.Event()
        self.sio_redis = redis.StrictRedis().pubsub()
        self.sio_redis.subscribe("socketio")

        App.log(1, "TensorFlow "+ tf.__version__)
        self.load()
        self.start()

    # Load the network
    def load(self):
        # For each neural network
        self.classifiers = []
        for f in glob.glob(self.nn_folder + "/*"):
            if os.path.isdir(f) and "__pycache__" not in f :
                c = Classifier(f)
                self.classifiers.append(c)
                if self.cutoff is None:
                    self.cutoff = c.cutoff
                elif self.cutoff != c.cutoff:
                    App.error(0,"Classifier must have the same cutoff value ("+str(self.cutoff)+" != "+str(c.cutoff)+") for " + self.nn_folder)
                    sys.exit(-1)

        if len(self.classifiers) < 1:
            App.error(0,"No classifier found in: " + self.nn_folder)
            quit()

    # Loop to receive socket io msg from redis pubsub
    def run(self):
        while not self.stopFlag.wait(0.1):
            msg = self.sio_redis.get_message()
            if msg:
                 try:
                     if msg['type']=="message":
                         data = pickle.loads(msg["data"])
                         if data.get('method')=="emit" and data.get('event') == "JackSource":
                             self.count_run = 0
                 except Exception as e:
                     App.error(0, "Redis message" + str(e) + "------\n" + str(data))

    # Function called by the streamer to predic its current sample
    def execute(self, inputs):
        label_dic   = []
        res         = []
        # BOUNDARY THE VALUES
        inputs["ffts"]["data"] =  np.nan_to_num(inputs["ffts"]["data"])

        # COMPUTE THE ABSOLUTE DATETIME FOR EACH SOURCE
        self.count_run = self.count_run + 1
        hours   = int(self.count_run * 0.5 * (1-inputs["overlap"]) / 3600)
        minutes = int((self.count_run * 0.5 * (1-inputs["overlap"]) % 3600)/60)
        seconds = int(self.count_run * 0.5 * (1-inputs["overlap"]) % 3600 % 60)
        milliseconds = int( ((self.count_run * 0.5 * (1-inputs["overlap"]) % 3600 % 60) * 1000) % 1000)
        sample_time = timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds)

        for source in inputs["sources"]:
            if source["starting_time"] is None:
                source["starting_time"] = time.strftime("%Y-%m-%d-%H-%M-%S")
            date = datetime.strptime(source["starting_time"], "%Y-%m-%d-%H-%M-%S")
            source["time"] = (date + sample_time).isoformat()

        # COMPUTE THE DNN OUTPUTS
        for selector in self.classifiers:
            if selector.name == "selector":
                res = selector.predict(inputs["ffts"]["data"])
                label_dic += list(selector.label_dic)
                break

        for nn in self.classifiers:
            if nn.name != "selector":
                label_dic += list(nn.label_dic)
                weight_selector = res[:,np.where(np.asarray(selector.label_dic)==nn.name)[0][0]]
                res = np.concatenate( (res, np.transpose( np.transpose(nn.predict(inputs["ffts"]["data"]))  * weight_selector) ), axis=1 )

        # AVERAGE WITH PREVIOUS OUTPUTS IF THERE IS AN OVERLAP
        if inputs["overlap"] > 0:
            if self.history is None:
                self.history = np.copy(res)
            elif self.history.shape != res.shape:
                self.history = np.copy(res)

            res = (res + self.history) / 2
            self.history = res

        # APPLY THE DECISION FUNCTION
        detections = []
        for i in range(res.shape[0]):
            detections_classe = []
            a = np.argsort(res[i,:])

            if res[i,a[len(a)-1]] - res[i,a[len(a)-2]] > 0.5:
                # If we detect a super classe, we check if the seond best detection is the specimen
                if label_dic[a[len(a)-1]] in label_dic[a[len(a)-2]] and res[i,a[len(a)-2]] - res[i,a[len(a)-3]] > 0.2:
                    detections_classe.append(label_dic[a[len(a)-2]])
                else:
                    detections_classe.append(label_dic[a[len(a)-1]])

            else:
                detections_classe.append("unknown")
            detections.append(detections_classe)

        # BUILD AND TRANSMIT RESULT as an array of channel
        results = []
        for i in range(0, inputs["ffts"]["data"].shape[0]):
            channel = {}
            channel["outputs"]      = res[i,:]
            channel["detections"]   = detections[i]
            channel["samplerate"]   = inputs["samplerate"]
            try:
                channel["audio"]    = inputs["audio"][:,i]
            except:
                channel["audio"]    = inputs["audio"] # mono
            channel["fft"]          = {
                "data":inputs["ffts"]["data"][i,:],
                "time_scale":inputs["ffts"]["time_scale"],
                "freq_scale":inputs["ffts"]["freq_scale"],
                "size":inputs["ffts"]["size"]
                }

            for m in inputs["mapping"]:
                if m[1] == "analyzer:input_"+str(i):
                    break
            channel["mapping"] = m
            for source in inputs["sources"]:
                if source["name"] in m[0]:
                 break
            channel["time"] = source["time"]
            results.append(channel)

            App.log(3, source["time"] + "\tchannel: " + channel["mapping"][0] + '\t' + str(detections[i]))

        # CALL THE CONSUMERS
        for obj in self.callable_objects:
            obj.execute(results, label_dic)
