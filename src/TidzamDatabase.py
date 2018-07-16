from __future__ import print_function
from __future__ import division

import sys, os
import numpy as np
import optparse
import random
import math
import copy
from matplotlib import pyplot as plt
import glob
import time
import re

import multiprocessing as mp
import atexit

from scipy import signal
import soundfile as sf
import sounddevice as sd
import traceback

from App import App
import json

###################################SOUND PROCESS##########################################


#This function blend a sound inside a given background and repeat the process for a given number of time
#to produce multiple samples with the same sound at different position
def blend_sound_to_background_severals_positions(sound_data , ambiant_sound_data , number_of_instance):
    new_outputs = []
    for i in range(number_of_instance):
        new_outputs.append(blend_sound_to_background(sound_data , ambiant_sound_data))
    return new_outputs

#This function blend a sound inside a given background at a random position
def blend_sound_to_background(sound_data , ambiant_sound_data):
    volume_factor = np.max(sound_data)

    sound_data = sound_data / np.max(sound_data) * volume_factor
    ambiant_sound_data = ambiant_sound_data / np.max(ambiant_sound_data) * volume_factor

    sound_data_position = int(random.randint(0 , len(ambiant_sound_data) - len(sound_data)) )

    if sound_data_position < 0:
        raise Exception("Corrupted Data")

    signal_sum = ambiant_sound_data[:]
    for i in range(len(sound_data)):
        try:
            signal_sum[sound_data_position + i] += sound_data[i]
        except:
            signal_sum[sound_data_position + i] += sound_data[i,0]

    mixed_signal = signal_sum / np.max(signal_sum) * volume_factor
    return mixed_signal

def blend_multiple_sound_to_background(sounds_data , ambiant_sound_data):
    for sound_data in sounds_data:
        ambiant_sound_data = blend_sound_to_background(sound_data , ambiant_sound_data)
    return ambiant_sound_data

def convert_to_monochannel(input):
    return input if len(input.shape) <= 1 else input[: , 0]

###################################SOUND PROCESS##########################################

def get_spectrogram(data, samplerate, channel=0,  show=False, cutoff=[20,170]):
    plt.ion()
    fs, t, Sxx = signal.spectrogram(data, samplerate, nfft=1024, noverlap=128)
    # editor between 1-8 Khz
    if cutoff is not []:
        Sxx = Sxx[[x for x in range(cutoff[0],cutoff[1])], :]*1000
        fs = fs[[x for x in range(cutoff[0],cutoff[1])]]
    # Normalize and cutoff
    Sxx = np.maximum(Sxx/np.max(Sxx), np.ones((Sxx.shape[0], Sxx.shape[1]))*0.01)

    if show is True:
        plt.figure(channel, figsize=(7, 7))
        plt.pcolormesh(t, fs, Sxx)
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.show()
        plt.pause(0.1)
        sd.play(data, samplerate)
        time.sleep(0.5)

    size = [Sxx.shape[0], Sxx.shape[1]]
    Sxx = np.reshape(Sxx, [1, Sxx.shape[0]*Sxx.shape[1]] )
    return fs, t, Sxx, size

def play_spectrogram_from_stream(file, show=False, callable_objects = [], overlap = 0, cutoff=[20,170]):

    with sf.SoundFile(file, 'r') as f:
        while f.tell() < len(f):
            data = f.read(int(f.samplerate/2))

            for i in range(0,f.channels):
                if f.channels > 1:
                    fs, t, Sxx, size = get_spectrogram(data[:,i], f.samplerate, i,  show=show, cutoff=cutoff)
                else:
                    fs, t, Sxx, size  = get_spectrogram(data, f.samplerate, i, show=show, cutoff=cutoff)

                if i == 0:
                    Sxxs = Sxx
                    fss = fs
                    ts = t
                else:
                    Sxxs = np.concatenate((Sxxs, Sxx), axis=0)
                    fss = np.concatenate((fss, fs), axis=0)
                    ts = np.concatenate((ts, t), axis=0)

            for obj in callable_objects:
                obj.run(Sxxs, fss, ts, [data, f.samplerate], overlap=overlap)

            f.seek(int(-int(f.samplerate/2)*overlap), whence=sf.SEEK_CUR)

        return Sxx, t, fs, size

