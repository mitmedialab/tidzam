from __future__ import division
import jack
import sys, os, signal,time
import numpy as np
import threading
from threading import Thread
import re

import TidzamDatabase as database
from socketIO_client import SocketIO
from App import App

import traceback

def sorted_nicely( l ):
    """ Sort the given iterable in the way that humans expect."""
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key.name) ]
    return sorted(l, key = alphanum_key)

class TidzamJack(Thread):
    def __init__(self, port_names, callable_objects=[], overlap=0, socketio_address="localhost:8001", cutoff=[20,170]):
        Thread.__init__(self)

        App.ok(0, "Jack client initialized")
        self.jack_ports_toload = port_names
        self.lock   = threading.Lock()

        self.socketIO = None
        self.socketio_address = App.socketIOanalyzerAdress

        self.mustReload = False
        self.mapping    = []
        self.sources    = []

        self.samplerate     = -1
        self.blocksize      = -1
        self.buffer_size    = -1
        self.overlap        = overlap
        self.buffer_jack    = -1
        self.stopFlag       = threading.Event()
        self.cutoff         = cutoff

        self.callable_objects = callable_objects
        self.init_client()

    def init_client(self):
        App.log(1, "Tidzam Jack client initialization.")
        self.client = jack.Client("analyzer")
        self.client.set_samplerate_callback(self.callback_samplerate)
        self.client.set_blocksize_callback(self.callback_blocksize)
        self.client.set_process_callback(self.callback_rt)
        self.client.set_shutdown_callback(self.callback_quit)
        self.client.set_client_registration_callback(self.callback_client_registration)
        self.client.set_port_registration_callback(self.callback_port_registration, only_available=True)
        self.client.set_port_connect_callback(self.callback_port_connection, only_available=True)
        self.client.set_xrun_callback(self.callback_xrun)
        self.channels_state = {}

    def init_socketIO(self):
        tmp = self.socketio_address.split(":")
        self.socketIO = SocketIO(tmp[0], int(tmp[1]))
        self.socketIO.on('JackSource', self.update_sources)
        threading.Thread(target=self._run_socketIO).start()
        App.ok(0, "Connected to " + self.socketio_address +"")

    def _run_socketIO(self):
        while not self.stopFlag.wait(0.1):
            self.socketIO.wait(1)

    def update_sources(self, sources):
        self.sources = sources

    def load_stream(self):
        try:
             # Wait that all jack ports are properly disconnected
            App.log(1, "Reset the Jack client.")
            self.client.inports.clear()
            self.client.outports.clear()
            time.sleep(1)

            self.client.deactivate()
            self.client.close()
            #
            self.init_client()
            self.mustReload = False

            App.log(1, "Stream initialization tentative.")

            # Clean all connections and buffers
            self.ports          = []
            self.channels       = []
            self.ring_buffer    = []
            self.channels_data  = []
            self.mapping        = []
            self.channels_state = {}
            self.client.inports.clear()

            App.log(1, "List of automatic port connections:")
            App.log(1, self.jack_ports_toload)

            # Load the port patterns to connect
            for port in self.jack_ports_toload:
                self.ports = self.ports + self.client.get_ports(port, is_output=True)
            sorted_nicely(self.ports)

            # Register TidZam inputs for each MPV ports
            for i in range(0, len(self.ports)):
                self.channels.append(self.client.inports.register("input_"+str(i)))
                self.ring_buffer.append(jack.RingBuffer(self.buffer_jack))

            # Activate TidZam ports and connecto MPV
            App.log(1, "Tidzam client activation: " +str(len(self.ports))+" ports")
            self.client.activate()

            for i in range(0, len(self.ports)):
                # Connect Tidzam
                if "input" not in self.ports[i].name:
                    App.log(2, "Connection " + self.ports[i].name + " -> " + self.channels[i].name)
                    self.client.connect(self.ports[i], self.channels[i])

                    # Store the stream mapping
                    self.mapping.append([self.ports[i].name, self.channels[i].name])

                    # If there is no starting time defined for this stream, we create one
                    tmp = self.ports[i].name.split(":")[0]
                    found = False
                    for source in self.sources:
                        if source["name"] in tmp:
                            found = True
                    if found is False:
                        self.sources.append({"name":tmp,"starting_time":time.strftime("%Y-%m-%d-%H-%M-%S")})

            App.log(2, "Audio stream mapping: ")
            App.log(2, self.mapping)

            # Wait that all jack ports are connected
            time.sleep(0)

        except Exception as e:
            App.error(0, "Loading stream exception: " + str(e))
            #self.mustReload = True

    def portsAllReady(self):
        for p in self.channels_state:
            if self.channels_state[p] is False:
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
        run = False
        while not self.stopFlag.wait(0.01):
            if self.socketIO is None:
                self.init_socketIO()

            with self.lock:
                if self.portsAllReady() and self.mustReload is False and self.buffer_size > -1:
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
                                fs, t, Sxx, size = database.get_spectrogram(data, self.samplerate, cutoff=self.cutoff )

                                if i == 0:
                                    if int(len(self.channels_data[i])/self.buffer_size) > 1:
                                        App.warning(0, "Buffer queue is " + str(int(len(self.channels_data[i])/self.buffer_size)) + " samples" )
                                    if int(len(self.channels_data[i])/self.buffer_size) > 3:
                                        App.warning(0, "Buffer overflow, delay > 3 samples, clean it" )
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
                            # Call all thread consumers
                            inputs = {
                                "ffts":{
                                    "data":Sxxs,
                                    "time_scale":ts,
                                    "freq_scale":fss,
                                    "size":size
                                    },
                                "samplerate":self.samplerate,
                                "sources":self.sources,
                                "audio":np.transpose(datas),
                                "overlap":self.overlap,
                                "mapping":self.mapping
                                }

                            for obj in self.callable_objects:
                                obj.execute(inputs)

                    except Exception as e:
                        App.error(0, "Buffer loading..." + str(e))
                        traceback.print_exc()

                # If there there is no port ready => nothing to wait
                elif self.portStarting() is False or self.mustReload is True:
                    self.load_stream()

                else:
                    App.log(0, "waiting port registration.")
                    time.sleep(1)

    def stop(self):
        self.client.deactivate()
        self.client.close()
        self.stopFlag.set()

    def callback_client_registration(self, name, registered):
        App.log(2, "Client connector change " + name + "(" + str(registered) + ")")
        for port in self.jack_ports_toload:
            if port in name and "-out_" not in name:
                self.mustReload = True
                break

    def callback_port_registration(self, port, registered):
        App.log(2, "Port registration " + port.name + "(" + str(registered) + ")")

    def callback_port_connection(self, port_in, port_out, state):
        if state is True:
            App.log(2, "This link is created: " + port_in.name + " -> " + port_out.name)
            if "analyzer" in port_out.name:
                self.channels_state[port_in.name] = state
        else:
            App.log(2, "This link is broke: " + port_in.name + " -> " + port_out.name)
            if "analyzer" in port_in.name:
                    self.mustReload = True

    def callback_xrun(self, delay):
        App.log(1, "xrun " + str(delay))

    def callback_quit(self,status, reason):
        with self.lock:
            App.warning(1, "Jack client in zombi mode... Restart !\n" + str(status) )
            time.sleep(1)
            self.init_client()

    def callback_samplerate(self, samplerate):
        self.samplerate     = samplerate
        self.buffer_size    = int(self.samplerate / 2)
        self.buffer_jack    = 20 * self.buffer_size
        App.log(0, "Sample rate at " + str(samplerate))

    def callback_blocksize(self, blocksize):
        self.blocksize = blocksize

    def callback_rt(self,frame):
        try :
            for i in range(len(self.channels)):
                self.ring_buffer[i].write(self.channels[i].get_array())
        except:
            App.error(0, "Error loading RT ring buffer")
