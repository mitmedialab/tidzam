import jack
import sys, os
import numpy as np
import threading
from threading import Thread
import subprocess
import data as tiddata

class TidzamJack(Thread):
    def __init__(self, port_name, callable_objects=[]):
        Thread.__init__(self)

        self.data_size = (150,186)
        self.callable_objects = callable_objects

        self.client = jack.Client("tidzam")
        self.ports = self.client.get_ports(port_name)

        self.samplerate = -1
        self.blocksize = -1
        self.buffer_size = 24000
        self.buffer_jack = self.buffer_size * 20

        self.channels = []
        self.ring_buffer = []
        self.channels_data = []

        self.stopFlag = threading.Event()

        for i in range(0, len(self.ports)):
            self.channels.append(self.client.inports.register("chan"+str(i)))
            self.ring_buffer.append(jack.RingBuffer(self.buffer_jack))

        self.client.set_samplerate_callback(self.callback_samplerate)
        self.client.set_blocksize_callback(self.callback_blocksize)

        self.client.set_process_callback(self.callback_rt)

        self.client.activate()

        for i in range(0, len(self.ports)): #p in ports:
            self.client.connect(self.ports[i], self.channels[i])

        self.run_streaming()

    def stop(self):
        self.client.deactivate()
        self.client.close()
        self.stopFlag.set()

    def callback_samplerate(self, samplerate):
        self.samplerate = samplerate
        print("Sample rate: " + str(samplerate) + "Hz" )

    def callback_blocksize(self, blocksize):
        self.blocksize = blocksize
        print("Blocksize: " + str(blocksize))

    def callback_rt(self,frame):
        for i in range(len(self.channels)):
                self.ring_buffer[i].write(self.channels[i].get_array())

    def run(self):
        run = False
        while not self.stopFlag.wait(0.1):
            for i in range(len(self.channels)):
                try:
                    data = self.ring_buffer[i].read(self.buffer_jack)
                    data = np.frombuffer(data, dtype='float32')
                    try:
                        self.channels_data[i] = np.concatenate((self.channels_data[i], data ))
                    except:
                        self.channels_data.append( data )

                    # If the buffer contains the required data, we truncate it and send result
                    if len(self.channels_data[i]) >= self.buffer_size:
                        run = True
                        data = self.channels_data[i][0:self.buffer_size]
                        self.channels_data[i] = self.channels_data[i][self.buffer_size:len(self.channels_data[i])]
                        fs, t, Sxx = tiddata.get_spectrogram(data, self.samplerate)

                        if i == 0:
                            print("-----------------------------------")
                            print("Buffer load: " + str(int(len(self.channels_data[i])/self.buffer_size)) + " samples" )
                            datas   = data
                            Sxxs    = Sxx
                            fss     = fs
                            ts      = t
                        else:
                            Sxxs    = np.vstack((Sxxs, Sxx))
                            fss     = np.vstack((fss, fs))
                            ts      = np.vstack((ts, t))
                            datas   = np.vstack((datas, data))
                    else:
                        run = False
                except:
                    print("Sample error")

            if run is True:
                for obj in self.callable_objects:
                    obj.execute(Sxxs, fss, ts, [np.transpose(datas), self.samplerate], overlap=0,stream="rt")

    def run_streaming(self):
        print("====================================")
        print("Start channel streamer for IceCast")
        print("====================================\n")
        self.streamer_process = []
        FNULL = open(os.devnull, 'w')

        with open("icecast/ices-templates.xml", "r") as file_template:
            for i in range(0, len(self.ports)):
                file_template.seek(0)
                template = file_template.read()
                template = template.replace("/chan.ogg", "/ch"+str(i).zfill(2) +".ogg")
                with open("/tmp/ices-chan"+str(i)+".xml", "w") as file:
                    file.write(template)

                cmd = ["./icecast/icecast_stream.sh", str(i)]
                self.streamer_process.append(subprocess.Popen(cmd,
                        shell=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE))

        print("====================================\n")
        #