def play_spectrogram_from_stream_data(data , samplerate , channels , show=False, callable_objects = [], overlap = 0):
    idx = 0
    while idx < len(data):
        trunc_data = data[ idx : idx + samplerate // 2]

        for i in range(0,channels):
            if channels > 1:
                fs, t, Sxx, size = get_spectrogram(trunc_data[:,i], samplerate, i,  show=show)
            else:
                fs, t, Sxx, size  = get_spectrogram(trunc_data, samplerate, i, show=show)

            if i == 0:
                Sxxs = Sxx
                fss = fs
                ts = t
            else:
                Sxxs = np.concatenate((Sxxs, Sxx), axis=0)
                fss = np.concatenate((fss, fs), axis=0)
                ts = np.concatenate((ts, t), axis=0)

            for obj in callable_objects:
                obj.run(Sxxs, fss, ts, [trunc_data, samplerate], overlap=overlap)

            idx += samplerate // 2 + int(-int(samplerate/2)*overlap)

    return Sxx, t, fs, size

def sorted_nicely( l ):
    """ Sort the given iterable in the way that humans expect."""
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    return sorted(l, key = alphanum_key)

class LabelNode:
    def __init__(self , name):
        self.child_list = []
        self.name = name

    def find_child(self , name):
        for child in self.child_list:
            if child.name == name:
                return child
        return None

    def add_child(self , name):
        self.child_list.append(LabelNode(name))
        return self.child_list[-1]

    def get_child_number(self):
        child_number = len(self.child_list)
        for child in self.child_list:
            child_number += child.get_child_number()
        return child_number

    def show(self):
        print(self.name)
        print("go_down")
        for child in self.child_list:
            child.show()
        print("can't go down")

class LabelTree(LabelNode):
    def __init__(self):
        LabelNode.__init__(self , '')

class Dataset:
    def __init__(self, name="/tmp/dataset",conf_data = None, p=0.9, max_file_size=1000, split=0.9, cutoff=[20,170]):
        self.cur_batch = 0
        self.size           = None
        self.max_file_size  = max_file_size
        self.name           = name

        self.fileID         = 0
        self.files_count    = 0
        self.batchIDfile    = 0
        self.batchfile      = []
        self.cur_batch      = 0

        self.data           = []
        self.labels         = []
        self.batch_size     = 64

        self.mode                  = None
        self.thread_count_training = 3
        self.thread_count_testing  = 1
        self.threads               = []
        self.queue_training        = None
        self.queue_maxsize         = 20
        self.split                 = split

        self.conf_data = conf_data
        self.class_tree = None
        self.expert_mode = conf_data["expert_mode"]
        self.expert_labels_dic = []

        self.cutoff = cutoff
        if(self.conf_data["cutoff_up"] is not None and self.conf_data["cutoff_down"] is not None ):
            self.cutoff = [ int(conf_data["cutoff_down"]), int(conf_data["cutoff_up"]) ]

        self.cutoff = cutoff
        if(self.conf_data["cutoff_up"] is not None and self.conf_data["cutoff_down"] is not None ):
            self.cutoff = [ int(conf_data["cutoff_down"]), int(conf_data["cutoff_up"]) ]

        atexit.register(self.exit)

        self.load(self.name)

    def exit(self):
        App.log(0, " Exit.")
        for t in self.threads:
            t. terminate()

    def build_labels_dic(self):
        are_labels_wrong = False
        try:
            if "object" not in self.conf_data:
                self.conf_data["classes"] = []
                for cl in glob.glob(self.name + "/*"):
                    if os.path.isdir(cl):
                        cl = cl.split("/")
                        cl = cl[len(cl)-1].split("(")[0]
                        if cl not in self.conf_data["classes"] and cl != "unchecked":
                            self.conf_data["classes"].append(cl)

            labels_dic = (np.load(self.conf_data["out"] + "/labels_dic.npy")).tolist()

            if len(labels_dic) > len(self.conf_data["classes"]):
                are_labels_wrong = True
            for label in labels_dic:
                if label not in self.conf_data["classes"]:
                    are_labels_wrong = True

            if not are_labels_wrong:
                self.conf_data["classes"] = labels_dic
        except:
            App.log(0 , "Couldn't find a label dic , a new one will be build")

        if are_labels_wrong:
            App.log(0 , "CARE : The model was build for different labels")
            App.log(0 , "previous model classes : " + str(labels_dic))
            App.log(0 , "current model classes : " + str(self.conf_data["classes"]))
            exit(0)

        self.conf_data["classes"].sort()


    def build_labels_tree(self):
        self.class_tree = LabelTree()
        self.build_labels_dic()
        for cl in self.conf_data["classes"]:
            current_node = self.class_tree
            cl_s = cl.split("_")
            for sub_cl in cl_s:
                node = current_node.find_child(sub_cl)
                if node is not None:
                    current_node = node
                else:
                    current_node = current_node.add_child(sub_cl)

    def build_expert_labels_dic_rec(self , node):
        for child in node.child_list:
            self.expert_labels_dic.append(child.name)
        for child in node.child_list:
            self.build_expert_labels_dic_rec(child)


    def build_output_vector(self , class_index):
        label = np.zeros((1,len(self.out_labels)))
        if not self.expert_mode:
            label[0,class_index] = 1
        else:
            labels_classes = self.conf_data["classes"][class_index].split('_')
            for sub_label in labels_classes:
                label[0 , self.out_labels.index(sub_label)] = 1

        return label


    def load(self, folder ):
        self.name   = folder
        ctx = mp.get_context('spawn')
        self.queue_training  = ctx.Queue(self.queue_maxsize)
        self.queue_testing   = ctx.Queue(self.queue_maxsize)

        # Build classe dictionnary
        self.build_labels_tree()
        if self.expert_mode:
            self.build_expert_labels_dic_rec(self.class_tree)
            self.out_labels = self.expert_labels_dic
            print(self.out_labels)
        else:
            self.out_labels = self.conf_data["classes"]

        App.log(0 ,"trained expert classes are : " + str(self.expert_labels_dic))
        App.log(0 ,"trained classes are : " + str(self.conf_data["classes"]))

        # Extract file for training and testing
        if self.split == None:
            App.log(0, "You must specify the attribute --split for the proportion of testing sample")
            return

        self.files_training = {}
        self.files_testing  = {}

        if "object" in self.conf_data:
            cl_paths_list = [np.array(glob.glob(object["path"] + "*/**/*.wav", recursive=True)) for object in self.conf_data["object"]]
            cl_names = [object["name"] for object in self.conf_data["object"]]
            cl_type = [object["type"] for object in self.conf_data["object"]]
        else:
            cl_paths_list = [np.array(glob.glob(self.name + "/" + cl + "*/**/*.wav", recursive=True)) for cl in self.conf_data["classes"]]
            cl_names = self.conf_data["classes"]

        raw, time, freq, self.size   = play_spectrogram_from_stream(cl_paths_list[0][0], cutoff=self.cutoff)

        #if self.conf_data is None:
        for cl , paths in zip(cl_names , cl_paths_list):
            files_cl = paths
            idx = np.arange(len(files_cl))
            np.random.shuffle(idx)
            self.files_training[cl] = files_cl[ idx[:int(len(idx)*self.split)] ]
            self.files_testing[cl]  = files_cl[ idx[int(len(idx)*self.split):] ]
            App.log(0, "training / testing datasets for " + cl + ": " + str(len(self.files_training[cl])) + " / " +str(len(self.files_testing[cl]))+" samples" )

        dictionnary = None if "object" not in self.conf_data else self.conf_data["object"]

        # Start the workers
        for i in range(self.thread_count_training):
            t = ctx.Process(target=self.build_batch_onfly,
                    args=(self.queue_training, self.files_training, self.batch_size ,
                          dictionnary))
            t.start()
            self.threads.append(t)

        for i in range(self.thread_count_testing):
            t = ctx.Process(target=self.build_batch_onfly,
                    args=(self.queue_testing, self.files_testing, self.batch_size))
            t.start()
            self.threads.append(t)

        while self.queue_training.empty():
            pass
        self.data, self.labels = self.queue_training.get()

    def next_batch(self, batch_size=128, testing=False):
        if testing is False:
            if self.queue_training.qsize() == 0:
                App.log(0, "Next batch size on fly is waiting (queue empty).")
            while self.queue_training.empty():
                pass
            return self.queue_training.get()
        else:
            if self.queue_testing.qsize() == 0:
                App.log(0, "Next batch size on fly is waiting (queue empty).")
            while self.queue_testing.empty():
                pass
            return self.queue_testing.get()

    def build_batch_onfly(self, queue, files, batch_size=64 , dictionnary = None):
        if dictionnary is not None:
            #List all the ambiant class
            ambiant_cl = [object["name"] for object in dictionnary if object["type"] == "background"]
            type_dictionnary = dict()
            augmentation_dictionnary = dict()
            for cl in  dictionnary:
                type_dictionnary[cl["name"]] = cl["type"]
                if "is_augmented" in cl and cl["is_augmented"]:
                    augmentation_dictionnary[cl["name"]] = cl["is_augmented"]

        while True:
            while self.queue_training.full():
                pass

            count = math.ceil(batch_size / len(self.conf_data["classes"]))
            data = []
            labels = []

            for i , cl in enumerate(self.conf_data["classes"]):
                #pick random sample (only get the indexes)
                files_cl = files[cl]
                idx = np.arange(len(files_cl))
                np.random.shuffle(idx)
                idx = idx[:count]

                #for each picked sample -> process
                for id in idx:
                    sound_data , samplerate = sf.read(files_cl[id])
                    sound_data = sound_data if len(sound_data.shape) <= 1 else convert_to_monochannel(sound_data)

                    if dictionnary is not None and type_dictionnary[cl] == "content" and cl in augmentation_dictionnary:
                        ambiant_file = random.choice(files[random.choice(ambiant_cl)])
                        ambiant_sound , samplerate = sf.read(ambiant_file)
                        ambiant_sound = ambiant_sound if len(ambiant_sound.shape) <= 1 else convert_to_monochannel(ambiant_sound)
                        try:
                            sound_data = blend_sound_to_background(sound_data , ambiant_sound)
                        except:
                            App.Log(0 , "One of these 2 files are corrupted (or probably both) : " , files_cl[id] , " , " , ambiant_file)


                    try:
                        raw, time, freq, size   = play_spectrogram_from_stream(files_cl[id],cutoff=self.cutoff)
                        raw                     = np.nan_to_num(raw)
                        raw                     = np.reshape(raw, [1, raw.shape[0]*raw.shape[1]])
                        label                   = self.build_output_vector(i)

                        try:
                            data = np.concatenate((data, raw), axis=0)
                            labels = np.concatenate((labels, label), axis=0)
                        except:
                            data   = raw
                            labels = label

                    except Exception as e :
                        App.log(0, "Bad file" + str(e))
                        traceback.print_exc()

            #Shuffle the final batch
            idx = np.arange(data.shape[0])
            np.random.shuffle(idx)
            data   = data[idx,:]
            labels = labels[idx,:]

            data   = data[:batch_size,:]
            labels = labels[:batch_size,:]

            queue.put([data, labels])

        '''
        while True:
            while self.queue_training.full():
                pass

                        try:
                            data = np.concatenate((data, raw), axis=0)
                            labels = np.concatenate((labels, label), axis=0)
                        except:
                            data   = raw
                            labels = label

                    except Exception as e :
                        App.log(0, "Bad file" + str(e))
                        traceback.print_exc()

            #Shuffle the final batch
            idx = np.arange(data.shape[0])
            np.random.shuffle(idx)
            data   = data[idx,:]
            labels = labels[idx,:]

            data   = data[:batch_size,:]
            labels = labels[:batch_size,:]

            queue.put([data, labels])

    def get_nb_classes(self):
        return len(self.conf_data["classes"])
    '''
