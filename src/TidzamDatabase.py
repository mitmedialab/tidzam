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

def get_spectrogram(data, samplerate, channel=0,  show=False):
    plt.ion()
    fs, t, Sxx = signal.spectrogram(data, samplerate, nfft=1024, noverlap=128)
    # editor between 1-8 Khz
    Sxx = Sxx[[x for x in range(20,170)], :]*1000
    # Normalize and cutoff
    Sxx = np.maximum(Sxx/np.max(Sxx), np.ones((Sxx.shape[0], Sxx.shape[1]))*0.01)
    fs = fs[[x for x in range(20,170)]]

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

def play_spectrogram_from_stream(file, show=False, callable_objects = [], overlap = 0):
    with sf.SoundFile(file, 'r') as f:
        while f.tell() < len(f):
            data = f.read(int(f.samplerate/2))

            for i in range(0,f.channels):
                if f.channels > 1:
                    fs, t, Sxx, size = get_spectrogram(data[:,i], f.samplerate, i,  show=show)
                else:
                    fs, t, Sxx, size  = get_spectrogram(data, f.samplerate, i, show=show)

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
    def __init__(self, name="/tmp/dataset",conf_data = None, p=0.9, data_size=(150,186), max_file_size=1000, split=0.9 , expert_mode=True):
        self.cur_batch = 0
        self.dataw          = data_size[0]
        self.datah          = data_size[1]
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
        self.expert_mode = expert_mode
        self.expert_labels_dic = []

        atexit.register(self.exit)
        self.load(self.name)

    def exit(self):
        App.log(0, " Exit.")
        for t in self.threads:
            t. terminate()

    def load(self, input):
        if os.path.isdir(input) is False and input != "":
            App.log(0 , "file_mode")
            self.mode = "file"
            self.load_file(input)
        else:
            self.mode = "onfly"
            self.load_onfly(input)

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

            labels_dic = np.load(self.conf_data["out"] + "/labels_dic.npy")

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


    def load_onfly(self, folder ):
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

    def next_batch_onfly(self, batch_size=128, testing=False):
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
                        raw, time, freq, size   = play_spectrogram_from_stream(files_cl[id])
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

            count = math.ceil(batch_size / len(self.conf_data["classes"]))
            data   = []
            labels = []
            for i, cl in enumerate(self.conf_data["classes"]):
                files_cl = files[cl]
                idx = np.arange(len(files_cl))
                np.random.shuffle(idx)
                idx = idx[:count]
                for id in idx:
                    try:
                        raw, time, freq, size   = play_spectrogram_from_stream(files_cl[id])
                        raw                     = np.nan_to_num(raw)
                        raw                     = np.reshape(raw, [1, raw.shape[0]*raw.shape[1]])
                        label                   = np.zeros((1,len(self.conf_data["classes"])))
                        label[0,i]              = 1
                        try:
                            data = np.concatenate((data, raw), axis=0)
                            labels = np.concatenate((labels, label), axis=0)
                        except:
                            data   = raw
                            labels = label

                    except Exception as e :
                        App.log(0, "Bad file" + str(e))
                        traceback.print_exc()

            idx = np.arange(data.shape[0])
            np.random.shuffle(idx)
            data   = data[idx,:]
            labels = labels[idx,:]

            data   = data[:batch_size,:]
            labels = labels[:batch_size,:]

            queue.put([data, labels])
            '''

    def load_file(self, file):
        self.cur_batch = 0
        self.name = file
        App.log(0, "\n===============")
        App.log(0, "Load " + self.name)
        App.log(0, "===============")
        try:
            self.fileID = self.files_count = self.nb_files()
            # Try to load metadata information
            try:
                f = np.load(self.name+"-0.npz")
                self.dataw              = f["dataFormat"][0]
                self.datah              = f["dataFormat"][1]
                self.max_file_size      = f["maxfilesize"]
                self.files_count        = f["files_count"]
                self.count_samples      = f["count_samples"]
                self.nb_features_count  = f["nb_features_count"]
                self.count_by_classe    = f["count_by_classe"]
            # Else generate them
            except:
                self.count_samples      = self.nb_samples()
                self.nb_features_count  = self.get_nb_features()
                self.count_by_classe    = self.get_sample_count_by_classe()
                App.log(0, "No metadata information found.")

            # Load the last dataset chunk
            f = np.load(self.name+"-"+str(self.fileID)+".npz")
            self.data   = f["data"]
            self.labels = f["labels"]
            self.conf_data["classes"] = list(np.load(self.name+"_labels_dic.npy"))

            # Print dataset information
            App.log(0, str(self.count_samples) +" samples of " +
                    str(self.nb_features_count ) + " features in " +
                    str(len(self.get_classes()) ) + " classes.")

            App.log(0, self.get_classes())
            App.log(0, "Samples distribution:")
            App.log(0, self.count_by_classe)

        except Exception as ex:
             App.log(0, "File not found: " + file + str(ex))
             self.data = []
             self.conf_data["classes"] = []
             self.labels = []

    def save(self,name=None):
        if name is None:
            name = self.name

        # Extract dataset name in filename
        tmp_name = name.split("/")
        tmp_name = tmp_name[len(tmp_name)-1]
        tmp_name = tmp_name.split("-")[0]
        try:
            np.savez(name + "-" + str(self.fileID) + ".npz",
                data=self.data,
                labels=self.labels
                )
            np.save(name + "_labels_dic", self.conf_data["classes"])
        except:
            App.log(0, "Unable to save the dataset (write permission ?)")

    def save_meta(self):
        App.log(0, "\nGenerate metadata information.")
        self.files_count        = self.nb_files()
        self.count_samples      = self.nb_samples()
        self.nb_features_count  = self.get_nb_features()
        self.count_by_classe    = self.get_sample_count_by_classe()

        tmp_name = self.name.split("/")
        tmp_name = tmp_name[len(tmp_name)-1]
        tmp_name = tmp_name.split("-")[0]

        f = np.load(self.name+"-0.npz")
        np.savez(self.name + "-0.npz",
                data=f["data"],
                labels=f["labels"],
                dataFormat=[self.dataw, self.datah],
                maxfilesize=self.max_file_size,
                name=tmp_name,
                files_count=self.files_count,
                count_samples=self.count_samples,
                nb_features_count=self.nb_features_count,
                count_by_classe=self.count_by_classe
                )

    def save_chunks(self, name=None):
        try:
            # Save the result in new chucks data files
            while self.data.shape[0] > self.max_file_size:
                data        = self.data[self.max_file_size:,:]
                labels      = self.labels[self.max_file_size:,:]
                self.data   = self.data[:self.max_file_size:,:]
                self.labels = self.labels[:self.max_file_size:,:]

                self.save(name)
                self.fileID = self.fileID + 1
                self.data   = data
                self.labels = labels
            self.save(name)
        except:
            App.log(0, "error during saving.")

    def rename(self,name):
        for file in glob.glob(self.name+"-*.npz"):
            a = file.split("/")
            a = a[len(a)-1].split("-")[1]
            App.log(0, file + " -> " + name + "-" + a)
            os.rename(file, name + "-" + a)
        self.name = name
        np.save(name + "_labels_dic", self.conf_data["classes"])

    def create_classe(self,name):
        try:
            self.conf_data["classes"].index(name)
        except:
            self.conf_data["classes"].append(name)
            np.save(self.name + "_labels_dic", self.conf_data["classes"])

            tmp_name = self.name.split("/")
            tmp_name = tmp_name[len(tmp_name)-1]
            tmp_name = tmp_name.split("-")[0]
            # Add zero column label to all dataset files
            for file in glob.glob(self.name+"-*.npz"):
                f = np.load(file)
                label_tmp = np.asarray(f["labels"])
                b = np.zeros((label_tmp.shape[0], self.labels.shape[1] + 1))
                b[:,:-1] = label_tmp
                label_tmp = b
                np.savez(file,
                    data=f["data"],
                    labels=label_tmp,
                    labels_dic=self.conf_data["classes"],
                    dataFormat=[self.dataw, self.datah],
                    maxfilesize=self.max_file_size,
                    name=tmp_name)
            # Add zero column label to current dataset
            try:
                b = np.zeros((self.labels.shape[0], self.labels.shape[1] + 1))
                b[:,:-1] = self.labels
                self.labels = b
            except:
                self.labels = np.zeros((0,1))

    def load_from_wav_folder(self, folder, asOneclasse=None):
        App.log(0, "\nLoading from folder " + folder)
        try:
            self.conf_data["classes"] = list(np.load(self.name + "_labels_dic.npy"))
        except:
            self.conf_data["classes"] = []

        for f in glob.glob(folder+"/*.wav"):
            App.log(0, f)
            try:
                raw, time, freq, size = play_spectrogram_from_stream(f)
                self.dataw = size[0]
                self.datah = size[1]
            except:
                App.log(0, "Bad file")
            raw  = np.reshape(raw, [1, raw.shape[0]*raw.shape[1]])

            if asOneclasse is None:
                classe = f.split('+')[1]
                classe = classe.split('(')[0]
            else:
                classe = asOneclasse

            raw = np.nan_to_num(raw)

            # Add the raw to dataset
            try:
                self.data = np.concatenate((self.data, raw), axis=0)
            except ValueError:
                self.data = raw

            # Check if the classe is known, else create it
            n_classes = len(self.conf_data["classes"])
            try:
                pos = self.conf_data["classes"].index(classe)
                b = np.zeros((1, n_classes))# IDEA:
                b[0][pos] = 1
            except ValueError:
                self.create_classe(classe)
                b = np.zeros((1, n_classes +1))
                b[0][n_classes] = 1
            try:
                self.labels = np.concatenate((self.labels, b), axis=0)
            except:
                self.labels = b

            if self.data.shape[0] > self.max_file_size:
                self.save_chunks()

        self.save_chunks()

        return self.data, self.labels, self.conf_data["classes"]

    def print_sample(self,dataX, dataY, classe, print_all=False):
        id = np.zeros((1, dataY.shape[1]))
        if classe is not False:
            id[0][int(classe)] = 1

        for i in range(0, dataY.shape[0]):
            if np.array_equiv(id,dataY[i,:]) is True or classe is False:
                App.log(0, dataY[i,:])
                im = dataX[i,:].reshape((self.dataw, self.datah))
                plt.ion()
                plt.imshow(im, interpolation='none')
                plt.show()
                if print_all is False:
                    return
                else:
                    plt.pause(0.5)

    def balance_classe(self):
        App.log(0, "\nClasse balancing.")
        for cl in range(self.labels.shape[1]):
            App.log(0, self.conf_data["classes"][cl])
            nb_cl = self.get_sample_count_by_classe()
            nb_new = int(np.max(nb_cl) - nb_cl[cl])

            # While there is some samples to extract
            while nb_new > 0:
                distrib_cl = []
                # Compute the distribution of samples over the different data files
                for file in sorted_nicely(glob.glob(self.name+"-*.npz")):
                    f = np.load(file)
                    data = f["data"]
                    labels = f["labels"]

                    data_cl = self.get_classe(cl, data, labels)
                    # Store number of sample of this classe for each file
                    distrib_cl.append(data_cl.shape[0])

                # Extract sample of this class according to the distribution over the data files
                distrib_cl = distrib_cl / np.max(distrib_cl)
                for id, file in enumerate(sorted_nicely(glob.glob(self.name+"-*.npz"))):
                    file = np.load(file)
                    data = file["data"]
                    labels = np.asarray(file["labels"])
                    data_cl = self.get_classe(cl, data, labels)

                    # Extract randomly sample from the file according to the sample distribution
                    idx = np.arange(len(data_cl))
                    np.random.shuffle(idx)
                    idx = idx[:int(len(data_cl) * distrib_cl[id])]

                    # Limit the maximum number of samples to extract in order to balance the classe
                    idx = idx[:nb_new]
                    nb_new -= len(idx)

                    # Add the samples to current data buffer
                    try:
                        self.data = np.concatenate((self.data, data_cl[idx]),axis=0)
                        id_cl = np.zeros( (len(idx), self.labels.shape[1]))
                        id_cl[:,cl] = 1
                        self.labels = np.concatenate((self.labels,id_cl),axis=0)
                    except ValueError:
                        pass

                    self.save_chunks()

                # Update the number of required sample to extract for the classe
                nb_cl = self.get_sample_count_by_classe()
                nb_new = int(np.max(nb_cl) - nb_cl[cl])


    def get_classe(self, classe=False, data=None, labels=None):
        res = []
        if data is None:
            data = self.data
        if labels is None:
            labels = self.labels

        id = np.zeros((1, self.labels.shape[1]))
        if classe is not False:
            id[0][int(classe)] = 1

        first=True
        for i in range(0, labels.shape[0]):
            if np.array_equiv(id, labels[i,:] ) is True or classe is False:
                res.append(data[i,:])
        return np.array(res)

    def randomize(self):
        App.log(0, "\nRandomization")

        tmp_name = self.name.split("/")
        tmp_name = tmp_name[len(tmp_name)-1]
        tmp_name = tmp_name.split("-")[0]

        # Mix the samples between the different files
        a = sorted_nicely(glob.glob(self.name+"-*.npz"))
        b = glob.glob(self.name+"-*.npz")
        random.shuffle(b)

        for file1 in a:
            App.log(0, file1)
            idx = np.arange(len(b))
            np.random.shuffle(idx)
            for i in idx[:int(np.maximum(len(idx)*0.5,1))]:
                file2 = b[i]
                # Extract randomly half of the sample in the file 1
                file        = np.load(file1)
                data1       = file["data"]
                labels1     = np.asarray(file["labels"])
                idx1        = np.arange(len(data1))
                np.random.shuffle(idx1)

                # Extract randomly half of the sample in the file 2
                file        = np.load(file2)
                data2       = file["data"]
                labels2     = np.asarray(file["labels"])
                idx2        = np.arange(len(data2))
                np.random.shuffle(idx2)

                nb_max = np.min([int(data1.shape[0] / 2), int(data2.shape[0] / 2)])

                idx1    = idx1[:nb_max]
                data1_extracted         = copy.deepcopy(data1[idx1,:])
                labels1_extracted       = copy.deepcopy(labels1[idx1,:])

                idx2    = idx2[:nb_max]
                data2_extracted         = copy.deepcopy (data2[idx2,:])
                labels2_extracted       = copy.deepcopy (labels2[idx2,:])

                # Switch the extracted sample in the two files
                if file1 != file2:
                    data1[idx1,:]       = data2_extracted
                    labels1[idx1,:]     = labels2_extracted
                    data2[idx2,:]       = data1_extracted
                    labels2[idx2,:]     = labels1_extracted

                # Randomize the sample in both files
                idx = np.arange(data1.shape[0])
                np.random.shuffle(idx)
                data1      = data1[idx,:]
                labels1    = labels1[idx,:]

                idx = np.arange(data2.shape[0])
                np.random.shuffle(idx)
                data2      = data2[idx,:]
                labels2    = labels2[idx,:]

                 # Save the files
                np.savez(file1,
                        data=data1,
                        labels=labels1,
                        labels_dic=self.conf_data["classes"],
                        dataFormat=[self.dataw, self.datah],
                        maxfilesize=self.max_file_size,
                        name=tmp_name)
                np.savez(file2,
                        data=data2,
                        labels=labels2,
                        labels_dic=self.conf_data["classes"],
                        dataFormat=[self.dataw, self.datah],
                        maxfilesize=self.max_file_size,
                        name=tmp_name)


    def merge(self,dataset_name, asOneClasse=None):
        App.log(0, "\nMerging with " + dataset_name)
        id = 0
        if asOneClasse is not None:
            try:
                pos = self.conf_data["classes"].index(asOneClasse)
            except:
                App.log(0, "New classe " + asOneClasse)
                try:
                    pos = self.labels.shape[1]
                except:
                    pos = 0
        else:
            try:
                labels_dic_to_merge = np.load(dataset_name+"_labels_dic.npy")
            except:
                App.log(0, "Dataset " + dataset_name + " not found")


        for id, file in enumerate(sorted_nicely(glob.glob(dataset_name+"-*.npz"))):
            file = np.load(file)
            data    = file["data"]
            labels  = file["labels"]

            try:
                self.data = np.concatenate((self.data, data),axis=0)
            except:
                self.data = data

            App.log(0, self.conf_data["classes"])
            if asOneClasse is not None:
                try:
                    # IS A NEW CLASSE
                    if pos == self.labels.shape[1]:
                        # Add and save the new classe label
                        self.create_classe(asOneClasse)
                        # Add the one column to current data file for the merge
                        l = np.zeros( (data.shape[0], self.labels.shape[1]) )
                        l[:,pos] = 1
                    # IS AN EXISTING CLASSE
                    else:
                        l = np.zeros( (data.shape[0], self.labels.shape[1]) )
                        l[:,pos] = 1

                    self.labels = np.concatenate((self.labels, l),axis=0)
                # If the current dataset is empty
                except:
                    self.conf_data["classes"].append(asOneClasse)
                    np.save(self.name + "_labels_dic", self.conf_data["classes"])
                    self.labels = np.ones( (data.shape[0], 1) )

            else:
                for l in labels:
                    name = labels_dic_to_merge[np.argmax(l)]
                    try:
                        # Looking for label position
                        pos = self.conf_data["classes"].index(name)

                    # If classe not found, it is a new classe which must be added to the dataset
                    except:
                        App.log(0, "Create " + name)
                        self.create_classe(name)
                        pos = self.labels.shape[1] - 1

                    l = np.zeros( (1, self.labels.shape[1]) )
                    l[:,pos] = 1
                    self.labels = np.concatenate((self.labels, l),axis=0)

            # Save the result in new chucks data files
            self.save_chunks()

    def split_dataset(self, name=None, p=0.9):
        if name is None:
            name = self.name+"_test"
        dic = np.load(self.name + "_labels_dic.npy")
        np.save(name + "_labels_dic.npy", dic)

        tmp_name = name.split("/")
        tmp_name = tmp_name[len(tmp_name)-1]
        tmp_name = tmp_name.split("-")[0]

        # Split each file into two files
        App.log(0, "Dataset splitting.")
        for i in range(0, self.fileID + 1):
            file = np.load(self.name + "-" + str(i) + ".npz")
            labels  = file["labels"]
            data    = file["data"]

            idx        = np.arange(len(data))
            np.random.shuffle(idx)

            l1 = labels[idx[:int(len(idx) * p)] ,:]
            d1 = data[idx[:int(len(idx) * p)] ,:]
            l2 = labels[idx[int(len(idx) * p):] ,:]
            d2 = data[idx[int(len(idx) * p):] ,:]

            np.savez(self.name + "-" + str(i) + ".npz",
                data=d1,
                labels=l1,
                labels_dic=self.conf_data["classes"],
                dataFormat=[self.dataw, self.datah],
                maxfilesize=self.max_file_size,
                name=tmp_name)
            np.savez(name + "-" + str(i) + ".npz",
                data=d2,
                labels=l2,
                labels_dic=self.conf_data["classes"],
                dataFormat=[self.dataw, self.datah],
                maxfilesize=self.max_file_size,
                name=name)

        # Homogeneous the file according to max_file_size
        for i in range(0,2):
            if i==0:
                n = name
            else:
                n = self.name
            App.log(0, "Dataset refactoring " + n)
            id = 0
            self.labels = np.zeros((0, self.labels.shape[1]))
            self.data = np.zeros((0, self.data.shape[1]))
            self.fileID = 0
            for file in sorted_nicely(glob.glob(n+"-*.npz")):
                file = np.load(file)
                l = file["labels"]
                d = file["data"]
                self.labels = np.concatenate( (self.labels, l), axis=0)
                self.data = np.concatenate( (self.data, d), axis=0)
                self.save_chunks(n)
            self.save_chunks(n)
            # Clean older and remaining files
            for file in glob.glob(n+"-*.npz"):
                id = int(file.split("-")[1].split(".")[0])
                if id > self.fileID:
                    os.remove(file)

    def nb_samples(self):
        count = 0
        countl = 0
        for f in glob.glob(self.name+"-*.npz"):
            tmp = np.load(f)
            count = count + tmp["data"].shape[0]
            countl = countl + tmp["labels"].shape[0]

        if count != countl:
            App.log(0, "ERROR Database inconsistent (" + str(count) + " != " + str(countl) +")")
            sys.exit(-1)
        return int(count)

    def get_nb_features(self):
        features = np.load(self.name+"-0.npz")
        return features["data"].shape[1]

    def get_nb_classes(self):
        return len(self.out_labels)

    def get_classes(self):
        classes = np.load(self.name+"_labels_dic.npy")
        return classes

    def nb_files(self):
        for file in sorted_nicely(glob.glob(self.name+"-*.npz")):
            pass
        file = file.split("/")
        file = file[len(file)-1]
        file = file.split(".npz")[0]
        return int(file.split("-")[1])

    def get_sample_count_by_classe(self):
        count = []
        first = True
        for f in glob.glob(self.name+"-*.npz"):
            f = np.load(f)
            labels = f["labels"]
            if first is True:
                first = False
                count = np.sum(labels, axis=0)
            else:
                tmp = np.sum(labels, axis=0)
                try:
                    count = np.sum((count,tmp) ,axis=0)
                except:
                    count = np.sum(count + tmp)
        return count

    def next_batch(self, batch_size=128, testing=False):
        if self.mode == "file":
            return self.next_batch_file(batch_size)

        elif self.mode == "onfly":
            return self.next_batch_onfly(batch_size, testing)
        else:
            return -1


    def next_batch_file(self, batch_size=128):
        tmp_name = self.name.split("/")
        tmp_name = tmp_name[len(tmp_name)-1]
        tmp_name = tmp_name.split("-")[0]

        if batch_size > self.max_file_size:
            App.log(0, "Batchsize must be lower than the dataset file size ("+str(self.max_file_size)+").")
            batch_size = self.max_file_size

        idfile  = (int(self.cur_batch / self.max_file_size)) % self.files_count
        pos_file = self.cur_batch % self.max_file_size

        if idfile != self.batchIDfile or self.batchfile == []:
            self.batchIDfile = idfile
            self.batchfile = np.load(self.name+ "-"+str(self.batchIDfile)+".npz")
        d    = self.batchfile["data"]
        l    = self.batchfile["labels"]

        data    = d[pos_file:pos_file+batch_size, :]
        labels  = l[pos_file:pos_file+batch_size, :]

        if pos_file + batch_size >= self.max_file_size:
            self.batchIDfile = self.batchIDfile + 1
            if self.batchIDfile >= self.nb_files():
                self.batchIDfile = 0
            self.batchfile = np.load(self.name+ "-"+str(self.batchIDfile)+".npz")
            d    = self.batchfile["data"]
            l    = self.batchfile["labels"]

            data    = np.concatenate( (data, d[ :batch_size - (self.max_file_size - pos_file), :] ), axis=0)
            labels  = np.concatenate( (labels, l[ :batch_size - (self.max_file_size - pos_file), :] ), axis=0)

        App.log(0, "#{0} Batch({5}) {1}/{2}: {3} samples of {4} features".format(
                int(self.cur_batch / self.count_samples),
                int( (self.cur_batch % self.count_samples) / batch_size ),
                int(self.count_samples / batch_size),
                batch_size,
                self.nb_features_count,
                tmp_name ) )

        self.cur_batch += batch_size
        return data, labels

    def batch_count(self,batch_size=128):
         return int( (((self.nb_files()-1) * self.max_file_size) + self.data.shape[0]) / batch_size)


if __name__ == "__main__":
    parser = optparse.OptionParser(usage="python src/TidzamDatabase.py")
    parser.add_option("--dataset", action="store", type="string", dest="dataset",
        default=None, help="Open an exisiting dataset.")

    parser.add_option("--rename", action="store", type="string", dest="rename",
        default=None, help="Rename the dataset.")

    parser.add_option("--classe", action="store", type="string", dest="classe",
        default=None, help="Create an empty classe.")

    parser.add_option("--audio-folder", action="store", type="string", dest="audio_folder",
        default=None, help="Load the audio file folder in the dataset (as a single classe if --classe is specified).")

    parser.add_option("--merge", action="store", type="string", dest="merge",
        default=None, help="Merge the dataset with another one (as a single classe if --classe is specified).")

    parser.add_option("--split", action="store", type="float", dest="split",
        default=None, help="Extraction proportion of a sub dataset for testing --split in [0...1]")

    parser.add_option("--split-name", action="store", type="string", dest="split_name",
        default=None, help="Name for the generated dataset.")

    parser.add_option("--balance", action="store_true", dest="balance",
        default=False, help="Automatic balance the classe in the dataset (by duplicating samples in small classes).")

    parser.add_option("--randomize", action="store_true", dest="randomize",
        default=False, help="Randomize the dataset.")

    parser.add_option("--file-count", action="store_true", dest="nb_files",
        default=False, help="Return the number of files which compose the dataset.")

    parser.add_option("--metadata", action="store_true", dest="metadata",
        default=False, help="Generate metadata information and store them on file 0.")

    parser.add_option("--info", action="store_true", dest="info",
        default=False, help="Return some dataset information.")


    (options, args) = parser.parse_args()

    if options.dataset:
        dataset = Dataset(options.dataset, split=options.split)
    else:
        dataset = Dataset()

    if options.rename:
        dataset.rename(options.rename)

    if options.audio_folder:
        dataset.load_from_wav_folder(options.audio_folder, options.classe)

    elif options.merge:
        dataset.merge(options.merge, options.classe)

    elif options.classe:
        dataset.create_classe(options.classe)

    if options.split and dataset.mode == "file":
        dataset.split_dataset(p=options.split, name=options.split_name)

    if options.balance:
        dataset.balance_classe()

    if options.randomize:
        dataset.randomize()

    if options.metadata:
        dataset.save_meta()

    if options.nb_files:
        App.log(0, "Number of files: ")
        App.log(0, dataset.nb_files())

    if options.info:
        App.log(0, "Data format: (" + str(dataset.dataw)+","+str(dataset.datah)+")")
