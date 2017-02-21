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
        self.data_size = (150,186)
        self.callable_objects = callable_objects
        self.lock = threading.Lock()

        self.client = jack.Client("tidzam")
        self.ports = self.client.get_ports(port_name)

        self.samplerate = -1
        self.blocksize = -1
        self.buffer_size = 24000

        self.channels = []
        self.channels_data = []

        for i in range(0, len(self.ports)):
            self.channels.append(self.client.inports.register("chan"+str(i)))

        self.client.set_samplerate_callback(self.callback_samplerate)
        self.client.set_blocksize_callback(self.callback_blocksize)
        self.client.set_process_callback(self.callback)


    def start(self):
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
                data = np.transpose(self.channels_data[i][0:self.buffer_size])
                self.channels_data[i] = self.channels_data[i][self.buffer_size:len(self.channels_data[i])]

                #print("Buffer " + str(i) + ": "+ str(len(data)) + " Bytes" )
                fs, t, Sxx = tiddata.get_spectrogram(data.astype(float),
                            self.samplerate)

                if i == 0:
                    datas = np.transpose(data)
                    Sxxs = Sxx
                    fss = fs
                    ts = t
                else:
                    Sxxs = np.vstack((Sxxs, Sxx))
                    fss = np.vstack((fss, fs))
                    ts = np.vstack((ts, t))
                    datas = np.vstack((datas, data))

        if run is True:
            for obj in self.callable_objects:
                obj.execute(Sxxs, fss, ts, [np.transpose(datas), self.samplerate], overlap=0)
        self.lock.release()
