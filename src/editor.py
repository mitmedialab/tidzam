import numpy as np
import optparse
import soundfile as sf
import sounddevice as sd

import data as tiddata

class Editor:
    def __init__(self,dataset=None):
        self.count_run = -1
        self.sample_size = 24000
        self.dataset = tiddata.Dataset()
        self.init = False

        if dataset is not None:
            self.load_dataset(dataset)

    def load_dataset(self,dataset):
        self.dataset = tiddata.Dataset(dataset)
        self.init = True

    def menu(self):
        print("===============")
        print("Classes\n---------------")
        for i in range(0, len(self.dataset.labels_dic)):
            print(str(i) + " : " + str(self.dataset.labels_dic[i]) )
        print("Actions:\n---------------")
        print("* (o): Open a dataset.")
        print("* (l): Load a folder of WAV files.")
        print("* (m): Merge with an other dataset.")
        print("* (s): Save the dataset.")
        print("-------------------")
        print("* (n): Create a new classe")
        print("* (i): Information on dataset")
        print("* (b): Balance classes")
        print("* (r): Randomize the dataset")
        print("-------------------")
        print("* (enter): next sample")
        print("* (q): quit")
        a = input()

        if a == 'o':
            print("Dataset:")
            dataset_path = input()
            self.load_dataset(dataset_path)

        elif a == 'l':
            print("Folder:")
            folder = input()
            print("Import as single classe ? [y/N]")
            single = input()
            if single == 'y':
                print("Class name:")
                single = input()
            else:
                single = None
            try:
                self.dataset.load_from_wav_folder(folder,asOneclasse=single)
            except:
                print("Impossible to load " + folder +"\n")

        elif a == 's':
            print("Dataset name: ")
            out = input()
            self.dataset.save(out)
            print('Save')

        elif a == 'n':
            print('New classe name: ')
            name = input()
            try:
                print(self.dataset.labels_dic)
                self.dataset.labels_dic = np.append(self.dataset.labels_dic, name)
            except NameError:
                self.dataset.labels_dic = name

        elif a == 'm':
            print("Merge with dataset:")
            name = input()
            dataset = tiddata.Dataset(name)
            print("As a single classe ? (y/N)")
            a = input()
            if a == 'y':
                print("Mother classe name to create:")
                classe = input()
                self.dataset.merge(dataset, asOneClasse=classe)
            else:
                self.dataset.merge(dataset)

        elif a == 'b':
            nb = np.max(self.dataset.get_sample_count_by_classe())
            print("NB samples : ", nb)

            for cl in range(self.dataset.labels.shape[1]):
                print(self.dataset.labels_dic[cl])
                samples = self.dataset.get_classe(cl)
                nb_cl = self.dataset.get_classe(cl).shape[0]
                while nb_cl < nb:
                    idx = np.arange(len(samples))
                    np.random.shuffle(idx)
                    idx = idx[:int(nb-nb_cl)]
                    self.dataset.data = np.concatenate((self.dataset.data, samples[idx]),axis=0)

                    id_cl = np.zeros( (len(idx), self.dataset.labels.shape[1]))
                    id_cl[:,cl] = 1
                    self.dataset.labels = np.concatenate((self.dataset.labels,id_cl),axis=0)
                    nb_cl = self.dataset.get_classe(cl).shape[0]

        elif a == 'p':
            pass

        elif a == 'r':
            print("Randomization")
            try:
                self.dataset.randomize()
            except:
                print("No data.")
        elif a == 'i':
            print('Informations:\n--------------')
            try:
                print(str(self.dataset.data.shape[0]) +" samples of " + str(self.dataset.data.shape[1]) + " features in " +
                    str(self.dataset.labels.shape[1]) + " classes.")
                print(self.dataset.labels_dic)
                print("Samples distribution:")
                print(self.dataset.get_sample_count_by_classe())
                print("Print labels:")
                print(self.dataset.labels)
            except:
                print('No data.')

        elif a == 'q':
            quit()

        elif a == '':
            pass
        else:
            return a
        return None

    def run(self):
        while True:
            self.menu()

    def run_stream(self, stream, show=False):
        with sf.SoundFile(stream, 'r') as f:
            while f.tell() < len(f):
                data = f.read(self.sample_size)
                self.count_run = self.count_run + 1

                time = str(int( (self.count_run * 0.5) / 3600) ) + ":" + \
                    str( int( (self.count_run * 0.5 % 3600)/60) ) + ":" + \
                    str( int( (self.count_run * 0.5 % 3600 % 60)) ) + ":" + \
                    str( int( ((self.count_run * 0.5 % 3600 % 60) * 1000) % 1000) ) + "ms"

                for i in range(0,f.channels):
                    if f.channels > 1:
                        data_chan = data[:,i]
                    else:
                        data_chan = data

                    while True:
                        fs, t, Sxx = tiddata.get_spectrogram(data_chan, f.samplerate, i,  show=show)
                        print("\n===============")
                        print("Channel: " + str(i) + "\n---------------")
                        print("Timestamp: " + time + "\n---------------")
                        print("Actions:")
                        print("* (g): go to")

                        if show is True:
                            sd.play(data_chan, 48000)

                        a = self.menu()
                        if a == ' ':
                            break

                        elif a == 'g':
                            print('Timestamp destination: (hh:mm:s:ms)')
                            d = input()
                            d = d.split(':')
                            self.count_run = (int(d[0])*3600 + int(d[1])*60 + int(d[2]) + (int(d[3])*2))*2
                            f.seek(self.count_run * self.sample_size)
                            self.count_run = self.count_run - 1
                            i = f.channels + 1
                            break

                        elif a is not None and Sxx is not None:
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
    parser = optparse.OptionParser(usage="python src/editor.py")
    parser.add_option("--open", action="store", type="string", dest="open",
        default=None, help="Open an exisiting dataset")

    parser.add_option("--stream", action="store", type="string", dest="stream",
        default=None, help="Sample extraction from an audio stream [WAV/OGG/MP3].")

    parser.add_option("--play", action="store_true",  dest="play",
        default=False, help="Play the dataset content.")

    parser.add_option("--play-id", action="store", type="int",  dest="playID",
        default=False, help="Play the dataset content of a particular classe.")

    parser.add_option("-s", "--show", action="store_true", dest="show",
        default=False, help="Select a specific classe ID fpr --play option.")


    (options, args) = parser.parse_args()

    obj_editor = Editor()
    if options.open:
        obj_editor.load_dataset(options.open)

    # Open a dataset and plot all example of a classe
    if options.play:
        if options.open is None:
            print("You must specify a dataset to open.")
        else:
            data = tiddata.Dataset(options.open,data_size=(150,186))
            data.print_sample(np.abs(data.data), data.labels, options.playID, print_all=True)

    # Run on an audio stream to extract samples
    elif options.stream:
        obj_editor.run_stream(options.stream, show=options.show)

    # Start in normal mode
    else:
        obj_editor.run()
