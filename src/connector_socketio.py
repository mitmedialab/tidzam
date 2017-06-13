import socketio
from aiohttp import web
import json
import asyncio
from time import sleep
import os, signal
import subprocess
import glob
import datetime
import atexit
import input_jack as input_jack

mgr = socketio.AsyncRedisManager('redis://')
sio = socketio.AsyncServer(client_manager=mgr, ping_timeout=6000000)
app = web.Application()
sio.attach(app)

def create_socket(namespace):
    socket = TidzamSocketIO(namespace)
    sio.register_namespace(socket)

    return socket


class TidzamSocketIO(socketio.AsyncNamespace):

    def __init__(self,namespace):
        socketio.AsyncNamespace.__init__(self,namespace)
        self.path_database = "/mnt/tidmarsh-audio/impoundment-mc"
        self.stream_rt = "http://doppler.media.mit.edu:8000/impoundment.opus"
        self.external_sio = None
        self.classes_dic  = None
        self.mpv          = None
        self.time         = None

        atexit.register(self.kill_process)

    def kill_process(self):
        subprocess.Popen.kill(self.mpv)

    def start(self, port=80):
        web.run_app(app, port=port)

    def on_connect(self, sid, environ):
        print("connect ", sid)

    def on_disconnect(self, sid):
        print("disconnect ", sid)

    def create_socketClient(self):
        self.external_sio = socketio.AsyncRedisManager('redis://', write_only=True)

    def build_classes_dic(self):
        classes = []
        for cl in  self.classes_dic:
            classes.append('classifier-' +  cl + '.nn')
        obj =  {'sys':{'classifier':{'list':classes}}}
        return obj

    def build_time(self):
        return {"sys": {"time": self.time}}

    def execute(self, prob_classes, predictions, classes_dic, sound_obj=None, time=None):
        self.time = time

        if self.external_sio is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            print('Create Redis client socket ')
            self.create_socketClient()
            print("======= TidZam RUNNING =======")

        if self.classes_dic is None:
            self.classes_dic = classes_dic
            self.loop.run_until_complete(self.external_sio.emit('sys', self.build_classes_dic() ) )
            self.loop.run_until_complete(self.external_sio.emit('sys', self.build_time() ) )
            sleep(0.1)

        resp = []
        for channel in range(len(prob_classes)):
            pred = {}
            for cl in range(0, len(classes_dic)):
                pred[classes_dic[cl]] = prob_classes[channel][cl]
            obj = {
                    "chan":channel+1,
                    "analysis":{
                        "time":time,
                        "result":[predictions[channel]],
                        "predicitions":pred
                    }
                }
            resp.append(obj)
        self.loop.run_until_complete(self.external_sio.emit('sys', resp) )
        sleep(0.1)

    def load_source(self, desired_date, seek=0):
        desired_date = desired_date.replace(":","-").replace("T","-")
        datetime_asked = datetime.datetime.strptime(desired_date, '%Y-%m-%d-%H-%M-%S')

        # Boudary: if the date is in future, load onlime stream
        if datetime_asked.date() > datetime.datetime.today().date():
            fpred = self.stream_rt
            seek_seconds = 0
            desired_date = fpred.replace(".opus","") + desired_date + ".opus"
            print('Real Time stream: ' + fpred)

        # Looking for the file and compute seek position
        else:
            desired_date = self.path_database + "/impoundment-" + desired_date + ".opus"
            files = sorted(glob.glob(self.path_database + "/*.opus"))
            fpred = None
            for f in files:
                if f > desired_date:
                    break
                fpred = f

            if fpred is not None:
                datetime_file = datetime.datetime.strptime(fpred, self.path_database + '/impoundment-%Y-%m-%d-%H-%M-%S.opus')
                seek_seconds = (datetime_asked-datetime_file).total_seconds()

            # Boudary: if the date is too old, load first file
            else :
                fpred  = files[0]
                desired_date = files[0]
                seek_seconds = 0

            print('From database: ' + fpred + ' at ' + str(seek_seconds) + ' seconds')

        cmd = ['mpv', "-ao", "jack:no-connect",
                "--audio-channels=30",
                "--start="+str(seek_seconds),
                fpred]
        if self.mpv is not None:
            subprocess.Popen.kill(self.mpv)
        subprocess.call(["pkill", "mpv"]) # Kill other mpv process, just in case)
        sleep(1)

        logfile = open(os.devnull, 'w')
        self.mpv = subprocess.Popen(cmd,
                shell=False,
                stdout=logfile,
                stderr=logfile,
                preexec_fn=os.setsid)

        input_jack.stream = desired_date
        if self.external_sio:
            self.loop.run_until_complete(self.external_sio.emit('sys', {'sys':{'source':desired_date}} ) )

    async def on_sys(self, sid, data):
        #print("sys event : " + data)
        obj = json.loads(data)
        if obj.get('sys'):
            if obj["sys"].get("classifier"):
                await sio.emit('sys',self.build_classes_dic())

            if obj["sys"].get("source"):
                self.load_source(obj["sys"]["source"])

            if obj["sys"].get("time") == "":
                await sio.emit('sys', self.build_time())

            if obj["sys"].get("database") == "":
                files = sorted(glob.glob(self.path_database + "/*.opus"))
                rsp = []
                for fo in files:
                    f = fo.split("/")
                    f = f[len(f)-1].replace(".opus", "").replace("impoundment-","")
                    f = f.split("-")
                    start = datetime.datetime(int(f[0]),int(f[1]),int(f[2]),int(f[3]),int(f[4]),int(f[5]))
                    nb_seconds = int(int(os.stat(fo).st_size)*0.000013041)
                    end = start + datetime.timedelta(seconds=nb_seconds)
                    rsp.append([
                            start.strftime('%Y-%m-%d-%H-%M-%S'),
                            end.strftime('%Y-%m-%d-%H-%M-%S')
                            ])
                await sio.emit('sys', {"sys":{"database":rsp}})

    def on_data(self, sid, data):
        print("data event : " + data)

app.router.add_static('/static', 'static')
def index(request):
     with open('static/index.html') as f:
         return web.Response(text=f.read(), content_type='text/html')
app.router.add_get('/', index)
