import threading
import soundfile as sf
import numpy as np
import random
import os, gc
import copy
import glob
import collections
import math
import scipy.misc
import pathlib

from socketIO_client import SocketIO
from App import App
import traceback

class TidzamRecorder(threading.Thread):
    def __init__(self, extraction_dest='/tmp/tidzam/opus', extraction_rules=[]):
        threading.Thread.__init__(self)
        self.lock   = threading.Lock()

        self.socketIO = None
        self.socketio_address = App.socketIOanalyzerAdress

        self.stopFlag               = threading.Event()
        self.label_dic              = []
        self.queue_fifo_length      = 300
        self.queue_fifo             = collections.deque(maxlen=self.queue_fifo_length)

        self.standalone = False
        if extraction_rules != []:
            self.standalone = True

        self.extraction_dest            = extraction_dest
        self.extraction_rules           = extraction_rules
        self.database_info         = {}

        self.dynamic_distribution           = []
        self.dynamic_distribution_prev      = []
        self.database_info_update_counter   = 0

        self.recording_channels = {}

        if not os.path.exists(self.extraction_dest):
            os.makedirs(self.extraction_dest)

        if not os.path.exists(self.extraction_dest + '/unchecked/'):
            os.makedirs(self.extraction_dest + '/unchecked/')

        App.log(1, "Destination folder: " + extraction_dest)

        self.start()

    ###################################
    # SOCKET.IO
    ###################################
    def init_socketIO(self):
        tmp = self.socketio_address.split(":")
        self.socketIO = SocketIO(tmp[0], int(tmp[1]))
        self.socketIO.on('RecorderRules', self.process_socketIO)
        threading.Thread(target=self._run_socketIO).start()
        App.ok(0, "Connected to " + self.socketio_address +"")

    def _run_socketIO(self):
        while not self.stopFlag.wait(0.1):
            self.socketIO.wait(1)

    def process_socketIO(self, req):
        # TODO: SocketIO-client does nt support rooms for now, so broadcast to everybody (emitter field use for filtering)...
        if isinstance(req, dict) is False:
            self.socketIO.emit("sys",
                {"error":"request must be a JSON.", "request-origin":req},
                room=sid)
            return

        if req.get("add_rule"):
            App.log(0, "New extraction rules received:  " + str(req.get("add_rule")))
            rule        = req.get("add_rule")
            rule["id"]  = len(self.extraction_rules)
            self.extraction_rules.append(rule)

        if req.get("del_rule"):
            for rule in self.extraction_rules:
                if str(rule["id"]) == str(req.get("del_rule")):
                    App.log(1, "Delete rule " + str(rule["id"]) + " of " + str(rule))
                    self.extraction_rules.remove(rule)

        if req.get("get_rules") == "":
            self.socketIO.emit("RecorderRules",{"rules":self.extraction_rules, "emitter":"TidzamRecorder"})

        if req.get("get_database_info") == '':
            with self.lock:
                self.socketIO.emit("RecorderRules",{"database_info":self.database_info, "emitter":"TidzamRecorder"})

        if req.get("emitter") and req.get("emitter") != "TidzamRecorder":
            App.warning(0, "Bad request " + str(req))

    ###################################
    # RECORDER FUNCTIONS
    ###################################
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
            App.log(2, "Extract recording on " + sample["channel"] + " ("+str(metric)+" < " +str(window)+ ")")
            return True

        return False

    def must_be_recorded(self, sample):
        results = sample["detections"]
        channel = sample["mapping"][0].replace(":","-")
        dst     = 'unchecked'
        length  = 0

        if self.recording_channels[channel] != 0:
            return [0, dst]

        for rule in self.extraction_rules:
            if rule.get('dst') is not None:
                dst = rule.get('dst')

            if rule.get("count") is None:
                rule["count"] = 0

            if rule.get("length") is None:
                rule["length"] = 0.5;

            if channel not in rule.get("channels") and "*" not in rule.get("channels") :
                continue

            if rule["length"] > (len(self.queue_fifo) * ( 1 - sample["overlap"]) ) /2:
                continue

            cl = set(results).intersection(rule["classes"])
            if len(cl) == 0 and "*" not in rule.get("classes") :
                continue

            if rule.get("object_filter"):
                if self.extraction__object_filter(sample) is False:
                    continue

            if rule.get("rate") is None:
                rule["rate"] = 1

            if rule["rate"] == "auto":
                if "unknown" in rule.get("classes"):
                    length = rule["length"]

                elif len(self.dynamic_distribution) > 0:
                    if random.uniform(0, 1) > self.dynamic_distribution[self.label_dic.index(next(iter(cl)))]:
                        length = rule["length"]

            elif random.uniform(0, 1) > 1 - float(rule["rate"]):
                length = rule["length"]

            if length and self.recording_channels[channel] == 0:
                rule["count"] += 1
            return [length, dst]

        return [0, dst]


    def record_audiofile(self, channel_id, length, dst='unchecked'):
        # Audio stream reconstruction by concatenating sample
        audio_file = []
        overlap         = self.queue_fifo[0][channel_id]["overlap"]
        index           = int(len(self.queue_fifo) / 2)
        time            = self.queue_fifo[index][channel_id]["time"]
        detected_as     = self.queue_fifo[index][channel_id]["detections"]
        samplerate      = int(self.queue_fifo[index][channel_id]["samplerate"])
        channel_name    = self.queue_fifo[index][channel_id]["mapping"][0].replace(":","-")

        a               = int(length * (1 + overlap) )
        for i in range( index-a, index + a + 1):
            sample_audio = self.queue_fifo[i][channel_id]["audio"]
            if len(audio_file) == 0:
                b = len(sample_audio)
            else:
                b = int(len(sample_audio) * (1-overlap) )
            audio_file.append(sample_audio[:b])

        audio_file = [item for sublist in audio_file for item in sublist]

        self.recording_channels[channel_name] = a + 1

        # Store the audio file
        pathlib.Path(self.extraction_dest + '/'+dst+'/').mkdir(parents=True, exist_ok=True)
        path = self.extraction_dest + '/'+dst+'/' + str(detected_as) + '(' + str(channel_name) + ')_' + time +'.wav'
        sf.write (path, audio_file, samplerate)
        App.log(1,"Recording " + path + " ("+str(samplerate)+" Hz) saved.")

    ###################################
    # MAIM LOOP
    ###################################

    def run(self):
        while not self.stopFlag.wait(0.01):
            if self.socketIO is None and self.standalone is False:
                self.init_socketIO()

            if len(self.queue_fifo) == 0:
                continue

            samples = self.queue_fifo[int(len(self.queue_fifo) / 2)]
            for channel_id, sample in enumerate(samples):
                channel = sample["mapping"][0].replace(":","-")
                if self.recording_channels[channel] is None:
                    self.recording_channels[channel] = 0

                [length, dst] = self.must_be_recorded(sample);
                if (length):
                    self.record_audiofile(channel_id, length, dst)

            if self.database_info_update_counter == 0:
                self.dynamic_distribution_update()
                self.database_info_update_counter = 6000
            else:
                self.database_info_update_counter -= 1


    def execute(self, results, label_dic):
        # Store the results in a circular buffer
        self.queue_fifo.append(results)

        if len(self.label_dic) == 0:
            self.label_dic = label_dic

        # Create / update the recording counter
        # >0 a recodring has been done on the X last samples,
        # we should wait for a next one
        for channel in results:
             channel_name = channel["mapping"][0].replace(":","-")
             if self.recording_channels.get(channel_name) is None:
                 self.recording_channels[channel_name] = 0

             elif (self.recording_channels[channel_name] > 0):
                 self.recording_channels[channel_name] -= 1
