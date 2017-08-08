
from __future__ import division

import jack
import numpy as np
import os, signal
import subprocess

from aiohttp import web
import socketio
from socketIO_client import SocketIO
import aiohttp_cors

import glob
import datetime
import json
import atexit

import optparse
class Stream():
    def __init__(self, id, samplerate=44100, buffer_jack_size=3, debug=1):
        self.samplerate         = samplerate
        self.buffer_jack_size   = buffer_jack_size
        self.ring_buffer        = jack.RingBuffer(samplerate*buffer_jack_size)
        self.id                 = id
        self.portname           = None
        self.debug              = debug

    def add_data(self,data):
        data = np.frombuffer(data, dtype='int16')
        data = data.astype("float32")
        data = data / 32768
        data = data.tobytes()
        self.ring_buffer.write(data)
        if self.debug > 2:
            print("** SocketioJackConnector ** connection " +self.id + " Jack Ring Buffer usage: " + str(self.ring_buffer.read_space*100/(self.ring_buffer.size)) + "%")

        if self.ring_buffer.write_space == 0:
            self.ring_buffer.reset()

class SocketioJackConnector():
    def __init__(self, available_ports=10, samplerate=44100, buffer_jack_size=50, debug=0):
        self.available_ports    = available_ports
        self.available_ports    = available_ports
        self.samplerate         = samplerate
        self.buffer_jack_size   = buffer_jack_size
        self.debug              = debug

        self.streams            = []
        self.sources            = []

        self.sio_tidzam = socketio.AsyncRedisManager('redis://')

        self.starting_time = -1
        self.path_database = "/mnt/tidmarsh-audio/impoundment-mc"
        self.stream_rt = "http://doppler.media.mit.edu:8000/impoundment.opus"

        atexit.register(self.exit)

        if self.debug > 0:
            print("** SocketioJackConnector **  Tidzam Jack client initialization.")

        self.client = jack.Client("tidzam-livestreams")
        self.client.set_samplerate_callback(self.callback_samplerate)
        self.client.set_blocksize_callback(self.callback_blocksize)
        self.client.set_process_callback(self.callback_rt)
        self.client.set_shutdown_callback(self.callback_quit)
        self.client.set_client_registration_callback(self.callback_client_registration)
        self.client.set_port_registration_callback(self.callback_port_registration, only_available=True)
        self.client.set_port_connect_callback(self.callback_port_connection, only_available=True)

        for i in range(0,self.available_ports):
            self.client.outports.register('out_{0}'.format(i))
        self.client.activate()

    def exit(self):
        for source in self.sources:
            subprocess.Popen.kill(source[2])

    ############
    # Live Stream Interface for capturing Web microphone
    ############
    def add_stream(self, id):
        if self.debug > 1:
            print("** SocketioJackConnector ** new live stream " + str(id))

        if len(self.streams) < self.available_ports:
            self.streams.append(Stream(id, self.samplerate, self.buffer_jack_size, self.debug))
        else:
            print("** SocketioJackConnector ** unable to allocate a new live stream (already full).")


    def del_stream(self, id):
        found = False
        for s in self.streams:
            if s.id == id:
                if self.debug > 1:
                    print("** SocketioJackConnector ** delete live stream " + str(id))
                self.streams.remove(s)

    def add_data(self, id, data):
        found = False
        for s in self.streams:
            if s.id == id:
                found = True
                s.add_data(data)
        if found is False:
            self.add_stream(id)
            self.add_data(id, data)

    ############
    # Source Interface for capturing HTTP / local audio streams
    ############
    def get_sources_url(self):
        res = []
        for s in self.sources:
            res.append(s[1])
        return res

    def load_source(self, name, url, permanent=False):
        seek_seconds = 0
        stream_name  = url
        self.starting_time = -1
        self.unload_source(name)

        if "database_" in url:
            [url, seek_seconds, stream_name] = self.load_source_local_database(name, url.split("_")[1])

        cmd = ['mpv', "-ao", "jack:name=" + name + ":no-connect", "--start="+str(seek_seconds), url]
        logfile = open(os.devnull, 'w')
        self.sources.append([name, stream_name, subprocess.Popen(cmd,
                shell=False,
                stdout=logfile,
                stderr=logfile,
                preexec_fn=os.setsid)])
        print("** Socket IO ** New source is loading: " + name + " ("+stream_name+")")
        return stream_name

    def unload_source(self,name):
        found = False
        for source in self.sources:
            if name == source[0]:
                found = True
                break

        if found:
            subprocess.Popen.kill(source[2])
            #print("** Socket IO ** Source remove: " + source[0] + " ("+source[1]+")")
            self.sources.remove(source)
            return 0

        return -1

    def load_source_local_database(self, name, desired_date, seek=0):
        self.starting_time = desired_date
        desired_date    = desired_date.replace(":","-").replace("T","-")
        datetime_asked  = datetime.datetime.strptime(desired_date, '%Y-%m-%d-%H-%M-%S')

        # Boudary: if the date is in future, load onlime stream
        if datetime_asked.date() > datetime.datetime.today().date():
            fpred = self.stream_rt
            seek_seconds = 0
            desired_date = fpred.replace(".opus","") + desired_date + ".opus"
            self.starting_time = -1
            print('** Socket IO ** Real Time stream: ' + fpred)

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

            print('** Socket IO ** Load source from database: ' + fpred + ' at ' + str(seek_seconds) + ' seconds')

        return fpred, seek_seconds, desired_date

