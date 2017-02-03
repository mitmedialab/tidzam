from __future__ import print_function

import sys, optparse
import numpy as np
from matplotlib import pyplot as plt
import glob

from scipy import signal
import soundfile as sf
import sounddevice as sd

def play_spectrogram_from_stream(file, show=False, callable_objects = []):
    with sf.SoundFile(file, 'r') as f:
        while f.tell() < len(f):
            data = f.read(24000)
            for i in range(0,f.channels):
                plt.ion()
                fs, t, Sxx = signal.spectrogram(data[:,i], f.samplerate,
                        nfft=1024, noverlap=128)

                # Extract between 1-8 Khz
                Sxx = Sxx[[x for x in range(20,170)], :]*1000
                # Normalize and cutoff
                Sxx = np.maximum(Sxx/np.max(Sxx), np.ones((Sxx.shape[0], Sxx.shape[1]))*0.01)
                fs = fs[[x for x in range(20,170)]]

                if show is True:
                    plt.figure(i, figsize=(7, 7))
                    plt.pcolormesh(t, fs, Sxx)
                    plt.ylabel('Frequency [Hz]')
                    plt.xlabel('Time [sec]')
                    plt.show()
                    plt.pause(0.5/f.channels)

                for obj in callable_objects:
                    obj.run(Sxx, fs, t, [data[:,i], f.samplerate])

        return Sxx, t, fs

class Dataset:
    def __init__(self, file=False,p=0.9, data_size=(92,300)):
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
            self.load(file)
            self.split_dataset(p=p)

    def load(self, file):
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

    def load_from_wav_folder(self, folder):
        print("Folder " + folder)
        labels_dic = []
        labels = []
        data = []
        for f in glob.glob(folder+"/*.wav"):
            raw, time, freq = play_spectrogram_from_stream(f)
            raw  = np.reshape(raw, [1, raw.shape[0]*raw.shape[1]])
            classe = f.split('+')[1]
            classe = classe.split('(')[0]
            print(classe)
            # Check if the classe is known, else create it
            try:
                pos = labels_dic.index(classe)+1
                labels.append(pos)
            except ValueError:
                labels_dic.append(classe)
                labels.append(len(labels_dic))
            # Add the raw to dataset
            try:
                data = np.concatenate((data, raw), axis=0)
            except ValueError:
                data = raw

        # Label reconstruction as vector
        l = np.zeros((len(labels), np.max(labels)))
        for i in range(0,len(labels)):
            l[i,labels[i]-1] = 1
        labels = l

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

    def randomize(self):
        idx = np.arange(self.data.shape[0])
        np.random.shuffle(idx)
        self.data = self.data[idx,:]
        self.labels = self.labels[idx,:]

    def merge(self,dataset):
        self.data = np.append(self.data, dataset.data, axis=0)

        # Shift classe positions for alignment and merge labels
        n_classes = self.labels.shape[1] + dataset.labels.shape[1]
        print(n_classes)
        b = np.zeros((self.labels.shape[0], n_classes))
        b[:,:-dataset.labels.shape[1]] = self.labels
        self.labels = b

        b = np.zeros((dataset.labels.shape[0], n_classes))
        b[:, [x for x in range(n_classes - dataset.labels.shape[1], n_classes)]] = dataset.labels
        dataset.labels = b

        ### Merge labels and dictionary
        self.labels = np.append(self.labels, dataset.labels, axis=0)
        self.labels_dic = np.append(self.labels_dic, dataset.labels_dic)

        print(self.labels)

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
        batch_x = self.data_train[ [x for x in range(a,b)], :]
        batch_y = self.label_train[ [x for x in range(a,b)], :]
        print("Batch #{0}: {1} samples of {2} features".format(
                self.cur_batch_train, batch_x.shape[0],batch_x.shape[1]))
        self.cur_batch_train += 1
        return batch_x, batch_y

    def batch_train_count(self,batch_size=128):
        return int(self.data_train.shape[0]/batch_size)

    def next_batch_test(self, batch_size=128):
        a = (self.cur_batch_test*batch_size) % self.data_test.shape[0]
        b = ((self.cur_batch_test+1)*batch_size) % self.data_test.shape[0]
        batch_x = self.data_test[ [x for x in range(a,b)], :]
        batch_y = self.label_test[ [x for x in range(a,b)], :]
        print("Batch #{0}: {1} samples of {2} features".format(
                self.cur_batch_test, batch_x.shape[0],batch_x.shape[1]))
        self.cur_batch_test += 1
        return batch_x, batch_y

    def batch_test_count(self,batch_size=128):
        return int(self.data_test.shape[0]/batch_size)

