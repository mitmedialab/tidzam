import threading
import soundfile as sf
import numpy as np
import random
import os
import copy
import glob

from socketIO_client import SocketIO
from App import App

class SampleExtractor(threading.Thread):
    def __init__(self, extraction_dest='/tmp/tidzam/opus', extraction_rules={}, dd=True):
        threading.Thread.__init__(self)
        self.lock   = threading.Lock()

        self.socketIO = None
        self.socketio_address = App.socketIOanalyzerAdress

        self.stopFlag               = threading.Event()
        self.buffer                 = []
        self.label_dic              = []

        self.dd = dd
        self.extraction_dest            = extraction_dest
        self.extraction_rules           = extraction_rules
        self.database_info         = {}

        self.dynamic_distribution       = []
        self.dynamic_distribution_prev  = []
        self.dynamic_distribution_inc   = 0

        if not os.path.exists(self.extraction_dest):
            os.makedirs(self.extraction_dest)

        if not os.path.exists(self.extraction_dest + '/unchecked/'):
            os.makedirs(self.extraction_dest + '/unchecked/')

        App.log(1, "Destination folder: " + extraction_dest)

        self.start()

    def process_socketIO(self, req):
        # TODO: SocketIO-client does nt support rooms for now, so broadcast to everybody (emitter field use for filtering)...

        if req.get("set") == 'rules':
            self.extraction_rules = req.get("rules")
            App.log(1, "New extraction rules received:  " + str(req.get("rules")))

        elif req.get("get") == 'rules':
            self.socketIO.emit("SampleExtractionRules",{"rules":self.extraction_rules, "emitter":"SampleExtractor"})

        elif req.get("get") == 'database_info':
            with self.lock:
                self.socketIO.emit("SampleExtractionRules",{"database_info":self.database_info, "emitter":"SampleExtractor"})

        elif req.get("emitter") and req.get("emitter") != "SampleExtractor":
            App.warning(0, "Bad request " + str(req))

    def init_socketIO(self):
        tmp = self.socketio_address.split(":")
        self.socketIO = SocketIO(tmp[0], int(tmp[1]))
        self.socketIO.on('SampleExtractionRules', self.process_socketIO)
        threading.Thread(target=self._run_socketIO).start()
        App.ok(0, "Connected to " + self.socketio_address +"")

    def _run_socketIO(self):
        while not self.stopFlag.wait(0.1):
            self.socketIO.wait(1)

    def dynamic_distribution_update(self):
        with self.lock:
            self.database_info          = {}
            self.dynamic_distribution   = {}
            primary_count               = {}
            count                       = np.zeros(len(self.label_dic))

            for i, classe in enumerate(self.label_dic):
                # Compute the number of sample of this classe
                count[i]  += len(glob.glob(self.extraction_dest + "/**/"+classe+"*/**/*.wav", recursive=True))
                self.database_info[classe] = count[i]

                # Get the name of its primary classe in order to determine if it is the biggest classe
                primary_name = "".join(classe.split("-")[:-1])
                if primary_count.get(primary_name) is None:
                    primary_count[primary_name] = 0
                primary_count[primary_name] = max(primary_count[primary_name], count[i])

            self.database_info["unchecked"] = len(glob.glob(self.extraction_dest + "/**/unchecked/**/*.wav", recursive=True))

            # Normalize the distribution
            for i, classe in enumerate(self.label_dic):
                primary_name = "".join(classe.split("-")[:-1])
                count[i] /= primary_count[primary_name]

            self.dynamic_distribution = count

            if np.array_equiv(self.dynamic_distribution_prev,self.dynamic_distribution) is False:
                self.dynamic_distribution_prev = self.dynamic_distribution
                App.log(1, "Extraction Dynamic Distribution Update")
                for i, classe in enumerate(self.label_dic):
                    App.log(1, " \t" + classe + ": " + str(self.dynamic_distribution[i]) )

    def run(self):
        while not self.stopFlag.wait(0.1):
            if self.socketIO is None:
                self.init_socketIO()

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
                    App.warning(0, "Unable to remove extracted sample from queue.")
            if len(self.buffer) > 50:
                App.warning(0, "Buffer queue is " + str(len(self.buffer)))

    def evaluate_extraction_rules(self, channel, results):
        channel = channel.replace(":","-")
        if channel in self.extraction_rules:
            if self.extraction_rules[channel]["classes"]:
                for cl in self.extraction_rules[channel]["classes"].split(","):
                    if cl in results:
                        if self.extraction_rules[channel]["rate"] is None:
                            self.extraction_rules[channel]["rate"] = 0

                        if self.extraction_rules[channel]["rate"] == "auto":
                            if cl == "unknow":
                                return True

                            if len(self.dynamic_distribution) > 0:
                                if random.uniform(0, 1) > self.dynamic_distribution[self.label_dic.index(cl)]:
                                    return True

                        elif random.uniform(0, 1) > 1 - float(self.extraction_rules[channel]["rate"]):
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
                App.error(0, "Extraction rule error ("+str(self.extraction_rules[channel])+")")
