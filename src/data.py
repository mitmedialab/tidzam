from __future__ import print_function

import sys, optparse
import numpy as np
from matplotlib import pyplot as plt
import glob
import time

from scipy import signal
import soundfile as sf
import sounddevice as sd

def play_spectrogram_from_stream(file, show=False, callable_objects = []):
    with sf.SoundFile(file, 'r') as f:
        while f.tell() < len(f):
            data = f.read(24000)
            for i in range(0,f.channels):
                plt.ion()
                if f.channels > 1:
                    fs, t, Sxx = signal.spectrogram(data[:,i], f.samplerate,
                            nfft=1024, noverlap=128)
                else:
                    fs, t, Sxx = signal.spectrogram(data, f.samplerate,
                            nfft=1024, noverlap=128)
                # editor between 1-8 Khz
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
                    plt.pause(0.1)
                    sd.play(data[:,i], f.samplerate)
                    time.sleep(0.5)

                Sxx = np.reshape(Sxx, [1, Sxx.shape[0]*Sxx.shape[1]] )

                if i == 0:
                    Sxxs = Sxx
                    fss = fs
                    ts = t
                else:
                    Sxxs = np.concatenate((Sxxs, Sxx), axis=0)
                    fss = np.concatenate((fss, fs), axis=0)
                    ts = np.concatenate((ts, t), axis=0)

            for obj in callable_objects:
                obj.run(Sxxs, fss, ts, [data, f.samplerate])

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
            self.name = file
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
                b[pos] = 1
            except ValueError:
                labels_dic.append(classe)

                # Shift classe positions for alignment and merge labels
                b = np.zeros((data.shape[0], n_classes + 1))
                b[:,:-n_classes] = self.labels
                self.labels = b
                b = np.zeros((1, n_classes +1))
                b[n_classes] = 1

            try:
                labels = np.concatenate((labels, b), axis=0)
            except ValueError:
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

    def randomize(self):
        idx = np.arange(self.data.shape[0])
        np.random.shuffle(idx)
        self.data = self.data[idx,:]
        self.labels = self.labels[idx,:]

    def merge(self,dataset, asOneClasse=False):

        if asOneClasse is not False:
            nb_max = np.max(self.get_sample_count_by_classe())
            if nb_max > 0:
                nb_max = int(np.min([nb_max, dataset.data.shape[0]], axis=0))
            else:
                nb_max = dataset.data.shape[0]
            print(nb_max)
            dataset.randomize()
            dataset.data = dataset.data[1:nb_max,:]
            dataset.labels = np.ones((dataset.data.shape[0], 1))
            dataset.labels_dic = []
            dataset.labels_dic.append(asOneClasse)

        try:
            self.data = np.append(self.data, dataset.data, axis=0)
            # Shift classe positions for alignment and merge labels
            n_classes = self.labels.shape[1] + dataset.labels.shape[1]
            b = np.zeros((self.labels.shape[0], n_classes))
            b[:,:-dataset.labels.shape[1]] = self.labels
            self.labels = b

            b = np.zeros((dataset.labels.shape[0], n_classes))
            b[:, [x for x in range(n_classes - dataset.labels.shape[1], n_classes)]] = dataset.labels
            dataset.labels = b

            ### Merge labels and dictionary
            self.labels = np.append(self.labels, dataset.labels, axis=0)
            self.labels_dic = np.append(self.labels_dic, dataset.labels_dic)

        # There is no data, first add
        except:
            self.data = dataset.data
            self.labels = dataset.labels
            self.labels_dic = dataset.labels_dic

        print("Randomization")
        for i in range(0,10):
            self.randomize()

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
                [x for x in range(a,self.data_train.shape[0]) +range(0,b)], :]
            batch_y = self.label_train[
                [x for x in range(a,self.data_train.shape[0]) +range(0,b)], :]
        print("#({3}) Batch (train) #{0}: {1} samples of {2} features".format(
                self.cur_batch_train,
                batch_x.shape[0],
                batch_x.shape[1],
                self.cur_batch_train*batch_size/self.data_train.shape[0] ))
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
                [x for x in range(a,self.data_test.shape[0]) + range(0,b)], :]
            batch_y = self.label_test[
                [x for x in range(a,self.label_test.shape[0]) + range(0,b)], :]
        print("#({3}) Batch (test) #{0}: {1} samples of {2} features".format(
                self.cur_batch_test,
                batch_x.shape[0],
                batch_x.shape[1],
                self.cur_batch_test*batch_size/self.data_test.shape[0] ))
        self.cur_batch_test += 1
        return batch_x, batch_y

    def batch_test_count(self,batch_size=128):
        return int(self.data_test.shape[0]/batch_size)

########################################

class Editor:
    def __init__(self,load_dataset=""):
        print(load_dataset)
        if load_dataset != "":
            self.dataset = Dataset(load_dataset)
            self.init = True
        else:
            self.dataset = Dataset()
            self.init = False

    def run(self, Sxx=None, fs=None, t=None, sound_obj=None):
        while True:
            if sound_obj is not None:
                sd.play(sound_obj[0], 48000)

            print("\n===============\n Classe available\n---------------")
            for i in range(0, len(self.dataset.labels_dic)):
                print(str(i) + " : " + str(self.dataset.labels_dic[i]) )
            print("Actions:\n---------------")
            print("* (enter): next sample\n* (n): create a new classe\n* (m) merge with another dataset")
            print("* (s): save the dataset \n* (i): dataset info\n* (p) print the labels\n"+ \
                "* (r) randomize the dataset\n* (q): quit\n")
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
                print("As a single classe ? (y/N)")
                a = raw_input()
                if a == 'y':
                    print("Mother classe name to create:")
                    classe = raw_input()
                    self.dataset.merge(dataset, asOneClasse=classe)
                else:
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
                    print("Samples distribution:")
                    print(self.dataset.get_sample_count_by_classe())
                except:
                    print('No data.')
            elif a == 'q':
                quit()
            elif a == '':
                break;
            elif Sxx is not None:
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
    parser = optparse.OptionParser(usage="python src/data.py --stream=stream.wav")
    parser.add_option("-w", "--wav", action="store", type="string", dest="wav")
    parser.add_option("-d", "--dataset", action="store", type="string", dest="open",
        default="", help="Open an exisiting dataset")

    parser.add_option("-o", "--out", action="store", type="string", dest="out",
                help="Provide output dataset name for wav processing.")

    parser.add_option("-s", "--show", action="store", type="string", dest="classe_id",
        default=False, help="Show spectrograms for a specific class_id")

    parser.add_option("--stream", action="store", type="string", dest="stream",
        default=None, help="Sample extraction from an audio stream [WAV/OGG/MP3].")
    parser.add_option("--editor", action="store_true", help="Interractive mode.")
    (options, args) = parser.parse_args()

    # Build a dataset from a folder containing wav files
    if options.wav:
        if options.out is False:
            print('Destination dataset must be specified --out=filename')
            quit()
        data = Dataset()
        data.load_from_wav_folder(options.wav)
        data.save(options.out)


    if options.editor:
        obj_editor = Editor(options.open)
        if options.stream is not None:
            play_spectrogram_from_stream(options.stream,
                        show=True,
                        callable_objects = [obj_editor])
        else:
            obj_editor.run()

    # Open a dataset and plot all example of a classe
    elif options.open:
        data = Dataset(options.open,data_size=(150,186))
        data.print_sample(np.abs(data.data), data.labels, options.classe_id, print_all=True)
