import threading
import soundfile as sf
import numpy as np
import random
import os
import copy
import glob

class SampleExtractor(threading.Thread):
    def __init__(self, classes_to_extract, channels=[], extraction_dest='/tmp/tidzam/opus', dd=False, debug=0):
        threading.Thread.__init__(self)
        self.extraction_dest        = extraction_dest
        self.classes_to_extract     = classes_to_extract
        self.channels               = channels
        self.stopFlag               = threading.Event()
        self.debug                  = debug
        self.buffer                 = []

        if not os.path.exists(self.extraction_dest):
            os.makedirs(self.extraction_dest)

        if not os.path.exists(self.extraction_dest + '/unchecked/'):
            os.makedirs(self.extraction_dest + '/unchecked/')

        print("===== SAMPLE EXTRACTOR =====")
        print("Classes: ", self.classes_to_extract)
        print("WAV destination folder: " + extraction_dest)

        self.dd = dd
        self.dynamic_distribution = []
        self.dynamic_distribution_prev = []
        self.dynamic_distribution_inc = 0

        # Preload the list of classe already extracted in extraction_dest folder
        self.dynamic_distribution_classes = []

        for f in glob.glob(self.extraction_dest + "/*/"):
            f = f.split("/")
            f = f[len(f)-2]
            if f not in self.dynamic_distribution_classes:
                for cl in self.classes_to_extract: # Only directory interested in extraction rule
                    if cl in f:
                        self.dynamic_distribution_classes.append(f)
                        break

        for cl in self.classes_to_extract:
            if cl not in self.dynamic_distribution_classes:
                self.dynamic_distribution_classes.append(cl)

        if self.dd is True:
            self.dynamic_distribution_update()

        self.start()

    def dynamic_distribution_update(self):
        count = np.zeros(len(self.dynamic_distribution_classes))

        for f in glob.glob(self.extraction_dest + "/*/*"):
            for i, cl in enumerate(self.dynamic_distribution_classes):
                if cl in f:
                    count[i] = count[i] + 1
        self.dynamic_distribution = count/np.max(count)

        if self.debug > 0 and np.array_equiv(self.dynamic_distribution_prev,self.dynamic_distribution) is False:
            self.dynamic_distribution_prev = self.dynamic_distribution
            print("\n** Sample Extractor **: Extraction Dynamic Distribution Update")
            for i, cl in enumerate(self.dynamic_distribution_classes):
                print(cl + ": " + str(self.dynamic_distribution[i]) )

    def dynamic_distribution_decision(self, classe):
        for i, cl in enumerate(self.dynamic_distribution_classes):
            if cl == classe:
                try:
                    if random.uniform(0, 1) > self.dynamic_distribution[i]:
                        return True
                except:
                    pass # This is a new registered classe, the update has not be done
                return False

    def run(self):
        while not self.stopFlag.wait(0.1):
            # Compute the dynamic distribution in order to extract the samples
            if self.dd is True:
                self.dynamic_distribution_inc = self.dynamic_distribution_inc + 1
                if self.dynamic_distribution_inc > 1000:
                    self.dynamic_distribution_inc = 0
                    self.dynamic_distribution_update()

            # Process all extracted samples in buffer queue
            for o in self.buffer:
                sf.write (self.extraction_dest + '/unchecked/+' + o[1] + '(' + str(o[0]) + ')_' + o[2] +'.wav', o[3], o[4])
                try:
                    self.buffer.remove(o)
                except:
                    print("** Sample Extractor **: Unable to remove extracted sample from queue.")
            if len(self.buffer) > 50:
                print("** WARNING ** Sample extractor : buffer queue is " + str(len(self.buffer)))

    def execute(self, prob_classes, predictions, classes_dic, sound_obj=None, time=None, mapping=None):
        for channel in range(len(prob_classes)):
            if len(self.channels) > 0 and self.channels[0] != ""  and str(channel) not in self.channels:
                continue

            for cl in self.classes_to_extract:
                if cl in predictions[channel]:
                    if predictions[channel] not in self.dynamic_distribution_classes:
                        self.dynamic_distribution_classes.append(predictions[channel])

                    if self.dd is False or self.dynamic_distribution_decision(predictions[channel]) is True:
                        try:
                            self.buffer.append([channel+1, predictions[channel], time, sound_obj[0][:,channel], sound_obj[1] ])
                        except:
                            self.buffer.append([channel+1, predictions[channel], time, sound_obj[0], sound_obj[1] ])
