import socketio
from aiohttp import web
import aiohttp_cors
import asyncio
import numpy as np
import optparse
import traceback
import glob, os

import soundfile as sf
from TidzamDatabase import get_spectrogram
from App import App

sio = socketio.AsyncServer(
            ping_timeout=120,
            ping_interval=10,
            cors_credentials='tidmarsh.media.mit.edu')
app = web.Application()

cors = aiohttp_cors.setup(app, defaults={
        "tidmarsh.media.mit.edu": aiohttp_cors.ResourceOptions(),
    })
sio.attach(app)
class TidzamDatabaseManager(socketio.AsyncNamespace):

    def __init__(self,namespace, database_folder):
        socketio.AsyncNamespace.__init__(self, namespace)
        sio.register_namespace(self)

        self.database_folder = database_folder

        cors.add(app.router.add_static('/database', "out-tidzam"), {
                "*":aiohttp_cors.ResourceOptions(allow_credentials=True)
            })

    def get_samples_list(self, classe, start=0, limit=-1):
        files_result = []
        tmp = classe.split("-")
        classe = tmp[0]
        if len(tmp) > 1:
            for i in range(2, len(tmp)):
                classe += "/" + tmp[i]
            classe += "/" + tmp[len(tmp)-2] + "-" + tmp[len(tmp)-1]

        App.log(2, "Client request "+str(limit)+" samples lists from " + self.database_folder + "/" +classe)
        files = glob.glob(self.database_folder + "/"+classe+"*/**/*.wav", recursive=True)
        if start == -1:
            start = 0
            idx = np.arange(len(files))
            np.random.shuffle(idx)
            files = np.asarray(files)[idx]

        for i in range(start, len(files) ):
            data, samplerate = sf.read(files[i])
            try:
                try:
                    freq, time, fft, size = get_spectrogram(data, samplerate, show=False)
                except:
                    freq, time, fft, size = get_spectrogram(data[:,0], samplerate, show=False)
                files_result.append({
                    "path":files[i].replace(self.database_folder,""),
                    "length":len(data)/samplerate,
                    "samplerate":samplerate,
                    "fft": {
                        "data":fft[0].tolist(),
                        "time_scale": time.tolist(),
                        "freq_scale": freq.tolist(),
                        "size":size
                        }
                })
            except:
                App.error(0, "During the spectrogram processing of " + files[i])

            if limit > -1 and len(files_result) >= limit:
                break
        return files_result

    def start(self, port=5678):
        web.run_app(app, port=port)

    def on_connect(self, sid, environ):
        App.log(1,"Client connection " + str(sid) )

    def on_disconnect(self, sid):
        App.log(1, "Client disconnection " + str(sid) )

    async def on_DatabaseManager(self, sid, data):
        if isinstance(data, dict) is False:
            await sio.emit("sys",
                {"error":"request must be a JSON.", "request-origin":data},
                room=sid)
            return

        if data.get("samples_list") is not None:
            if data["samples_list"].get("classe") is None:
                await sio.emit("DatabaseManager",
                    {"error":"classe field MUST be specified", "request-origin":data},
                    room=sid)
                return
            limit   = int(data["samples_list"].get("limit")) if data["samples_list"].get("limit") else 10
            start   = int(data["samples_list"].get("start")) if data["samples_list"].get("start") else 0
            classe  = data["samples_list"].get("classe") if data["samples_list"].get("classe") else ""

            await sio.emit("DatabaseManager",
                {"samples_list":self.get_samples_list(classe, start, limit)},
                room=sid)

        if data.get("classes_list") is not None:
            classes = []
            for root, dirs, files in os.walk(self.database_folder):
                classes += dirs
            for i, cl in enumerate(classes):
                classes[i] = cl.split("(")[0]
            classes = list(set(classes))
            await sio.emit("DatabaseManager",
                {"classes_list":sorted(classes)},
                room=sid)

        if data.get("extract") is not None:
            if data["extract"].get("path") is None or data["extract"].get("time") is None or data["extract"].get("classe") is None:
                await sio.emit("DatabaseManager",
                    {"error":"an argument is missing (path, time, classe)", "request-origin":data},
                    room=sid)
                return

            print(data.get("extract"))
            end_file = data["extract"]["path"].split("]")[1]
            dest_name = data["extract"]["classe"].split(".")[0] if len(data["extract"]["classe"].split(".")) > 1 else ""
            dest_name += data["extract"]["classe"] + "/['" + data["extract"]["classe"] + "']" + end_file
            print(dest_name)
            with sf.SoundFile(self.database_folder + "/" + data["extract"]["path"], 'r') as fin:
                with sf.SoundFile(self.database_folder + "/" + dest_name, 'w',
                            samplerate=fin.samplerate,
                            channels=1) as fout:
                    fin.seek( int(data["extract"]["time"] * fin.samplerate) )
                    data = fin.read(int(fin.samplerate * 0.5))
                    print(len(data))
                    fout.write(data)

if __name__ == "__main__":
    parser = optparse.OptionParser(usage="python src/TidzamDatabase.py")

    parser.add_option("--database-folder", action="store", type="string", dest="database_folder",
        default=None, help="Define the path to the databse .")

    parser.add_option("--port", action="store", type="int", dest="port",
        default=5678, help="SocketIO server port (default: 5678).")

    parser.add_option("--debug", action="store", type="int", dest="debug",
        default=2, help="Debug level (default: 2).")

    (options, args) = parser.parse_args()
    App.verbose     = options.debug

manager = TidzamDatabaseManager("/", database_folder=options.database_folder)
manager.start(options.port)
