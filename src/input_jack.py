from __future__ import division
import jack
import sys, os, signal,time
import numpy as np
import threading
from threading import Thread
import data as tiddata


import re

def sorted_nicely( l ):
    """ Sort the given iterable in the way that humans expect."""
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key.name) ]
    return sorted(l, key = alphanum_key)

class TidzamJack(Thread):
    def __init__(self, port_names, callable_objects=[], debug=0, overlap=0):
        Thread.__init__(self)
        global starting_time
        global TIDZAM_JACK_PORTS

        print("======= JACK CLIENT =======")
        starting_time = -1
        self.debug = debug
        TIDZAM_JACK_PORTS = port_names
        self.lock   = threading.Lock()

        self.mustReload = False
        self.mapping    = []

        self.samplerate = -1
        self.blocksize = -1
        self.buffer_size = 24000
        self.overlap = overlap
        self.buffer_jack = self.buffer_size * 20
        self.stopFlag = threading.Event()

        self.callable_objects = callable_objects
        self.init_client()

    def init_client(self):
        if self.debug > 1:
            print("JACK Connector: Tidzam Jack client initialization.")
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

    def load_stream(self):
        global TIDZAM_JACK_PORTS
        try:
             # Wait that all jack ports are properly disconnected
            print("JACK Connector: reset the Jack client.")
            self.client.deactivate()
            self.client.close()
            time.sleep(2)
            self.init_client()
            self.mustReload = False

            if self.debug > 0:
                print("JACK Connector: stream initialization tentative.")

            # Clean all connections and buffers
            self.ports          = []
            self.channels       = []
            self.ring_buffer    = []
            self.channels_data  = []
            self.mapping        = []
            self.channels_state = {}
            self.client.inports.clear()

            if self.debug > 0:
                print("JACK Connector: list of automatic port connections:")
                print(TIDZAM_JACK_PORTS)

            # Load the port patterns to connect
            for port in TIDZAM_JACK_PORTS:
                pattern_already_loaded = False
                for p in self.ports:
                    if port in p.name:
                        pattern_already_loaded = True
                if pattern_already_loaded is False:
                    self.ports = self.ports + self.client.get_ports(port, is_output=True)
            sorted_nicely(self.ports)

            # Register TidZam inputs for each MPV ports
            for i in range(0, len(self.ports)):
                self.channels.append(self.client.inports.register("input_"+str(i)))
                self.ring_buffer.append(jack.RingBuffer(self.buffer_jack))

            # Activate TidZam ports and connecto MPV
            if self.debug > 0:
                print("JACK Connector: Tidzam client activation: " +str(len(self.ports))+" ports")
            self.client.activate()

            for i in range(0, len(self.ports)):
                # Connect Tidzam
                if "input" not in self.ports[i].name:
                    if self.debug > 0:
                        print("JACK Connector: Connection: " + self.ports[i].name + " -> " + self.channels[i].name)
                    self.client.connect(self.ports[i], self.channels[i])
                    self.mapping.append([self.ports[i].name, self.channels[i].name])

            if self.debug > 0:
                print("JACK Connector: audio stream mapping: ")
                print(self.mapping)

            # Wait that all jack ports are connected
            time.sleep(2)

        except Exception as e:
            if self.debug > 0:
                print("JACK Connector: Loading stream exception: " + str(e))
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
        global starting_time
        run = False
        while not self.stopFlag.wait(0.01):
            with self.lock:
                if self.portsAllReady() and self.mustReload is False:
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
                                    if int(len(self.channels_data[i])/self.buffer_size) > 1:
                                        print("JACK Connector: -----------------------------------")
                                        print("JACK Connector: ** WARNING ** JACK Connector: buffer queue is " + str(int(len(self.channels_data[i])/self.buffer_size)) + " samples" )
                                    if int(len(self.channels_data[i])/self.buffer_size) > 3:
                                        print("JACK Connector: -----------------------------------")
                                        print("JACK Connector: ** ERROR ** JACK Connector: buffer overflow, delay > 3 samples, clean it" )
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
                                            starting_time=starting_time,
                                            mapping=self.mapping)
                    except Exception as e:
                        print("JACK Connector: buffer loading..." + str(e))

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

    def callback_client_registration(self, name, registered):
        global TIDZAM_JACK_PORTS
        if self.debug > 1:
            print("JACK Connector: client connector change " + name + "(" + str(registered) + ")")
        for port in TIDZAM_JACK_PORTS:
            if port in name and "-out_" not in name:
                self.mustReload = True
                break

    def callback_port_registration(self, port, registered):
        if self.debug > 1:
            print("JACK Connector: port registration " + port.name + "(" + str(registered) + ")")

    def callback_port_connection(self,port_in, port_out, state):
        if state is True:
            if self.debug > 1:
                print("JACK Connector: This link is created: " + port_in.name + " -> " + port_out.name)
            if "analyzer" in port_in.name:
                self.channels_state[port_in.name] = state
        else:
            if self.debug > 1:
                print("JACK Connector: This link is broke: " + port_in.name + " -> " + port_out.name)
            if "analyzer" in port_in.name:
                    self.mustReload = True

    def callback_xrun(self, delay):
        if self.debug > 0:
            print("JACK Connector: xrun " + str(delay))

    def callback_quit(self,status, reason):
        with self.lock:
            if self.debug > 0:
                print("JACK Connector: process in zombi mode... Restart !\n" + str(status) )
            time.sleep(1)
            self.init_client()

    def callback_samplerate(self, samplerate):
        self.samplerate = samplerate
        print("JACK Connector: Sample rate at " + str(samplerate))

    def callback_blocksize(self, blocksize):
        self.blocksize = blocksize

    def callback_rt(self,frame):
        try :
            for i in range(len(self.channels)):
                self.ring_buffer[i].write(self.channels[i].get_array())
        except:
            print("JACK Connector: Error loading RT ring buffer")
