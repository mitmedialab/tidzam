from __future__ import division
import jack
import sys, os, signal,time
import numpy as np
import threading
from threading import Thread
import subprocess
import data as tiddata
import atexit

import re

def sorted_nicely( l ):
    """ Sort the given iterable in the way that humans expect."""
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key.name) ]
    return sorted(l, key = alphanum_key)

class TidzamJack(Thread):
    def __init__(self, port_names, callable_objects=[], debug=0, overlap=0):
        Thread.__init__(self)
        global stream
        stream = "http"
        self.debug = debug
        self.port_names = port_names
        self.FNULL  = open(os.devnull, 'w')
        self.lock   = threading.Lock()

        self.mustReload = False

        self.samplerate = -1
        self.blocksize = -1
        self.buffer_size = 24000
        self.overlap = overlap
        self.buffer_jack = self.buffer_size * 20
        self.streamer_process = []
        self.stopFlag = threading.Event()

        self.callable_objects = callable_objects
        self.init_client()
        atexit.register(self.kill_streamer)

    def init_client(self):
        if self.debug > 1:
            print("Tidzam Jack client initialization.")
        self.client = jack.Client("tidzam")
        self.client.set_samplerate_callback(self.callback_samplerate)
        self.client.set_blocksize_callback(self.callback_blocksize)
        self.client.set_process_callback(self.callback_rt)
        self.client.set_shutdown_callback(self.callback_quit)
        self.client.set_port_connect_callback(self.callback_port_connection, only_available=True)
        self.channels_state = {}

    def kill_streamer(self):
        for pro in self.streamer_process:
            os.killpg(os.getpgid(pro.pid), signal.SIGKILL)
        self.streamer_process = []

    def load_streamer(self):
        self.kill_streamer()
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
                        preexec_fn=os.setsid)
                        )

    def load_stream(self):
        try:
             # Wait that all jack ports are properly disconnected
            self.client.deactivate()
            time.sleep(5)
            self.mustReload = False

            if self.debug > 0:
                print("JACK Connector: stream initialization tentative.")

            # Clean all connections and buffers
            self.ports          = []
            self.channels       = []
            self.ring_buffer    = []
            self.channels_data  = []
            self.channels_state = {}
            self.client.inports.clear()

            for port in self.port_names:
                self.ports = self.ports + self.client.get_ports(port)
            sorted_nicely(self.ports)

            # Register TidZam inputs for each MPV ports
            for i in range(0, len(self.ports)):
                self.channels.append(self.client.inports.register("chan"+str(i)))
                self.ring_buffer.append(jack.RingBuffer(self.buffer_jack))

            # If the ports have been connected, start audio streaming
            self.load_streamer()
            time.sleep(2) # TODO: Wait that all ecasound process are ready

            # Activate TidZam ports and connecto MPV
            print("JACK Connector: Tidzam client activation: " +str(len(self.ports))+" ports")
            self.client.activate()
            time.sleep(2)
            for i in range(0, len(self.ports)):
                # Connect Tidzam
                print("JACK Connector: Connection: " + self.ports[i].name + " -> " + self.channels[i].name)
                self.client.connect(self.ports[i], self.channels[i])
                # Connect output stream (ecasound)
                if i != 0:
                    self.client.connect(self.ports[i], self.client.get_port_by_name("ecasound-"+str(i).zfill(2)+":in_1" ))
                    self.client.connect(self.ports[i], self.client.get_port_by_name("ecasound-"+str(i).zfill(2)+":in_2" ))
                else:
                    self.client.connect(self.ports[i], self.client.get_port_by_name("ecasound:in_1"))
                    self.client.connect(self.ports[i], self.client.get_port_by_name("ecasound:in_2"))

            # Wait that all jack ports are connected
            time.sleep(1)

        except Exception as e:
            if self.debug > 0:
                print("JACK Connector: Loading stream exception: " + str(e))
                self.mustReload = True

    def check_jack_connector(self):
        ports = []
        for port in self.port_names:
            ports = ports + self.client.get_ports(port)
        for port in ports:
            if port not in self.ports:
                print("JACK Connector: new input connector detected " + port.name)
                self.mustReload = True

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
            if self.channels_state[p] is True:
                return True
        return False

    def run(self):
        global stream
        run = False
        while not self.stopFlag.wait(0.1):
            with self.lock:
                if self.portsAllReady() and self.mustReload is False:
                    try:
                        # check if there is a new jack device
                        self.check_jack_connector()

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
                                        print("JACK Connector: -----------------------------------")
                                        print("JACK Connector: ** WARNING ** JACK Connector: buffer queue is " + str(int(len(self.channels_data[i])/self.buffer_size)) + " samples" )
                                    if int(len(self.channels_data[i])/self.buffer_size) > 50:
                                        print("JACK Connector: -----------------------------------")
                                        print("JACK Connector: ** ERROR ** JACK Connector: buffer overflow, delay > 50 samples, clean it" )
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
                    except Exception as e:
                        print("JACK Connector: buffer loading...")

                # If there there is no port ready => nothing to wait
                elif self.portStarting() is False or self.mustReload is True:
                    self.load_stream()

                else:
                    if self.debug > 0:
                        print("JACK Connector: waiting port registration.")
                        time.sleep(1)

    def stop(self):
        self.client.deactivate()
        self.client.close()
        self.stopFlag.set()

    def callback_port_connection(self,port_in, port_out, state):
        if state is True:
            self.channels_state[port_in.name] = state
            if self.debug > 1:
                print("JACK Connector: This link is created: " + port_in.name + " -> " + port_out.name)
        else:
            if self.debug > 1:
                print("JACK Connector: This link is broke: " + port_in.name + " -> " + port_out.name)
            self.mustReload = True


    def callback_quit(self,status, reason):
        with self.lock:
            if self.debug > 0:
                print("JACK Connector: process in zombi mode... Restart !\n" + str(status) )
            time.sleep(1)
            self.init_client()

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
