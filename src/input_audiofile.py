import soundfile as sf
import numpy as np
from threading import Thread
import os, glob

import TidzamDatabase as database

from App import App

class TidzamAudiofile(Thread):
    def __init__(self, streams, callable_objects=[], overlap=0, channel=None, cutoff=[20,170]):
        Thread.__init__(self)

        if os.path.isdir(streams) is True:
            self.filenames = glob.glob(streams+"/*")
        else:
            self.filenames = [streams]

        self.callable_objects   = callable_objects
        self.overlap            = overlap
        self.channel            = channel
        self.cutoff             = cutoff

    def stop(self):
        return

    def run(self):
        for audiofilename in self.filenames:
            with sf.SoundFile(audiofilename, 'r') as f:

                if self.channel is None:
                    channels = range(0,f.channels)
                else:
                    channels = range(self.channel,self.channel+1)

                while f.tell() < len(f):
                    data = f.read(int(f.samplerate/2))

                    if (len(data) < int(f.samplerate/2)):
                        break

                    for i in channels:
                        if f.channels > 1:
                            fs, t, Sxx, size  = database.get_spectrogram(data[:,i], f.samplerate, i, cutoff=self.cutoff)
                        else:
                            fs, t, Sxx, size = database.get_spectrogram(data, f.samplerate, i, cutoff=self.cutoff)

                        if i == 0:
                            Sxxs = Sxx
                            fss = fs
                            ts = t
                        else:
                            Sxxs = np.concatenate((Sxxs, Sxx), axis=0)
                            fss = np.concatenate((fss, fs), axis=0)
                            ts = np.concatenate((ts, t), axis=0)

                    for obj in self.callable_objects:
                        obj.execute({
                            "fft":{
                                "data":Sxxs,
                                "time_scale":ts,
                                "freq_scale":fss,
                                "size":size
                                },
                            "samplerate":f.samplerate,
                            "sources":None,
                            "audio":data,
                            "overlap":self.overlap,
                            "mapping:None"
                            })

                    f.seek(int(-int(f.samplerate/2)*self.overlap), whence=sf.SEEK_CUR)
        App.log(0, "End of stream ...")
        os._exit(0)
