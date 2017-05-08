import soundfile as sf
import numpy as np
from threading import Thread
import os

import data as tiddata

class TidzamAudiofile(Thread):
    def __init__(self, audiofilename, callable_objects=[], overlap=0, channel=None):
        Thread.__init__(self)
        self.audiofilename      = audiofilename
        self.callable_objects   = callable_objects
        self.overlap            = overlap
        self.channel            = channel

    def stop(self):
        return

    def run(self):
        with sf.SoundFile(self.audiofilename, 'r') as f:
            if self.channel is None:
                channels = range(0,f.channels)
            else:
                channels = range(self.channel,self.channel+1)

            while f.tell() < len(f):
                data = f.read(24000)

                if (len(data) < 24000):
                    print("End of stream ...")
                    os._exit(0)

                for i in channels:
                    if f.channels > 1:
                        fs, t, Sxx = tiddata.get_spectrogram(data[:,i], f.samplerate, i)
                    else:
                        fs, t, Sxx = tiddata.get_spectrogram(data, f.samplerate, i)

                    if i == 0:
                        Sxxs = Sxx
                        fss = fs
                        ts = t
                    else:
                        Sxxs = np.concatenate((Sxxs, Sxx), axis=0)
                        fss = np.concatenate((fss, fs), axis=0)
                        ts = np.concatenate((ts, t), axis=0)

                for obj in self.callable_objects:
                    obj.execute(Sxxs, fss, ts, [data, f.samplerate], overlap=self.overlap,stream=self.audiofilename)

                f.seek(int(-24000*self.overlap), whence=sf.SEEK_CUR)
