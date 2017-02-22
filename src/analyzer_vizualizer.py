import sys
import numpy as np
import Queue
import multiprocessing as mp
import threading

from matplotlib import pyplot as plt
import matplotlib.animation as animation
from threading import Thread

class TidzamVizualizer (Thread):
    def __init__(self, channels_to_print=[]):
        Thread.__init__(self)
        self.init = True
        self.channels_to_print = channels_to_print
        self.data_size      = (150,186)
        self.out_queue_show = mp.Queue()
        self.lock = threading.Lock()

        self.stopFlag = False

    def execute(self, Sxxs, fs, t, sound_obj, overlap=0.5):
        if self.init:
            self.init = False
            if len(self.channels_to_print) == 0:
                self.channels_to_print = range(Sxxs.shape[0])
            self.start()

        self.out_queue_show.put([fs, t, Sxxs])

    def stop(self):
        self.stopFlag = True

    def run(self):
        self.vizualize(self.channels_to_print )

    def vizualize(self, channels_to_print=[] ):
        self.show = True
        self.ims = []
        self.channels_to_print = channels_to_print

        nb_plot = len(self.channels_to_print)
        if nb_plot < 2:
            nb_plot = 2

        self.fig, self.ax = plt.subplots(nb_plot, sharex=True)
        self.win = self.fig.canvas.manager.window

        for i in range(len(self.channels_to_print)):
            self.ims.append(self.ax[i].pcolormesh(np.ones(self.data_size,dtype=float),
                    vmin=0,
                    vmax=1))

        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        #self.an1 = animation.FuncAnimation(self.fig, self.animate, interval=100, repeat=True)
        self.win.after(100, self.animate)
        plt.show()

    def animate(self):
        try:
            data = self.out_queue_show.get_nowait()
            for i in range(len(self.channels_to_print)):
                sample = data[2][self.channels_to_print[i],:]
                Sxx = np.reshape(sample, [self.data_size[0],self.data_size[1]] )
                self.ims[i].set_array(Sxx.ravel())
            self.fig.canvas.draw()  # redraw the canvas
            print('Spectrogram Updated')
        except Queue.Empty:
            pass
            #print('Waiting data ...')

        if self.stopFlag is False:
            self.win.after(100, self.animate)
        else:
            plt.close('all')
