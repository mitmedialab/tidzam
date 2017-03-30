import soundfile as sf
import os

# MUST BE THREADED

class SampleExtractor:
    def __init__(self, classes_to_extract, wav_folder='/tmp/tidzam/opus'):
        self.wav_folder = wav_folder
        self.classes_to_extract = classes_to_extract

        if not os.path.exists(self.wav_folder):
            os.makedirs(self.wav_folder)

        print("WAV destination folder: " + wav_folder)

    def execute(self, prob_classes, predictions, classes_dic, sound_obj=None, time=None):
        for channel in range(len(prob_classes)):
            for cl in self.classes_to_extract:
                if predictions[channel] == cl:
                    sf.write (self.wav_folder + '/+' + predictions[channel] + '(' + str(channel) + ')_' + time +'.wav',
                        sound_obj[0][:,channel], sound_obj[1])