########################################

class Extractor:
    def __init__(self,load_dataset=""):
        print(load_dataset)
        if load_dataset != "":
            self.dataset = Dataset(load_dataset)
            self.init = True
        else:
            self.dataset = Dataset()
            self.init = False

    def run(self, Sxx, fs, t, sound_obj):
        while True:
            sd.play(sound_obj[0], 48000)
            print("\n===============\n Classe available\n---------------")
            for i in range(0, len(self.dataset.labels_dic)):
                print(str(i) + " : " + str(self.dataset.labels_dic[i]) )
            print("Actions:\n---------------")
            print("* (enter): next sample\n* (n): create a new classe\n* (m) merge with another dataset")
            print("* (s): save the dataset \n* (i): dataset info\n* (p) print the labels\n"+ \
                "*(r) randomize the dataset\n* (q): quit\n")
            a = raw_input()

            if a == 's':
                if options.out  is not None:
                    out = options.out
                else:
                    print("Dataset name: ")
                    out = raw_input()
                self.dataset.save(out)
                print('Save')

            elif a == 'n':
                print('New classe name: ')
                name = raw_input()
                try:
                    print(self.dataset.labels_dic)
                    self.dataset.labels_dic = np.append(self.dataset.labels_dic, name)
                except NameError:
                    self.dataset.labels_dic = name
            elif a == 'm':
                print("Merge with dataset:")
                name = raw_input()
                dataset = Dataset(name)
                self.dataset.merge(dataset)

            elif a == 'p':
                print("Print labels:")
                print(self.dataset.labels)

            elif a == 'r':
                print("Randomization")
                self.dataset.randomize()

            elif a == 'i':
                print('Informations:\n--------------')
                try:
                    print(str(self.dataset.data.shape[0]) +" samples of " + str(self.dataset.data.shape[1]) + " features in " +
                    str(self.dataset.labels.shape[1]) + " classes.")
                    print(self.dataset.labels_dic)
                except:
                    print('No data.')
            elif a == 'q':
                quit()
            elif a == '':
                break;
            else:
                try:
                    if int(a) < len(self.dataset.labels_dic):
                        if self.init is False:
                            self.dataset.data =  np.reshape(Sxx,[1,Sxx.shape[0]*Sxx.shape[1]])
                            c = np.zeros((1, len(self.dataset.labels_dic)))
                            c[0][int(a)] = 1
                            self.dataset.labels = c
                            self.init = True
                        else:
                            self.dataset.data = np.append(self.dataset.data,
                                np.reshape(Sxx,[1,Sxx.shape[0]*Sxx.shape[1]]), axis=0)

                            # New classe => add a new column to label
                            if (int(a) >= self.dataset.labels.shape[1]):
                                b = np.zeros((self.dataset.labels.shape[0],self.dataset.labels.shape[1] + 1))
                                b[:,:-1] = self.dataset.labels
                                self.dataset.labels = b

                            # Create the classe vector and add it
                            c = np.zeros((1, len(self.dataset.labels_dic)))
                            c[0][int(a)] = 1
                            self.dataset.labels = np.append(self.dataset.labels, c, axis=0)
                        print(str(self.dataset.labels.shape[0]) + " samples of " + str(self.dataset.labels.shape[1]) + " classes")
                        break
                except:
                    pass

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-b", "--build", action="store", type="string", dest="build")
    parser.add_option("-o", "--out", action="store", type="string", dest="out")
    parser.add_option("-r", "--read", action="store", type="string", dest="read", default="")
    parser.add_option("-s", "--show", action="store", type="string", dest="show",
        default=False, help="Show spectrogram of the samples")

    parser.add_option("--file", action="store", type="string", dest="file", default="")
    parser.add_option("--extract", action="store_true")
    (options, args) = parser.parse_args()

    # Build a dataset from a folder containing wav files
    if options.build:
        if options.out is False:
            print('Destination filename must be specified --out=filename')
            quit()
        data = Dataset()
        data.load_from_wav_folder(options.build)
        data.save(options.out)


    if options.extract:
        if options.file == "":
            print('Please define an audio stream to open')
            quit()

        obj_extractor = Extractor(options.read)
        play_spectrogram_from_stream(options.file,
                    show=True,
                    callable_objects = [obj_extractor])

    # Read a dataset and plot all example of a classe
    elif options.read:
        data = Dataset(options.read,data_size=(150,186))
        data.print_sample(np.abs(data.data), data.labels, options.show, print_all=True)
