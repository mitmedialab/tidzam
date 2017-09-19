import threading

import chainclient as chainclient
from App import App

class ChainAPI(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stopFlag = threading.Event()

        self.site       = None
        self.site_url   = None
        self.auth       = None
        self.buffer = []
        self.start()

    def connect(self, site_url, auth=None):
        self.site_url = site_url
        self.auth     = auth
        try:
            self.site = chainclient.get(self.site_url)
            App.ok(0, "Connected to " + self.site_url)
        except chainclient.ChainException:
            App.error(0,"Unable to connect to site "+self.site_url)

    def push(self, device, sensor, time):
        devices_coll = self.site.rels['ch:devices']
        found = False

        for dev in devices_coll.rels['items']:
            if dev.name == str(device):
                found = True
                break
        # If the device doesn t exist, we create it
        if found is False:
            App.log(1,"Create new device: " + str(device))
            dev = devices_coll.create(
                {'name': device},
                auth=self.auth)

        found = False
        for sens_r in dev.rels['ch:sensors'].rels['items']:
            if sens_r.metric == sensor:
                found = True
                break
        # If the sensor doesn't exist, we create it
        if found is False:
            App.log(1, "Create new sensor: " + sensor + " on "+str(device))
            sens_r = dev.rels['ch:sensors'].create(
                {"sensor-type": "scalar", "metric": sensor, "unit": "boolean"},
                auth=self.auth)

        sens_r.rels['ch:dataHistory'].create(
                {"value": 1, "timestamp":time.replace("T"," ")},
                auth=self.auth)

    def run(self):
        while not self.stopFlag.wait(0.1):
            for o in self.buffer:
                try:
                    self.push(o[0], o[1], o[2])
                    self.buffer.remove(o)
                except chainclient.ChainException as e:
                    App.error(0, str(e))

                except:
                    App.error(0, "Error pushing on "+str(o[0])+" "+str(o[1]))
            if len(self.buffer) > 50:
                App.warning(0,"Queue size "+str(len(self.buffer)))

    def execute(self, results, label_dic):
        for channel in results:
            for detection in channel["detections"]:
                if 'unknown' not in detection and 'no_signal' not in detection:
                    self.buffer.append([channel["mapping"][0].replace("tidzam-",""), detection, channel["time"]])
