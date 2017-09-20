import socketio
from aiohttp import web
import aiohttp_cors
import asyncio
from time import sleep

import input_jack as input_jack
from App import App

import numpy as np
mgr = socketio.AsyncRedisManager('redis://')
sio = socketio.AsyncServer(
            client_manager=mgr,
            ping_timeout=120,
            ping_interval=10,
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

        self.external_sio   = None
        self.label_dic      = None
        self.sources        = []

    def start(self, port=80):
        web.run_app(app, port=port)

    def on_connect(self, sid, environ):
        App.log(1,"Client connection " + str(sid) )

    def on_disconnect(self, sid):
        App.log(1, "Client disconnection " + str(sid) )

    def create_socketClient(self):
        self.external_sio = socketio.AsyncRedisManager('redis://', write_only=True)

    def build_label_dic(self):
        classes = []
        for cl in  self.label_dic:
            classes.append(cl)
        obj =  {'sys':{'classifier':{'list':classes}}}
        return obj

    # This function is called from another Thread
    def execute(self, results, label_dic):
        if self.external_sio is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.create_socketClient()
            App.log(1,"Redis client socket started")
            App.ok(0, "System ready.")

        if self.label_dic is None:
            self.label_dic = label_dic
            self.loop.run_until_complete(self.external_sio.emit('sys', self.build_label_dic() ) )
            sleep(0.1)

        resp_common = []        # Streams from public access
        resp_livestream = []    # Streams from livestreams
        for channel in results:
            outputs = {}
            for cl in range(0, len(label_dic)):
                outputs[label_dic[cl]] = float(channel["outputs"][cl])

            obj = {
                     "chan":channel["mapping"][0],
                     "analysis":{
                         "time":channel["time"],
                         "result":channel["detections"],
                         "predicitions":outputs
                     }
                 }
            if "tidzam-livestreams" in channel["mapping"][0]:
                resp_livestream.append(obj)
            else:
                resp_common.append(obj)

        # Send results to all clients
        self.loop.run_until_complete(self.external_sio.emit('sys', resp_common) )

        # Send the result of each independent livestream
        for resp in resp_livestream:
            self.loop.run_until_complete(self.external_sio.emit(resp["chan"].replace(":","-"), resp) )
        #sleep(0.1)

    # TODO: SocketIO-client does nt support rooms for now, so broadcast to everybody ...
    async def on_SampleExtractionRules(self, sid, data):
            await sio.emit('SampleExtractionRules', data)

    # TODO: SocketIO-client does nt support rooms for now, so broadcast to everybody ...
    # Sources list received from the TidzamStreamManeger
    async def on_JackSource(self, sid, data):
            await sio.emit('JackSource', data)

    async def on_sys(self, sid, obj):
        try:
            if isinstance(obj, dict) is False:
                await sio.emit("sys",
                    {"error":"request must be a JSON.", "request-origin":obj},
                    room=sid)
                return

            # Classifier list requested by the clients
            if obj["sys"].get("classifier"):
                await sio.emit('sys',
                    self.build_label_dic(),
                    room=sid)

        except:
            App.warning(0,"Unable to process request " + str(obj))


cors.add(app.router.add_static('/static', 'static'), {
        "*":aiohttp_cors.ResourceOptions(allow_credentials=True)
    })
def index(request):
     with open('static/index.html') as f:
         return web.Response(text=f.read(), content_type='text/html')
app.router.add_get('/', index)
