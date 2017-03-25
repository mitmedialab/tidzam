import socketio
from aiohttp import web
import json
import asyncio
from time import sleep

app = web.Application()

mgr = socketio.AsyncRedisManager('redis://')
sio = socketio.AsyncServer(client_manager=mgr)
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

    def start(self):
        web.run_app(app)

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

    def execute(self, prob_classes, predictions, classes_dic, sound_obj=None, time=None):
        if self.external_sio is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            print('Create Redis client socket ')
            self.create_socketClient()

        if self.classes_dic is None:
            self.classes_dic = classes_dic
            self.loop.run_until_complete(self.external_sio.emit('sys', self.build_classes_dic() ) )
            sleep(0.1)

        resp = []
        for channel in range(len(prob_classes)):
            pred = {}
            for cl in range(0, len(classes_dic)):
                pred[classes_dic[cl]] = prob_classes[channel][cl]

            obj = {
                    "chan":channel,
                    "analysis":{
                        "time":time,
                        "result":[predictions[channel]],
                        "predicitions":pred
                    }
                }
            resp.append(obj)

        self.loop.run_until_complete(self.external_sio.emit('sys', resp) )

        sleep(0.1)


    async def on_sys(self, sid, data):
        print("sys event : " + data)
        obj = json.loads(data)
        if obj['sys']:
            if obj["sys"]["classifier"]:
                await sio.emit('sys',self.build_classes_dic())

    def on_data(self, sid, data):
        print("data event : " + data)

app.router.add_static('/static', 'static')
def index(request):
     with open('static/index.html') as f:
         return web.Response(text=f.read(), content_type='text/html')
app.router.add_get('/', index)
