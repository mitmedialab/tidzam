from __future__ import print_function

import sys, os
import numpy as np
from matplotlib import pyplot as plt
import glob
import time

from scipy import signal
import soundfile as sf
import sounddevice as sd

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

    Sxx = np.reshape(Sxx, [1, Sxx.shape[0]*Sxx.shape[1]] )
    return fs, t, Sxx

def play_spectrogram_from_stream(file, show=False, callable_objects = [], overlap = 0):

    with sf.SoundFile(file, 'r') as f:
        while f.tell() < len(f):
            data = f.read(24000)
            for i in range(0,f.channels):
                if f.channels > 1:
                    fs, t, Sxx = get_spectrogram(data[:,i], f.samplerate, i,  show=show)
                else:
                    fs, t, Sxx = get_spectrogram(data, f.samplerate, i, show=show)

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

            f.seek(int(-24000*overlap), whence=sf.SEEK_CUR)

        return Sxx, t, fs

class Dataset:
    def __init__(self, file=False,p=0.9, data_size=(150,186)):
        self.cur_batch_train = 0
        self.cur_batch_test = 0
        self.n_classes = -1
        self.n_input = -1

        self.dataw = data_size[0]#92
        self.datah =  data_size[1]#300

        self.data = []
        self.labels = []
        self.labels_dic = []

        if file is not False:
            self.name = file
            self.load(file)
            self.split_dataset(p=p)

    def load(self, file):
        a = file.split('(')
        if len(a) > 1:
            a = a[1].split(')')
            a = a[0].split(',')
            self.dataw = int(a[0])
            self.datah = int(a[1])
        try:
            self.data = np.load(file+"_data.npy")
            self.labels = np.load(file+"_labels.npy")
            self.labels_dic = np.load(file+"_labels_dic.npy")

            self.n_input = self.data.shape[1]
            self.n_classes = self.labels.shape[1]

            print(" " +str(self.data.shape[0]) + " samples ("+ \
                str(self.n_input) +" features) of " + \
                str(self.n_classes) + " classes")
        except IOError:
            print("File not found: " + file)

    def save(self,name):
        np.save(name + "_data", self.data)
        np.save(name + "_labels", self.labels)
        np.save(name + "_labels_dic", self.labels_dic)

    def load_from_wav_folder(self, folder, asOneclasse=None):
        print("Folder " + folder)
        labels_dic = self.labels_dic
        labels = self.labels
        data = self.data
        for f in glob.glob(folder+"/*.wav"):
            print(f)
            raw, time, freq = play_spectrogram_from_stream(f)
            raw  = np.reshape(raw, [1, raw.shape[0]*raw.shape[1]])

            if asOneclasse is None:
                classe = f.split('+')[1]
                classe = classe.split('(')[0]
            else:
                classe = asOneclasse

            if np.isnan(raw).any():
                print("Bad sample containing NaN value: " + f)
                os.remove(f)
                continue

            # Add the raw to dataset
            try:
                data = np.concatenate((data, raw), axis=0)
            except ValueError:
                data = raw

            # Check if the classe is known, else create it
            n_classes = len(labels_dic)
            try:
                pos = labels_dic.index(classe)
                b = np.zeros((1, n_classes))
                b[0][pos] = 1
            except ValueError:
                labels_dic.append(classe)
                # Shift classe positions for alignment and merge labels
                b = np.zeros((data.shape[0]-1, n_classes + 1))
                b[:,:-1] = labels
                labels = b
                b = np.zeros((1, n_classes +1))
                b[0][n_classes] = 1

            try:
                labels = np.concatenate((labels, b), axis=0)
            except:
                labels = b

        self.data = data
        self.labels = labels
        self.labels_dic = labels_dic
        # Label reconstruction as vector

        print("Randomization")
        self.randomize()
        self.labels_dic = labels_dic

        self.n_input = self.data.shape[1]
        self.n_classes = self.labels.shape[1]

        return self.data, self.labels, self.labels_dic

    def print_sample(self,dataX, dataY, classe, print_all=False):
        id = np.zeros((1, self.n_classes))
        if classe is not False:
            id[0][int(classe)] = 1

        for i in range(0, dataY.shape[0]):
            if np.array_equiv(id,dataY[i,:]) is True or classe is False:
                print(dataY[i,:])
                im = dataX[i,:].reshape((self.dataw, self.datah))
                plt.ion()
                plt.imshow(im, interpolation='none')
                plt.show()
                if print_all is False:
                    return
                else:
                    plt.pause(0.5)

    def get_classe(self, classe):
        res = []
        id = np.zeros((1, self.n_classes))
        if classe is not False:
            id[0][int(classe)] = 1

        for i in range(0, self.labels.shape[0]):
            if np.array_equiv(id,self.labels[i,:]) is True or classe is False:
                res.append(self.data[i,:])
        return np.array(res)

    def randomize(self):
        idx = np.arange(self.data.shape[0])
        np.random.shuffle(idx)
        self.data = self.data[idx,:]
        self.labels = self.labels[idx,:]

    def merge(self,dataset, asOneClasse=False):
        if asOneClasse is not False:
            dataset.labels = np.ones((dataset.data.shape[0], 1))
            dataset.labels_dic = []
            dataset.labels_dic.append(asOneClasse)

        try:
            for id_classe, label_name in enumerate(dataset.labels_dic):
                found = False
                data = dataset.get_classe(id_classe)
                for id_classe2, label2_name in enumerate(self.labels_dic):
                    if label_name == label2_name:
                        print("Found :" + label_name)
                        found = True
                        label = np.zeros( (data.shape[0],self.labels.shape[1]) )
                        label[:,id_classe2] = 1
                if found is False:
                    label = np.zeros( (data.shape[0],self.labels.shape[1] + 1) )
                    label[:, self.labels.shape[1]] = 1
                    self.labels_dic.append(label_name)
                self.labels = np.append(self.labels, label, axis=0)
                self.data  = np.append(self.data, data, axis=0)

        except:
             self.data = dataset.data
             self.labels = dataset.labels
             self.labels_dic = dataset.labels_dic

    def get_sample_count_by_classe(self):
        return np.sum(self.labels, axis=0)

    ########################################
    # Dataset Preparation for training
    ########################################
    def split_dataset(self, p=0.9):
        self.data_train = self.data[ [x for x in range(0,int(self.data.shape[0]*p))] ,:]
        self.label_train = self.labels[ [x for x in range(0,int(self.data.shape[0]*p))] ,:]
        idx = [x for x in range(int(self.data.shape[0]*p), int(self.data.shape[0]))]
        self.data_test = self.data[ idx ,:]
        self.label_test = self.labels[ idx ,:]
        return self.data_train, self.label_train, self.data_test, self.label_test

    def next_batch_train(self, batch_size=128):
        a = (self.cur_batch_train*batch_size) % self.data_train.shape[0]
        b = ((self.cur_batch_train+1)*batch_size) % self.data_train.shape[0]
        if a < b:
            batch_x = self.data_train[ [x for x in range(a,b)], :]
            batch_y = self.label_train[ [x for x in range(a,b)], :]
        else :
            batch_x = self.data_train[
                [x for x in list(range(a,self.data_train.shape[0])) + list(range(0,b))], :]
            batch_y = self.label_train[
                [x for x in list(range(a,self.data_train.shape[0])) + list(range(0,b))], :]
        print("#({3}) Batch (train) #{0}: {1} samples of {2} features".format(
                self.cur_batch_train,
                batch_x.shape[0],
                batch_x.shape[1],
                int(self.cur_batch_train*batch_size/self.data_train.shape[0] )))
        self.cur_batch_train += 1
        return batch_x, batch_y

    def batch_train_count(self,batch_size=128):
        return int(self.data_train.shape[0]/batch_size)

    def next_batch_test(self, batch_size=128):
        a = (self.cur_batch_test*batch_size) % self.data_test.shape[0]
        b = ((self.cur_batch_test+1)*batch_size) % self.data_test.shape[0]
        if a < b:
            batch_x = self.data_test[ [x for x in range(a,b)], :]
            batch_y = self.label_test[ [x for x in range(a,b)], :]
        else :
            batch_x = self.data_test[
                [x for x in list(range(a,self.data_test.shape[0])) + list(range(0,b))], :]
            batch_y = self.label_test[
                [x for x in list(range(a,self.label_test.shape[0])) + list(range(0,b))], :]
        print("#({3}) Batch (test) #{0}: {1} samples of {2} features".format(
                self.cur_batch_test,
                batch_x.shape[0],
                batch_x.shape[1],
                int(self.cur_batch_test*batch_size/self.data_test.shape[0] )))
        self.cur_batch_test += 1
        return batch_x, batch_y

    def batch_test_count(self,batch_size=128):
        return int(self.data_test.shape[0]/batch_size)

########################################
