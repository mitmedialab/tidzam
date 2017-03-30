import threading
import soundfile as sf
import os
import copy
# MUST BE THREADED

class SampleExtractor(threading.Thread):
    def __init__(self, classes_to_extract, wav_folder='/tmp/tidzam/opus'):
        threading.Thread.__init__(self)
        self.wav_folder = wav_folder
        self.classes_to_extract = classes_to_extract
        self.stopFlag = threading.Event()

        self.buffer = []

        if not os.path.exists(self.wav_folder):
            os.makedirs(self.wav_folder)

        print("WAV destination folder: " + wav_folder)

        self.start()

    def run(self):
        while not self.stopFlag.wait(1):
            for o in self.buffer:
                sf.write (self.wav_folder + '/+' + o[1] + '(' + str(o[0]) + ')_' + o[2] +'.wav', o[3], o[4])
                self.buffer.remove(o)

    def execute(self, prob_classes, predictions, classes_dic, sound_obj=None, time=None):
        for channel in range(len(prob_classes)):
            for cl in self.classes_to_extract:
                if predictions[channel] == cl:
                    self.buffer.append([channel, predictions[channel], time, sound_obj[0][:,channel], sound_obj[1] ])
