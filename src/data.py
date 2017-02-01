import sys, optparse
import numpy as np
from matplotlib import pyplot as plt
from scipy import signal
import soundfile as sf
import glob

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

                for obj in callable_objects:
                    obj.run(Sxx, fs, t)

                if show is True:
                    plt.figure(i, figsize=(7, 7))
                    plt.pcolormesh(t, fs, Sxx)
                    plt.ylabel('Frequency [Hz]')
                    plt.xlabel('Time [sec]')
                    plt.show()
                    plt.pause(0.5/f.channels)

        return Sxx, t, fs

class Dataset:
    def __init__(self, file=False,p=0.9, data_size=(92,300)):
        self.cur_batch_train = 0
        self.cur_batch_test = 0
        self.n_classes = -1
        self.n_input = -1

        self.dataw = data_size[0]#92
        self.datah =  data_size[1]#300

        if file is not False:
            self.load(file)
            self.split_dataset(p=p)

    def load(self, file):
        try:
            self.data = np.load(file+"_data.npy")
            self.labels = np.load(file+"_labels.npy")

            self.n_input = self.data.shape[1]
            self.n_classes = self.labels.shape[1]

            print(" " +str(self.data.shape[0]) + " samples ("+ \
                str(self.n_input) +" features) of " + \
                str(self.n_classes) + " classes")
        except IOError:
            print("File not found: " + file)

    def load_from_wav(self, folder):
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

        print(data.shape)
        print(len(labels))
        print(len(labels_dic))

        # Label reconstruction as vector
        l = np.zeros((len(labels), np.max(labels)))
        for i in range(0,len(labels)):
            l[i,labels[i]-1] = 1
        labels = l

        print("Randomization")
        idx = np.random.randint(data.shape[0], size=data.shape[0])
        labels = labels[idx,:]
        data   = data[idx,:]

        return data, labels, labels_dic

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

    def print_sample(self,dataX, dataY, classe, print_all=False):
        id = np.zeros((1, self.n_classes))
        #print(id.shape)
        id[0, classe-1] = 1
        for i in range(0, dataY.shape[0]):
            a = dataY[i,:]
            if np.array_equiv(id,dataY[i,:]) is True:
                im = dataX[i,:].reshape((self.dataw, self.datah))
                print(im.shape)
                plt.ion()
                plt.imshow(im, interpolation='none')
                plt.show()
                if print_all is False:
                    return
                else:
                    plt.pause(0.5)


# Read all MATLAB6 files in folder and return the concatenate database with labels
def convert_datasets (folder, outfile=None):
    files = glob.glob(folder+"/*.mat")

    i = 0
    for f in files:
        print(f)
        matc = signal.io.loadmat(f)
        try:
            data = np.concatenate((data, matc['database'][0,0]['yes']), axis=0)
            labels = np.concatenate((labels, [[i, '"'+f+'"'] for x in matc['database'][0,0]['yes'] ]), axis=0)
        except NameError:
            data = matc['database'][0,0]['yes']
            labels = [[i, f] for x in matc['database'][0,0]['yes'] ]
        i = i + 1

    l = np.zeros((data.shape[0], i))
    for i in range(l.shape[0]):
        l[i,labels[i,0]] = 1
    labels = l

    print("Randomization")
    idx = np.random.randint(data.shape[0], size=data.shape[0])
    labels = labels[idx,:]
    data   = data[idx,:]

    if outfile is not None:
        print("Saving in "+outfile+"_data.npy" )
        np.save(outfile+"_data", data)
        print("Saving in "+outfile+"_labels.npy" )
        np.save(outfile+"_labels",labels)
    return data, labels


def reshape_dataset(dataset, cutoff, shape_ori=(92,638)):
    for l in dataset:
        x = np.reshape(l, shape_ori)
        x = x[:, [x for x in range(0, cutoff)]]
        x = np.reshape(x, [1, shape_ori[0] * cutoff])
        try:
            res = np.concatenate((res, x), axis=0)
        except:
            res = x
        if res.shape[0] % 100 == 0:
            print(res.shape[0])
    return res

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.set_defaults(out=False, build=False, read=False, show=False)
    parser.add_option("-b", "--build", action="store", type="string", dest="build")
    parser.add_option("-o", "--out", action="store", type="string", dest="out")
    parser.add_option("-r", "--read", action="store", type="string", dest="read")
    parser.add_option("-s", "--show", action="store", type="string", dest="show")
    (options, args) = parser.parse_args()

    # Build a dataset from a folder containing wav files
    if options.build:
        if options.out is False:
            print('Destination filename must be specified --out=filename')
            quit()

        data = Dataset()
        data, labels, labels_dic = data.load_from_wav(options.build)
        np.save(options.out + "_data", data)
        np.save(options.out + "_labels", labels)
        np.save(options.out + "_labels_dic", labels_dic)

    # Read a dataset and plot all example of a classe
    if options.read:
        if options.show is False:
            print('Classe number to view must be specified --show=X')
            quit()
        data = Dataset(options.read,data_size=(150,186))
        data.print_sample(np.abs(data.data), data.labels, int(options.show), print_all=True)

# Convert all dataset from Tidzam 1 to new format
#data, labels = convert_datasets("database/dataset","out")
#data, labels = load_dataset("out")

# Reshape a dataset
#data = reshape_dataset(data, 300)
#print("Saving in out_data_reshape.npy" )
#np.save("out_data_reshape", data)
#print("Saving in out_labels_reshape.npy" )
#np.save("out_labels_reshape",labels)
#print_sample(data[0], shape=(92,300))
