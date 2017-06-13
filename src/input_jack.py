from __future__ import division
import jack
import sys, os, signal,time
import numpy as np
import threading
from threading import Thread
import subprocess
import data as tiddata
import atexit


class TidzamJack(Thread):
    def __init__(self, port_name, callable_objects=[], debug=0, overlap=0):
        Thread.__init__(self)
        global stream
        stream = "http"
        self.debug = debug
        self.port_name = port_name
        self.FNULL  = open(os.devnull, 'w')
        self.lock   = threading.Lock()

        self.samplerate = -1
        self.blocksize = -1
        self.buffer_size = 24000
        self.overlap = overlap
        self.buffer_jack = self.buffer_size * 20
        self.streamer_process = []
        self.stopFlag = threading.Event()

        self.callable_objects = callable_objects
        self.init_client()
        atexit.register(self.kill_process)

    def init_client(self):
        self.client = jack.Client("tidzam")

        self.client.set_samplerate_callback(self.callback_samplerate)
        self.client.set_blocksize_callback(self.callback_blocksize)
        self.client.set_process_callback(self.callback_rt)
        self.client.set_shutdown_callback(self.callback_quit)
        self.client.set_port_connect_callback(self.callback_port_connection, only_available=True)

        self.channels_state = {}


    def callback_quit(self,status, reason):
        with self.lock:
            if self.debug > 0:
                print("JACK Connector: process in zombi mode... Restart !")
            self.kill_process()
            time.sleep(1)
            self.init_client()

    def load_stream(self):
        if self.debug > 0:
            print("JACK Connector: stream initialization tentative.")

        try:
            self.client.deactivate()
            # Clean all connections and buffers
            self.channels = []
            self.ring_buffer = []
            self.channels_data = []
            self.channels_state = {}
            self.client.inports.clear()

            self.ports = self.client.get_ports(self.port_name)
            # Register TidZam inputs for each MPV ports
            for i in range(0, len(self.ports)):
                self.channels.append(self.client.inports.register("chan"+str(i)))
                self.ring_buffer.append(jack.RingBuffer(self.buffer_jack))


            # If the ports have been connected, start audio streaming
            with open("icecast/ices-templates.xml", "r") as file_template:
                for i in range(0, len(self.ports)):
                    file_template.seek(0)
                    template = file_template.read()
                    template = template.replace("/chan.ogg", "/ch"+str(i+1).zfill(2) +".ogg")
                    with open("/tmp/ices-chan"+str(i)+".xml", "w") as file:
                        file.write(template)

                    cmd = ["./icecast/icecast_stream.sh", str(i)]
                    self.streamer_process.append(subprocess.Popen(cmd,
                            shell=False,
                            stdout=self.FNULL,
                            stderr=self.FNULL,
                            preexec_fn=os.setsid))


            # Activate TidZam ports and connecto MPV
            self.client.activate()
            for i in range(0, len(self.ports)):
                if "mpv" in self.ports[i].name:
                    self.client.connect(self.ports[i], self.channels[i])
        except:
            if self.debug > 0:
                print("JACK Connector: Loading stream exception.")

    def callback_port_connection(self,port_in, port_out, state):
        self.channels_state[port_in.name] = state

    def portsAllReady(self):
        for p in self.channels_state:
            if self.channels_state[p] is False:
                #print(p)
                return False
        if len(self.channels_state) == 0:
            return False
        return True

    def portStarting(self):
        for p in self.channels_state:
            #print(str(p) + str(self.channels_state[p]))
            if self.channels_state[p] is True:
                return True
        return False

    def kill_process(self):
        for pro in self.streamer_process:
            os.killpg(os.getpgid(pro.pid), signal.SIGKILL)
        self.streamer_process = []

    def run(self):
        global stream
        run = False
        while not self.stopFlag.wait(0.1):
            with self.lock:
                if self.portsAllReady():
                    try:
                        for i in range(len(self.channels)):
                            data = self.ring_buffer[i].read(self.buffer_jack)
                            data = np.frombuffer(data, dtype='float32')
                            try:
                                self.channels_data[i] = np.concatenate((self.channels_data[i], data ))
                            except:
                                self.channels_data.append( data )

                            # If the buffer contains the required data, we truncate it and send result
                            if len(self.channels_data[i]) >= self.buffer_size:
                                if i == 0:
                                    run = True
                            else:
                                run = False

                            if run is True:
                                data = self.channels_data[i][0:self.buffer_size]
                                self.channels_data[i] = self.channels_data[i][int(self.buffer_size*(1-self.overlap) ):len(self.channels_data[i])]
                                fs, t, Sxx = tiddata.get_spectrogram(data, self.samplerate)

                                if i == 0:
                                    if int(len(self.channels_data[i])/self.buffer_size) > 10:
                                        print("-----------------------------------")
                                        print("** WARNING ** JACK Connector: buffer queue is " + str(int(len(self.channels_data[i])/self.buffer_size)) + " samples" )
                                    if int(len(self.channels_data[i])/self.buffer_size) > 50:
                                        print("-----------------------------------")
                                        print("** ERROR ** JACK Connector: buffer overflow, delay > 50 samples, clean it" )
                                        self.channels_data = []
                                        break

                                    datas   = data
                                    Sxxs    = Sxx
                                    fss     = fs
                                    ts      = t
                                else:
                                    Sxxs    = np.vstack((Sxxs, Sxx))
                                    fss     = np.vstack((fss, fs))
                                    ts      = np.vstack((ts, t))
                                    datas   = np.vstack((datas, data))

                        if run is True:
                            for obj in self.callable_objects:
                                obj.execute(Sxxs, fss, ts, [np.transpose(datas), self.samplerate],
                                            overlap=self.overlap,
                                            stream=stream)
                    except:
                        print("Sample error")

                # If there there is no port ready => nothing to wait
                elif self.portStarting() is False:
                    self.kill_process()
                    self.load_stream()
                    time.sleep(1)

                else:
                    if self.debug > 0:
                        print("JACK Connector error: waiting port registration.")
                        time.sleep(1)

    def stop(self):
        self.client.deactivate()
        self.client.close()
        self.stopFlag.set()

    def callback_samplerate(self, samplerate):
        self.samplerate = samplerate

    def callback_blocksize(self, blocksize):
        self.blocksize = blocksize

    def callback_rt(self,frame):
        try :
            for i in range(len(self.channels)):
                self.ring_buffer[i].write(self.channels[i].get_array())
        except:
            print("Error loading RT ring buffer")
