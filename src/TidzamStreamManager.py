
from __future__ import division

import jack
import numpy as np
import os, signal
import subprocess
import threading

from aiohttp import web
import socketio
from socketIO_client import SocketIO
import aiohttp_cors

import glob
import datetime
import json
import atexit
import time

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
            print("** TidzamStreamManager ** connection " +self.id + " Jack Ring Buffer usage: " + str(self.ring_buffer.read_space*100/(self.ring_buffer.size)) + "%")

        if self.ring_buffer.write_space == 0:
            self.ring_buffer.reset()

class Source():
    def __init__(self, name, url=None, channels=None, nb_channels=2, database=None, path_database=None, format="ogg", starting_time=None,is_permanent=False):
        self.name           = name
        self.url            = url
        self.nb_channels    = nb_channels
        self.channels        = channels # By default all channels are loaded
        self.database       = database
        self.starting_time  = starting_time
        self.seek           = 0
        self.process        = None
        self.format         = format

        self.sid            = -1
        self.is_permanent   = is_permanent

        self.path_database  = path_database
        self.default_stream = url

        if self.database is None:
            self.database = self.name

        if self.url is None:
            self.url = self.path_database

class TidzamStreamManager(threading.Thread):
    def __init__(self, available_ports=10, samplerate=44100, buffer_jack_size=50, debug=0, streamer_max=100):
        threading.Thread.__init__(self)

        self.available_ports    = available_ports
        self.available_ports    = available_ports
        self.samplerate         = samplerate
        self.buffer_jack_size   = buffer_jack_size
        self.debug              = debug

        self.streams            = []
        self.sources            = []
        self.streamer_process   = []
        self.streamer_max       = streamer_max
        self.FNULL              = open(os.devnull, 'w')

        self.portstoconnect      = []
        self.stopFlag               = threading.Event()

        self.sio_tidzam = socketio.AsyncRedisManager('redis://')

        atexit.register(self.exit)

        if self.debug > 0:
            print("** TidzamStreamManager **  Tidzam Jack client initialization.")

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
        self.start()

    def run(self):
        while not self.stopFlag.wait(0.1):
            # Check if all sources are loaded
            for source in self.sources:
                if source.process.poll() is not None:
                    if self.debug > 0:
                        print("** TidzamStreamManager **  the source "+source.name+" has been terminated.")
                    if source.is_permanent:
                        source.process = None
                        self.load_source(source)
                    else:
                        self.sources.remove(source)
                    time.sleep(1)

            for pro in self.streamer_process:
                if pro[0].poll() is not None:
                    if self.debug > 1:
                        print("** TidzamStreamManager **  the streamer "+pro[1]+" has been terminated.")
                    self.streamer_process.remove(pro)
                    name = pro[1].split(":")[0]
                    for source in self.sources:
                        if source.name == name and source.is_permanent and source.process is not None:
                            self.port_create_streamer(pro[1])

            # Check if there are port connections to create
            for connection in self.portstoconnect:
                try:
                    port_in = self.client.get_port_by_name(connection[0])
                    port_ou = self.client.get_port_by_name(connection[1])
                    if self.debug > 1:
                        print("** TidzamStreamManager **  port connection " + port_in.name + " -> " + port_ou.name)
                    self.client.connect(port_in, port_ou)
                except:
                    if self.debug > 1:
                        print("** TidzamStreamManager **  The streamer is not ready")
                self.portstoconnect.remove(connection)

    def exit(self):
        for source in self.sources:
            if source.process is not None:
                subprocess.Popen.kill(source.process)

        for pro in self.streamer_process:
            os.killpg(os.getpgid(pro[0].pid), signal.SIGKILL)
        self.streamer_process = []

    ############
    # Live Stream Interface for capturing Web microphones
    ############
    def add_stream(self, id):
        if self.debug > 0:
            print("** TidzamStreamManager ** new live stream " + str(id))

        if len(self.streams) < self.available_ports:
            self.streams.append(Stream(id, self.samplerate, self.buffer_jack_size, self.debug))
        else:
            print("** TidzamStreamManager ** unable to allocate a new live stream (already full).")


    def del_stream(self, id):
        found = False
        for s in self.streams:
            if s.id == id:
                if self.debug > 0:
                    print("** TidzamStreamManager ** delete live stream " + str(id))
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

    def wait_jack_client(self,name):
        found = True
        while found:
            found = False
            for connection in self.portstoconnect:
                if name in connection:
                    found = True
            if found:
                time.sleep(0.2)

    def unload_source(self, name):
        self.wait_jack_client(name)
        found = False
        for source in self.sources:
            if name == source.name:
                found = True
                break

        if found:
            if self.debug > 0:
                print("** TidzamStreamManager ** remove source stream " + str(source.name))
            if source.process is not None:
                subprocess.Popen.kill(source.process)
            self.sources.remove(source)
            return source
        return None

    def load_source(self, source):
        self.wait_jack_client(source.name)

        # If request an additionnal stream from a permanent stream
        source_old = None
        if source.name is not source.database:
            for s in self.sources:
                if s.database == source.database:
                    source.path_database  = s.path_database
                    source.nb_channels    = s.nb_channels
                    source.default_stream = s.default_stream
                    break
        # Else we stop the current stream to reload it with new parameters
        else:
            source_old = self.unload_source(source.name)
            if source_old is not None:
                source.path_database  = source_old.path_database
                source.default_stream = source_old.default_stream
                source.nb_channels    = source_old.nb_channels
                source.is_permanent   = source_old.is_permanent

        # If there is a starting time, look up in the database
        if source.starting_time:
            source = self.load_source_local_database(source)

        if source.url is None:
            source.url = source.default_stream

        if source.name == None:
            source.name = str(round(time.time()))


        logfile = open(os.devnull, 'w')
        if source.format == "ogg":
            cmd      = ['mpv', "-ao", "jack:name=" + source.name + ":no-connect", "--start="+str(source.seek), source.url]
        elif source.format == "copy":
            cmd = ['ffmpeg', "-re", "-i", source.url, "-codec","copy","-legacy_icecast","1","-content_type","audio/ogg","-ice_name",source.name,"-f","ogg","icecast://source:tidzam17@localhost:8000/"+source.name+".ogg"]

        source.process = subprocess.Popen(cmd,
                    shell=False,
                    stdout=logfile,
                    stderr=logfile,
                    preexec_fn=os.setsid)

        self.sources.append(source)

        if self.debug > 0:
            print("** Socket IO ** New source is loading: " + source.name + " ("+str(source.url)+") at " + str(source.seek))
        return source

    def load_source_local_database(self, source):
        datetime_asked  = datetime.datetime.strptime(source.starting_time, '%Y-%m-%d-%H-%M-%S')

        # Boudary: if the date is in future, load onlime stream
        if datetime_asked.date() > datetime.datetime.today().date():
            source.url              = source.default_stream
            source.starting_time    = None
            source.seek             = 0
            if self.debug > 0:
                print('** Socket IO ** Real Time stream: ' + str(source.url))

        # Looking for the file and compute seek position
        else:
            desired_date = source.path_database + "/"+source.database+"-" + source.starting_time
            files = sorted(glob.glob(source.path_database + "/*.opus")+glob.glob(source.path_database + "/*.ogg"))
            stream_url = None
            for f in files:
                if "opus" in f:
                    ext = ".opus"
                elif "ogg" in f:
                    ext = ".ogg"
                if f > desired_date + ext:
                    break
                stream_url = f

            if stream_url is not None:
                datetime_file = datetime.datetime.strptime(stream_url, source.path_database + '/'+source.database+'-%Y-%m-%d-%H-%M-%S' + ext)
                source.url           = stream_url
                source.seek          = (datetime_asked-datetime_file).total_seconds()

            # Boudary: if the date is too old, load first file
            else :
                source.url              = files[0]
                source.starting_time    = datetime.datetime.strptime(files[0], source.path_database + '/'+source.database+'-%Y-%m-%d-%H-%M-%S'+ext).strftime('%Y-%m-%d-%H-%M-%S')
                source.seek             = 0

        return source

    ############
    # JACK Callbacks
    ############
    def callback_client_registration(self, name, registered):
        if self.debug > 1:
            print("** TidzamStreamManager ** new client connector detected " + name + "(" + str(registered) + ")")

    def port_create_streamer(self, portname):
        cmd = ["./icecast/icecast_stream.sh", portname.replace(":","-")]
        if len(self.streamer_process) >= self.streamer_max:
            print("** TidzamStreamManager ** maximum number of streamer already allocated ("+str(len(self.streamer_process))+")")
            return
        self.streamer_process.append([subprocess.Popen(cmd,
                shell=False,
                stdout=self.FNULL,
                stderr=self.FNULL, #subprocess.PIPE,
                preexec_fn=os.setsid), portname
                ])

    def port_connect_streamer(self, port):
        name_ori = port.name.split(":")[0]
        if name_ori != "analyzer":
            name_ori = name_ori.split("-")
            port_connection = name_ori[len(name_ori)-1]
            port_name       = name_ori[0]
            for i in range(1, len(name_ori)-1):
                port_name += "-" + name_ori[i]

            try: # Try to connect to the output port
                port_in = self.client.get_port_by_name(port_name + ":" + port_connection)
                port_test = self.client.get_port_by_name(port.name)
                self.portstoconnect.append([port_in.name, port.name])

            except jack.JackError: # The input port don t exist anymore
                self.port_remove_streamer(port.name)

    def get_source(self,name):
        for source in self.sources:
            if source.name == name:
                return source
        return None

    def callback_port_registration(self, port, registered):
        if self.debug > 1:
            print("** TidzamStreamManager ** port registration status " + port.name + "(" + str(registered) + ")")

        if registered is True:
            # If there is a new stream producer (create a streamer)
            if port.is_output:
                tmp = port.name.split(":") # source name
                source = self.get_source(tmp[0])
                if source:
                    tmp    = tmp[1].split("_")[1] # channel id
                    if source.channels != None and tmp not in source.channels:
                        return

                self.port_create_streamer(port.name)
            # If the streamer has been created, we ask its connection to its stream producer
            else:
                self.port_connect_streamer(port)
        else:
            # If the link has been destroyed, we remove the streamer
            self.port_remove_streamer(port.name)

    def port_remove_streamer(self,portname):
        for pro in self.streamer_process:
            if pro[1] == portname:
                os.killpg(os.getpgid(pro[0].pid), signal.SIGKILL)
                self.streamer_process.remove(pro)

    def callback_port_connection(self,port_in, port_out, state):
        if state is True:
            if self.debug > 1:
                print("** TidzamStreamManager ** This link is created: " + port_in.name + " -> " + port_out.name + " " + str(state))
        else:
            if self.debug > 1:
                print("** TidzamStreamManager ** This link has been destroyed: " + port_in.name + " -> " + port_out.name + " " + str(state))
            if "analyzer" not in port_out.name:
                self.port_connect_streamer(port_out)

    def callback_quit(self,status, reason):
        if self.debug > 0:
            print("** TidzamStreamManager ** process in zombi mode... Restart !\n" + str(status) )

    def callback_samplerate(self, samplerate):
        if self.debug > 0:
            print("** TidzamStreamManager ** Sample rate at " + str(samplerate))

    def callback_blocksize(self, blocksize):
        if self.debug > 0:
            print("** TidzamStreamManager ** blocksize " + str(blocksize))
        self.blocksize = blocksize

    def callback_rt(self,frame):
        ports = self.client.outports
        for id, s in enumerate(self.streams):
            try:
                s.portname = ports[id].name
                bufr = np.frombuffer(s.ring_buffer.read(self.blocksize*4), dtype='float32')
                ports[id].get_array()[:] = bufr

            except Exception as e:
                if self.debug > 1:
                    print("** TidzamStreamManager ** Error loading RT ring buffer " + s.id + "("+str(e)+")")
                ports[id].get_array()[:].fill(0)
                if len(bufr) == 0:
                    self.del_stream(s.id)

    ############
    # Socket.IO controller
    ############
