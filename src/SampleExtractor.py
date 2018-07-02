import threading
import soundfile as sf
import numpy as np
import random
import os
import copy
import glob
import collections
import math
import scipy.misc

from socketIO_client import SocketIO
from App import App
import traceback

class SampleExtractor(threading.Thread):
    def __init__(self, extraction_dest='/tmp/tidzam/opus', extraction_rules={}, dd=True):
        threading.Thread.__init__(self)
        self.lock   = threading.Lock()

        self.socketIO = None
        self.socketio_address = App.socketIOanalyzerAdress

        self.stopFlag               = threading.Event()
        self.buffer                 = []
        self.label_dic              = []
        self.queue_fifo             = collections.OrderedDict()
        self.queue_fifo_length      = 600

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
        if isinstance(req, dict) is False:
            self.socketIO.emit("sys",
                {"error":"request must be a JSON.", "request-origin":req},
                room=sid)
            return

        if req.get("set") == 'rules':
            self.extraction_rules = req.get("rules")
            App.log(1, "New extraction rules received:  " + str(req.get("rules")))

        if req.get("get") == 'rules':
            self.socketIO.emit("SampleExtractionRules",{"rules":self.extraction_rules, "emitter":"SampleExtractor"})

        if req.get("get") == 'extracted_count':
            rsp = {}
            for channel in self.queue_fifo:
                rsp[channel] = self.queue_fifo[channel]["count"]
            self.socketIO.emit("SampleExtractionRules",{"extracted_count":rsp, "emitter":"SampleExtractor"})

        if req.get("get") == 'database_info':
            with self.lock:
                self.socketIO.emit("SampleExtractionRules",{"database_info":self.database_info, "emitter":"SampleExtractor"})

        if req.get("emitter") and req.get("emitter") != "SampleExtractor":
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

    def extraction__object_filter(self, sample, threshold=0.1, window=0.25):
        fft      = np.reshape(sample["fft"]["data"],sample["fft"]["size"])
        fft[fft > threshold] = 1
        fft[fft <= threshold] = 0

        if App.verbose >= 2:
            scipy.misc.imsave('ObjectFilter-output.jpg', fft)

        metric   = np.sum(fft[:,:int((window/2)*sample["fft"]["size"][0])])
        metric   += np.sum(fft[:,int((1-(window/2))*sample["fft"]["size"][0]):])
        metric   /= np.sum(fft)

        if metric < window:
            App.log(2, "Extract sample on " + sample["channel"] + " ("+str(metric)+" < " +str(window)+ ")")
            return True

        return False

    def evaluate_extraction_rules(self, sample):
        results = sample["detections"]
        channel = sample["channel"]
        channel = channel.replace(":","-")

        if channel in self.extraction_rules:
            if self.extraction_rules[channel].get("classes"):
                for cl in self.extraction_rules[channel]["classes"].split(","):
                    if cl in results:

                        if self.extraction_rules[channel].get("object_filter"):
                            if self.extraction__object_filter(sample) is False:
                                continue

                        if self.extraction_rules[channel].get("rate") is None:
                            self.extraction_rules[channel]["rate"] = 0

                        if self.extraction_rules[channel]["rate"] == "auto":
                            if cl == "unknown":
                                return True

                            if len(self.dynamic_distribution) > 0:
                                if random.uniform(0, 1) > self.dynamic_distribution[self.label_dic.index(cl)]:
                                    return True

                        elif random.uniform(0, 1) > 1 - float(self.extraction_rules[channel]["rate"]):
                            return True
        return False

    def run(self):
        while not self.stopFlag.wait(0.1):
            if self.socketIO is None:
                self.init_socketIO()

            # Compute the dynamic distribution in order to extract the samples
            if self.dd is True:
                self.dynamic_distribution_inc = self.dynamic_distribution_inc + 1
                if self.dynamic_distribution_inc > 1000 or self.dynamic_distribution == [] and len(self.label_dic) > 0:
                    self.dynamic_distribution_inc = 0
                    self.dynamic_distribution_update()

            # Process all extracted samples in buffer queue
            for obj in self.buffer:
                overlap      = self.queue_fifo.get(obj["channel"])["overlap"]

                # Looking for the target sample position in FIFO queue
                sample_index = -1
                samples      = self.queue_fifo.get(obj["channel"])["buffer"]
                for i, sample in enumerate(samples ):
                    if sample["time"] == obj["time"]:
                        sample_index = i
                        break

                if sample_index > -1:
                    # Audio stream reconstruction by concatenating sample
                    audio_file = []
                    a = int(self.queue_fifo.get(obj["channel"])["length"] * (1 + overlap) )

                    # If the FIFO buffer is not filled with enough sample yet, skip
                    if sample_index - a < 0 or sample_index + a >= len(samples):
                        continue

                    for i in range(-a, a + 1):
                        sample_audio = self.queue_fifo.get(obj["channel"])["buffer"][sample_index + i]["audio"]
                        if len(audio_file) == 0:
                            b = len(sample_audio)
                        else:
                            b = int(len(sample_audio) * (1-overlap) )
                        audio_file.append( sample_audio[:b ] )
                    audio_file = [item for sublist in audio_file for item in sublist]

                    # Store the audio file
                    sf.write (self.extraction_dest + '/unchecked/' + \
                                                str(sample["detections"]) + \
                                                '(' + str(obj["channel"].replace("_","-")) + ')_' + \
                                                obj["time"] +'.wav', \
                                                audio_file,
                                                self.queue_fifo.get(obj["channel"])["samplerate"])

                    self.queue_fifo.get(obj["channel"])["count"] += 1
                    App.log(2, "Extract sample " + obj["time"] + " on " + obj["channel"])

                try:
                    self.buffer.remove(obj)
                except:
                    App.warning(0, "Unable to remove extracted sample from queue.")
            if len(self.buffer) > 50:
                App.warning(0, "Buffer queue is " + str(len(self.buffer)))

    def execute(self, results, label_dic):

        if len(self.label_dic) == 0:
            self.label_dic = label_dic

        # Store the audio samples in ordered FIFO dictionnary
        for channel in results:
            if channel["mapping"][0]:
                ch = channel["mapping"][0].replace(":","-")
                if self.queue_fifo.get( ch ) is None:
                    self.queue_fifo[ ch ] = {
                            "buffer":[],
                            "recording_pos":0,
                            "count":0,
                            "samplerate":channel["samplerate"],
                            "overlap":0.25,
                            "channel":ch
                            }

                self.queue_fifo[ ch ]["buffer"].append({
                                    "time": channel["time"],
                                    "detections": channel["detections"],
                                    "audio": channel["audio"],
                                    "fft": channel["fft"],
                                    "channel":ch
                                    })

        for channel in self.queue_fifo:
            # Remove one element
            if len(self.queue_fifo[channel]["buffer"]) > self.queue_fifo_length:
                self.queue_fifo[channel]["buffer"].pop(0)

            # Get the sample in the middle of the list
            if len(self.queue_fifo[channel]["buffer"]) > 0:
                if self.queue_fifo[channel]["recording_pos"] > 0:
                    self.queue_fifo[channel]["recording_pos"] -= 1

                else:
                    sample = self.queue_fifo[channel]["buffer"][int(len(self.queue_fifo[channel]["buffer"])/2)]
                    try:
                        if self.evaluate_extraction_rules(sample) is True:
                            if self.extraction_rules[channel].get("length"):
                                length = self.extraction_rules[channel].get("length")
                            else:
                                length = 0.5
                            self.queue_fifo[channel]["recording_pos"]   = math.ceil( (float(length) + 1 )*(2-float(self.queue_fifo[channel]["overlap"]) ) )
                            self.queue_fifo[channel]["length"]          = float(length)
                            self.buffer.append( { "channel": channel, "time":sample["time"] } )
                    except:
                        App.error(0, "Extraction rule error ("+str(self.extraction_rules[channel])+")")
                        traceback.print_exc()
