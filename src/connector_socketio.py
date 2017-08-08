import socketio
from aiohttp import web
import aiohttp_cors
import json
import asyncio
from time import sleep

import input_jack as input_jack

mgr = socketio.AsyncRedisManager('redis://')
sio = socketio.AsyncServer(
            client_manager=mgr,
            ping_timeout=7,
            ping_interval=3,
            cors_credentials='tidmarsh.media.mit.edu')
app = web.Application()

cors = aiohttp_cors.setup(app, defaults={
        "tidmarsh.media.mit.edu": aiohttp_cors.ResourceOptions(),
    })
sio.attach(app)

def create_socket(namespace):
    socket = TidzamSocketIO(namespace)
    sio.register_namespace(socket)
    return socket


class TidzamSocketIO(socketio.AsyncNamespace):

    def __init__(self,namespace):
        socketio.AsyncNamespace.__init__(self,namespace)

        self.external_sio = None
        self.classes_dic  = None
        self.time         = None

        self.sources      = []

    def start(self, port=80):
        web.run_app(app, port=port)

    def on_connect(self, sid, environ):
        print("** Socket IO ** connect ", sid)

    def on_disconnect(self, sid):
        print("** Socket IO ** disconnect ", sid)
        #self.livestreams.del_stream(sid)

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

    # This function is called from another Thread
    def execute(self, prob_classes, predictions, classes_dic, sound_obj=None, time=None, mapping=None):
        self.time = time

        if self.external_sio is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            print('** Socket IO **Create Redis client socket ')
            self.create_socketClient()
            print("======= TidZam RUNNING =======")

        if self.classes_dic is None:
            self.classes_dic = classes_dic
            self.loop.run_until_complete(self.external_sio.emit('sys', self.build_classes_dic() ) )
            self.loop.run_until_complete(self.external_sio.emit('sys', self.build_time() ) )
            sleep(0.1)

        resp_common = []        # Streams from public access
        resp_livestream = []    # Streams from livestreams
        for channel in range(len(prob_classes)):
            pred = {}
            for cl in range(0, len(classes_dic)):
                pred[classes_dic[cl]] = float(prob_classes[channel][cl])
            for m in mapping:
                if m[1] == "tidzam:chan"+str(channel):
                    break
            obj = {
                    "chan":m[0],
                    "analysis":{
                        "time":time,
                        "result":[predictions[channel]],
                        "predicitions":pred
                    }
                }
            if "tidzam-livestreams" in m[0]:
                resp_livestream.append(obj)
            else:
                resp_common.append(obj)

        self.loop.run_until_complete(self.external_sio.emit('sys', resp_common) )

        for resp in resp_livestream:
            self.loop.run_until_complete(self.external_sio.emit(resp["chan"].replace(":","-"), resp) )
        sleep(0.1)

    async def on_sys(self, sid, data):
        try:
            obj = json.loads(data)
        except:
            obj = data

        if obj.get('sys') is not None:
            if obj["sys"].get("starting_time"):
                input_jack.starting_time = obj["sys"].get("starting_time")

            if obj["sys"].get("classifier"):
                await sio.emit('sys',self.build_classes_dic())

            # Request the current timestamp of the stream
            if obj["sys"].get("time") == "":
                await sio.emit('sys', self.build_time())

            if obj["sys"].get("stream"):
                input_jack.stream = desired_date
                self.loop.run_until_complete(self.external_sio.emit('sys', {'sys':{'source':desired_date}} ) )

    def on_data(self, sid, data):
        print("** Socket IO ** data event : " + data)


cors.add(app.router.add_static('/static', 'static'), {
        "*":aiohttp_cors.ResourceOptions(allow_credentials=True)
    })
def index(request):
     with open('static/index.html') as f:
         return web.Response(text=f.read(), content_type='text/html')
app.router.add_get('/', index)
