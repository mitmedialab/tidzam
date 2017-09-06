import threading
import soundfile as sf
import numpy as np
import random
import os
import copy
import glob

class SampleExtractor(threading.Thread):
    def __init__(self, classes_to_extract, channels=[], extraction_dest='/tmp/tidzam/opus', dd=True, debug=0):
        threading.Thread.__init__(self)
        global EXTRACTION_RULES

        self.label_dic              = []

        self.extraction_dest        = extraction_dest
        self.classes_to_extract     = classes_to_extract
        self.channels               = channels
        self.stopFlag               = threading.Event()
        self.debug                  = debug
        self.buffer                 = []

        EXTRACTION_RULES            = {}

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

        self.start()

    def dynamic_distribution_update(self):
        count = np.zeros(len(self.label_dic))
        primary_count = {}
        for i, classe in enumerate(self.label_dic):
            # Compute the number of sample of this classe
            count[i] += len(glob.glob(self.extraction_dest + "/**/"+classe+"*/**/*.wav", recursive=True))

            # Get the name of its primary classe in order to determine if it is the biggest classe
            primary_name = "".join(classe.split("-")[:-1])
            if primary_count.get(primary_name) is None:
                primary_count[primary_name] = 0
            primary_count[primary_name] = max(primary_count[primary_name], count[i])

        # Normalize the distribution
        for i, classe in enumerate(self.label_dic):
            primary_name = "".join(classe.split("-")[:-1])
            count[i] /= primary_count[primary_name]
        self.dynamic_distribution = count

        if self.debug > 0 and np.array_equiv(self.dynamic_distribution_prev,self.dynamic_distribution) is False:
            self.dynamic_distribution_prev = self.dynamic_distribution
            print("\n** Sample Extractor **: Extraction Dynamic Distribution Update")
            for i, classe in enumerate(self.label_dic):
                print(classe + ": " + str(self.dynamic_distribution[i]) )

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
                sf.write (self.extraction_dest + '/unchecked/+' + o[1] + '(' + str(o[0].replace("_","-")) + ')_' + o[2] +'.wav', o[3], o[4])
                try:
                    self.buffer.remove(o)
                except:
                    print("** Sample Extractor **: Unable to remove extracted sample from queue.")
            if len(self.buffer) > 50:
                print("** WARNING ** Sample extractor : buffer queue is " + str(len(self.buffer)))

    def evaluate_extraction_rules(self, channel, results):
        global EXTRACTION_RULES
        channel = channel.replace(":","-")
        if channel in EXTRACTION_RULES:
            if EXTRACTION_RULES[channel]["classes"]:
                for cl in EXTRACTION_RULES[channel]["classes"].split(","):
                    if cl in results:
                        if EXTRACTION_RULES[channel]["rate"] is None:
                            EXTRACTION_RULES[channel]["rate"] = 0

                        if EXTRACTION_RULES[channel]["rate"] == "auto":
                            if cl == "unknow":
                                return True

                            if len(self.dynamic_distribution) > 0:
                                if random.uniform(0, 1) > self.dynamic_distribution[self.label_dic.index(cl)]:
                                    return True

                        elif random.uniform(0, 1) > 1 - float(EXTRACTION_RULES[channel]["rate"]):
                            return True
        return False

    def execute(self, results, label_dic):
        if len(self.label_dic) == 0:
            self.label_dic = label_dic
            self.dynamic_distribution_update()

        for i, channel in enumerate(results):
            try:
                if self.evaluate_extraction_rules(channel["mapping"][0], channel["detections"]) is True:
                    self.buffer.append([channel["mapping"][0], str(channel["detections"]), channel["time"], channel["audio"], channel["samplerate"] ])
            except:
                print("** Sample Extractor **: Extraction rule error ("+str(EXTRACTION_RULES[channel])+")")
