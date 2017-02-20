import jack
import sys
import numpy as np
import Queue
import multiprocessing as mp
import threading

from matplotlib import pyplot as plt

import data as tiddata

class TidzamJack:
    def __init__(self, port_name, callable_objects=[]):
        self.show = False
        self.data_size = (150,186)
        self.callable_objects = callable_objects
        self.lock = threading.Lock()

        self.client = jack.Client("tidzam")
        self.ports = self.client.get_ports(port_name)

        self.first = True
        self.samplerate = -1
        self.blocksize = -1
        self.buffer_size = 24000

        self.channels = []
        self.channels_data = []
        self.out_queue_show = []

        for i in range(0, len(self.ports)):
            self.channels.append(self.client.inports.register("chan"+str(i)))
            self.out_queue_show.append(mp.Queue())

        self.client.set_samplerate_callback(self.callback_samplerate)
        self.client.set_blocksize_callback(self.callback_blocksize)
        self.client.set_process_callback(self.callback)
        self.client.activate()

        for i in range(0, len(self.ports)): #p in ports:
            self.client.connect(self.ports[i], self.channels[i])

    def callback_samplerate(self, samplerate):
        self.samplerate = samplerate
        print("Sample rate: " + str(samplerate) + "Hz" )

    def callback_blocksize(self, blocksize):
        self.blocksize = blocksize
        print("Blocksize: " + str(blocksize))

    def callback(self, frame):
        run = False
        datas = []

        self.lock.acquire()
        for i in range(0, len(self.channels)):
            # Store the received data in the corresponding buffer or create one
            try:
                self.channels_data[i] = np.concatenate((self.channels_data[i], self.channels[i].get_array()))
            except:
                self.channels_data.append( self.channels[i].get_array().tolist() )

            # If the buffer contains the required data, we truncate it and send result
            if len(self.channels_data[i]) >= self.buffer_size:
                run = True
                data = self.channels_data[i][0:self.buffer_size]
                self.channels_data[i] = self.channels_data[i][self.buffer_size:len(self.channels_data[i])]

                #print("Buffer " + str(i) + ": "+ str(len(data)) + " Bytes" )
                fs, t, Sxx = tiddata.get_spectrogram(data.astype(float),
                            self.samplerate)

                if self.show:
                    self.out_queue_show[i].put([fs, t, Sxx])

                datas.append(data)
                if i == 0:
                    Sxxs = Sxx
                    fss = fs
                    ts = t
                else:
                    Sxxs = np.concatenate((Sxxs, Sxx), axis=0)
                    fss = np.concatenate((fss, fs), axis=0)
                    ts = np.concatenate((ts, t), axis=0)

        if run is True:
            for obj in self.callable_objects:
                obj.run(Sxxs, fss, ts, [datas, self.samplerate], overlap=0)
        self.lock.release()

    ### Functions to draw channel spectrograms
    def vizualize(self, channels_to_print=[] ):
        self.show = True
        self.ims = []
        self.channels_to_print = channels_to_print

        nb_plot = len(self.channels_to_print)
        if nb_plot == 0:
            self.channels_to_print = range(len(self.channels))
            nb_plot = len(self.channels_to_print)
        elif nb_plot < 2:
            nb_plot = 2

        self.fig, self.ax = plt.subplots(nb_plot, sharex=True)
        self.win = self.fig.canvas.manager.window

        for i in range(len(self.channels_to_print)):
            self.ims.append(self.ax[i].pcolormesh(np.ones(self.data_size,dtype=float),
                vmin=0,
                vmax=1))
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        self.win.after(100, self.animate)
        plt.show()

    def animate(self):
        self.lock.acquire()
        for i in range(len(self.channels_to_print)):
            try:
                sample = self.out_queue_show[self.channels_to_print[i]].get_nowait()
            except Queue.Empty:
                print('empty')
                pass
            else:
                Sxx = np.reshape(sample[2], [self.data_size[0],self.data_size[1]] )
                self.ims[i].set_array(Sxx.ravel())
        self.fig.canvas.draw()  # redraw the canvas
        print('Spectrogram Updated')
        self.lock.release()
        self.win.after(100, self.animate)

if __name__ == "__main__":
    connector = TidzamJack("mpv:out*")
    connector.vizualize()
