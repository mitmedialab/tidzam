import threading

import chainclient.chainclient as chainclient

class ChainAPI(threading.Thread):
    def __init__(self,debug=0):
        threading.Thread.__init__(self)
        self.stopFlag = threading.Event()

        self.site       = None
        self.site_url   = None
        self.auth       = None
        self.debug      = debug
        self.buffer = []
        self.start()

    def connect(self, site_url, auth=None):
        self.site_url = site_url
        self.auth     = auth
        try:
            self.site = chainclient.get(self.site_url)
        except chainclient.ChainException:
            print("Unable to connect to site "+self.site_url)

    def push(self, device, sensor, time):
        devices_coll = self.site.rels['ch:devices']
        found = False

        for dev in devices_coll.rels['items']:
            if dev.name == str(device):
                found = True
                break
        # If the device doesn t exist, we create it
        if found is False:
            if self.debug > 0:
                print("** TidZam ChainAPI ** Create new device: " + str(device))
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
            if self.debug > 0:
                print("** TidZam ChainAPI ** Create new sensor: " + sensor + " on "+str(device))
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
                except chainclient.ChainException as e:
                    print("** TidZam ChainAPI ** Error "+ str(e))

                except:
                    print("** TidZam ChainAPI ** Error pushing on "+str(o[0])+" "+str(o[1]))


    def execute(self, prob_classes, predictions, classes_dic, sound_obj=None, time=None):
        for channel in range(len(prob_classes)):
            if predictions[channel] is not 'unknow':
                self.buffer.append([channel, predictions[channel], time])

#ch = ChainAPI()
#ch.connect('http://chain-api.media.mit.edu/sites/16', auth=HTTPBasicAuth('slash','toto'))
#ch.push("Yahoo", "sensor2", "2017-04-07T13:10:50.500000")
