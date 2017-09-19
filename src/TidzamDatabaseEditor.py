import numpy as np
import optparse
import soundfile as sf
import sounddevice as sd

import TidzamDatabase as database

from App import App

class Editor:
    def __init__(self,dataset=None):
        self.count_run = -1
        self.dataset = database.Dataset()
        self.init = False

        if dataset is not None:
            self.load_dataset(dataset)

    def load_dataset(self,dataset):
        self.dataset = database.Dataset(dataset)
        self.init = True

    def menu(self):
        App.log(0, "===============")
        App.log(0, "Classes\n---------------")
        for i in range(0, len(self.dataset.labels_dic)):
            App.log(0, str(i) + " : " + str(self.dataset.labels_dic[i]) )
        App.log(0, "Actions:\n---------------")
        App.log(0, "* (o): Open a dataset.")
        App.log(0, "* (l): Load a folder of WAV files.")
        App.log(0, "* (S): Save the dataset (metadata generation).")
        App.log(0, "* (m): Merge with an other dataset.")
        App.log(0, "* (s): Split into two dataset.")
        App.log(0, "-------------------")
        App.log(0, "* (n): Create a new classe")
        App.log(0, "* (i): Information on dataset")
        App.log(0, "* (b): Balance classes")
        App.log(0, "* (r): Randomize the dataset")
        App.log(0, "-------------------")
        App.log(0, "* (enter): next sample")
        App.log(0, "* (q): quit")
        a = input()

        if a == 'o':
            App.log(0, "Dataset:")
            dataset_path = input()
            self.load_dataset(dataset_path)

        elif a == 'S':
            App.log(0, "Metadata generation.")
            self.dataset.save_meta()

        elif a == 's':
            App.log(0, "Proportion:")
            p = float(input())
            self.dataset.split_dataset(p=p)

        elif a == 'l':
            App.log(0, "Folder:")
            folder = input()
            App.log(0, "Import as single classe ? [y/N]")
            single = input()
            if single == 'y':
                App.log(0, "Class name:")
                single = input()
            else:
                single = None
            if True:
                self.dataset.load_from_wav_folder(folder,asOneclasse=single)
            #except:
            #    App.log(0, "Impossible to load " + folder +"\n")

        elif a == 'n':
            App.log(0, 'New classe name: ')
            name = input()
            self.dataset.create_classe(name)

        elif a == 'm':
            App.log(0, "Merge with dataset:")
            name = input()
            #dataset = database.Dataset(name)
            App.log(0, "As a single classe ? (y/N)")
            a = input()
            if a == 'y':
                App.log(0, "Mother classe name:")
                classe = input()
                self.dataset.merge(name, asOneClasse=classe)
            else:
                self.dataset.merge(name)

        elif a == 'b':
            self.dataset.balance_classe()

        elif a == 'p':
            pass

        elif a == 'r':
            App.log(0, "Randomization")
            #try:
            if True:
                self.dataset.randomize()
            #except:
            #    App.log(0, "No data.")
        elif a == 'i':
            App.log(0, 'Informations:\n--------------')
            try:
                App.log(0, str(self.dataset.count_samples()) +" samples of " +
                    str(self.dataset.get_nb_features() ) + " features in " +
                    str(len(self.dataset.get_classes()) ) + " classes.")
                App.log(0, self.dataset.get_classes())
                App.log(0, "Samples distribution:")
                App.log(0, self.dataset.get_sample_count_by_classe())
            except:
                App.log(0, 'No data.')

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
                data = f.read(int(f.samplerate/2))
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
                        fs, t, Sxx = database.get_spectrogram(data_chan, f.samplerate, i,  show=show)
                        App.log(0, "\n===============")
                        App.log(0, "Channel: " + str(i) + "\n---------------")
                        App.log(0, "Timestamp: " + time + "\n---------------")
                        App.log(0, "Actions:")
                        App.log(0, "* (g): go to")

                        if show is True:
                            sd.play(data_chan, 48000)

                        a = self.menu()
                        if a == ' ':
                            break

                        elif a == 'g':
                            App.log(0, 'Timestamp destination: (hh:mm:s:ms)')
                            d = input()
                            d = d.split(':')
                            self.count_run = (int(d[0])*3600 + int(d[1])*60 + int(d[2]) + (int(d[3])*2))*2
                            f.seek(self.count_run * int(f.samplerate/2))
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
                                    App.log(0, str(self.dataset.labels.shape[0]) + " samples of " + str(self.dataset.labels.shape[1]) + " classes")
                                    break
                            except:
                                pass


if __name__ == "__main__":
    parser = optparse.OptionParser(usage="python src/TidzamDatabaseEditor.py")
    parser.add_option("--dataset", action="store", type="string", dest="open",
        default=None, help="Open an exisiting dataset")

    parser.add_option("--stream", action="store", type="string", dest="stream",
        default=None, help="Sample extraction from an audio stream [WAV/OGG/MP3].")

    parser.add_option("--play", action="store_true",  dest="play",
        default=False, help="Play the dataset content.")

    parser.add_option("--play-id", action="store", type="int",  dest="playID",
        default=False, help="Play the dataset content of a particular classe.")

    parser.add_option("-s", "--show", action="store_true", dest="show",
        default=False, help="Select a specific classe ID for --play option.")


    (options, args) = parser.parse_args()

    obj_editor = Editor()
    if options.open:
        obj_editor.load_dataset(options.open)

    # Open a dataset and plot all example of a classe
    if options.play:
        if options.open is None:
            App.log(0, "You must specify a dataset to open.")
        else:
            data = database.Dataset(options.open,data_size=(150,186))
            data.print_sample(np.abs(data.data), data.labels, options.playID, print_all=True)

    # Run on an audio stream to extract samples
    elif options.stream:
        obj_editor.run_stream(options.stream, show=options.show)

    # Start in normal mode
    else:
        obj_editor.run()