if __name__ == '__main__':

    usage = 'TidzamStreamManager.py [options]'
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

    parser.add_option("--sources", action="store", type="string", dest="sources",
        default="",
        help="JSON file containing the list of the initial audio source streams (default: None).")

    parser.add_option("--debug", action="store", type="int", dest="DEBUG", default=0,
        help="Set debug level (Default: 0).")

    (opts, args) = parser.parse_args()
    sio = socketio.AsyncServer(
            ping_timeout=21,
            ping_interval=10)
    app = web.Application()
    sio.attach(app)

    jack_service = TidzamStreamManager(
                available_ports=opts.live_port,
                samplerate=opts.samplerate,
                buffer_jack_size=opts.buffer_size,
                debug=opts.DEBUG)

    # Load initial configuration
    try:
        with open(opts.sources) as data_file:
            jfile = json.load(data_file)
            if jfile.get("sources"):
                for stream in jfile["sources"]:
                    path_database = None
                    if stream.get("path_database"):
                        path_database = stream.get("path_database")
                    jack_service.load_source( Source(
                        name=stream["name"],
                        url=stream["url"],
                        nb_channels=stream["nb_channels"],
                        path_database=path_database,
                        is_permanent=True ))

            if jfile.get("database"):
                jack_service.path_database = jfile["database"]

            if jfile.get("default_stream"):
                jack_service.default_stream = jfile["default_stream"]
    except:
        print("** TidzamStreamManager ** no valid source file.")


    tidzam_address = opts.tidzam_address.split(":")
    sio_tidzam = SocketIO(tidzam_address[0], tidzam_address[1])

    @sio.on('connect', namespace='/')
    def connect(sid, environ):
        if opts.DEBUG > 0:
            print("** TidzamStreamManager ** client connected ", sid)

    @sio.on('audio', namespace='/')
    async def audio(sid, data):
        jack_service.add_data(sid, data)

    @sio.on('disconnect', namespace='/')
    def disconnect(sid):
        if opts.DEBUG > 0:
            print("** TidzamStreamManager ** client disconnected ", sid)
        jack_service.del_stream(sid)

        # Delete the stream that has been created by this web user
        found = True
        while found:
            found = False
            for stream in jack_service.sources:
                if stream.sid == sid and stream.is_permanent is False:
                    found = True
                    break
            if found:
                jack_service.unload_source(stream.name)

    @sio.on('sys', namespace='/')
    async def sys(sid, data):
        try:
            obj = json.loads(data)

            # A source is connected to the tidzam analyzer
            if obj["sys"].get("loadsource"):
                if obj["sys"]["loadsource"].get("date"):
                    date = obj["sys"]["loadsource"]["date"];
                else:
                    date = None

                if obj["sys"]["loadsource"].get("url"):
                    url = obj["sys"]["loadsource"]["url"];
                else:
                    url = None

                if obj["sys"]["loadsource"].get("database"):
                    database = obj["sys"]["loadsource"]["database"]
                else:
                    database = None

                if obj["sys"]["loadsource"].get("channels") is not None:
                    channels = obj["sys"]["loadsource"]["channels"].split(",")
                else:
                    channels = None

                if obj["sys"]["loadsource"].get("is_permanent") is not None:
                    is_permanent = int(obj["sys"]["loadsource"]["is_permanent"])
                else:
                    is_permanent = False

                if obj["sys"]["loadsource"].get("format") is not None:
                    format = obj["sys"]["loadsource"]["format"]
                else:
                    format = "ogg"
                if format != "ogg" and format != "copy":
                    format = "ogg"

                source = jack_service.load_source(Source(
                        name=obj["sys"]["loadsource"]["name"],
                        url=url,
                        channels=channels,
                        database=database,
                        is_permanent=is_permanent,
                        format=format,
                        starting_time=date ))
                source.sid = sid

                # Send the new stream configuration to tidzam analyzer process and clients TODO
                rsp = []
                for source in jack_service.sources:
                    rsp.append({"name":source.name,"starting_time":source.starting_time})
                sio_tidzam.emit('sys', {"sys":{"sources":rsp}} )

            elif obj["sys"].get("unloadsource"):
                jack_service.unload_source(obj["sys"]["unloadsource"]["name"])

            # A live stream is a socket io interface connected to the tidzam analyzer
            elif obj["sys"].get("add_livestream"):
                for s in jack_service.streams:
                    if s.id == sid:
                        await sio.emit('sys',
                                data={'portname': s.portname},
                                room=sid)

            elif obj["sys"].get("del_livestream"):
                jack_service.del_stream(sid)

            # Request the list of available recordings in database TODO : Ugly
            elif obj["sys"].get("database") == "":
                rsp = {}
                for source in jack_service.sources:
                    if source.is_permanent:
                        rsp[source.name] = {}
                        rsp[source.name]["nb_channels"] = source.nb_channels
                        rsp[source.name]["database"] = []
                        if source.path_database:
                            files = sorted(glob.glob(source.path_database + "/*.opus")+glob.glob(source.path_database + "/*.ogg"))
                            for fo in files:
                                f = fo.split("/")
                                f = f[len(f)-1].replace(".opus", "").replace(".ogg", "").replace(source.database+"-","")
                                f = f.split("-")
                                start = datetime.datetime(int(f[0]),int(f[1]),int(f[2]),int(f[3]),int(f[4]),int(f[5]))
                                nb_seconds = int(int(os.stat(fo).st_size)*0.000013041)
                                end = start + datetime.timedelta(seconds=nb_seconds)
                                rsp[source.name]["database"].append([
                                        start.strftime('%Y-%m-%d-%H-%M-%S'),
                                        end.strftime('%Y-%m-%d-%H-%M-%S')
                                        ])
                await sio.emit('sys', {"sys":{"database":rsp}})

            else:
                print("** TidzamStreamManager ** umknow socket.io command: " +str(data)+ " ("+str(sid)+")")
        except Exception as e:
            print("** TidzamStreamManager ** umknow socket.io command: " +str(data)+ " ("+str(sid)+") " + str(e))

    web.run_app(app, port=opts.port)