#        input_jack.stream = desired_date
#        if self.external_sio:
#            self.loop.run_until_complete(self.external_sio.emit('sys', {'sys':{'source':desired_date}} ) )


    ############
    # JACK Callbacks
    ############
    def callback_client_registration(self, name, registered):
        if self.debug > 0:
            print("** SocketioJackConnector ** new client connector detected " + name + "(" + str(registered) + ")")

    def callback_port_registration(self, port, registered):
        if self.debug > 1:
            print("** SocketioJackConnector ** new port registration " + port.name + "(" + str(registered) + ")")

    def callback_port_connection(self,port_in, port_out, state):
        if self.debug > 1:
            print("** SocketioJackConnector ** This link is created: " + port_in.name + " -> " + port_out.name + " " + str(state))

    def callback_quit(self,status, reason):
        if self.debug > 0:
            print("** SocketioJackConnector ** process in zombi mode... Restart !\n" + str(status) )

    def callback_samplerate(self, samplerate):
        if self.debug > 0:
            print("** SocketioJackConnector ** Sample rate at " + str(samplerate))

    def callback_blocksize(self, blocksize):
        if self.debug > 0:
            print("** SocketioJackConnector ** blocksize " + str(blocksize))
        self.blocksize = blocksize

    def callback_rt(self,frame):
        # print("frame: " + str(frame)) = 1024

        ports = self.client.outports
        for id, s in enumerate(self.streams):
            try:
                s.portname = ports[id].name
                bufr = np.frombuffer(s.ring_buffer.read(self.blocksize*4), dtype='float32')
                ports[id].get_array()[:] = bufr

            except Exception as e:
                if self.debug > 1:
                    print("** SocketioJackConnector ** Error loading RT ring buffer " + s.id + "("+str(e)+")")
                ports[id].get_array()[:].fill(0)
                self.del_stream(s.id)

    ############
    # Socket.IO controller
    ############
if __name__ == '__main__':

    usage = 'SocketioJackConnector.py [options]'
    parser = optparse.OptionParser(usage=usage)

    parser.add_option("--buffer-size", action="store", type="int", dest="buffer_size", default=3,
        help="Set the Jack ring buffer size in seconds (default: 100 seconds).")

    parser.add_option("--samplerate", action="store", type="int", dest="samplerate", default=44100,
        help="Set the sample rate (default: 44100).")

    parser.add_option("--port-available", action="store", type="int", dest="live_port", default=2,
        help="Number of available ports for live connections (default: 10).")

    parser.add_option("--port", action="store", type="int", dest="port", default=1234,
        help="Socket.IO Web port (default: 8080).")

    parser.add_option("--tidzam-socketio", action="store", type="string", dest="tidzam_address", default="localhost:8001",
        help="Socket.IO address of the tidzam server (default: localhost:8001).")

    parser.add_option("--database", action="store", type="string", dest="path_database",
        default="/mnt/tidmarsh-audio/impoundment-mc",
        help="Folder path to local opus database (default: /mnt/tidmarsh-audio/impoundment-mc).")

    parser.add_option("--sources", action="store", type="string", dest="sources",
        default="",
        help="JSON file containing the list of the initial audio source streams (default: None).")

    parser.add_option("--debug", action="store", type="int", dest="DEBUG", default=0,
        help="Set debug level (Default: 0).")

    (opts, args) = parser.parse_args()
    sio = socketio.AsyncServer(
            ping_timeout=7,
            ping_interval=3)
    app = web.Application()
    sio.attach(app)

    jack_service = SocketioJackConnector(
                available_ports=opts.live_port,
                samplerate=opts.samplerate,
                buffer_jack_size=opts.buffer_size,
                debug=opts.DEBUG)

    tidzam_address = opts.tidzam_address.split(":")
    sio_tidzam = SocketIO(tidzam_address[0], tidzam_address[1])

    # Load initial sources
    try:
        with open(opts.sources) as data_file:
            jfile = json.load(data_file)
            print(str(jfile) )
            for stream in jfile:
                jack_service.load_source(stream["name"], stream["url"])
    except:
        print("** SocketioJackConnector ** no valid source file.")

    @sio.on('connect', namespace='/')
    def connect(sid, environ):
        if opts.DEBUG > 0:
            print("** SocketioJackConnector ** client connected ", sid)

    @sio.on('audio', namespace='/')
    async def audio(sid, data):
        jack_service.add_data(sid, data)

    @sio.on('disconnect', namespace='/')
    def disconnect(sid):
        if opts.DEBUG > 0:
            print("** SocketioJackConnector ** client disconnected ", sid)
        jack_service.del_stream(sid)

    @sio.on('sys', namespace='/')
    async def sys(sid, data):
        try:
            obj = json.loads(data)

            if obj["sys"].get("loadsource"):
                jack_service.load_source(
                            obj["sys"]["loadsource"]["name"],
                            obj["sys"]["loadsource"]["url"],
                            obj["sys"]["loadsource"]["permanent"])

                sio_tidzam.emit('sys', {"sys":{"starting_time":jack_service.starting_time}} )

            elif obj["sys"].get("unloadsource"):
                jack_service.unload_source(obj["sys"]["unloadsource"]["name"])

            elif obj["sys"].get("addstream"):
                for s in jack_service.streams:
                    if s.id == sid:
                        await sio.emit('sys',
                                data={'portname': s.portname},
                                room=sid)

            elif obj["sys"].get("delstream"):
                jack_service.del_stream(sid)

            # Request the list of available recordings in database
            elif obj["sys"].get("database") == "":
                files = sorted(glob.glob(opts.path_database + "/*.opus"))
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

            else:
                print("** SocketioJackConnector ** umknow socket.io command: " +str(data)+ " ("+str(sid)+")")
        except Exception as e:
            print("** SocketioJackConnector ** umknow socket.io command: " +str(data)+ " ("+str(sid)+") " + str(e))

    web.run_app(app, port=opts.port)
