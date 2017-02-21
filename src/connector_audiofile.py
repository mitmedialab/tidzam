import soundfile as sf
import numpy as np

import data as tiddata

class TidzamAudiofile:
    def __init__(self, audiofilename, callable_objects=[], overlap=0):
        self.audiofilename      = audiofilename
        self.callable_objects   = callable_objects
        self.overlap            = overlap

    def start(self):
        with sf.SoundFile(self.audiofilename, 'r') as f:
            while f.tell() < len(f):
                data = f.read(24000)
                for i in range(0,f.channels):
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
                    obj.execute(Sxxs, fss, ts, [data, f.samplerate], overlap=self.overlap)

                f.seek(int(-24000*self.overlap), whence=sf.SEEK_CUR)
