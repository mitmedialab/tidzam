from aiohttp import web
import aiohttp_cors
import asyncio
import numpy as np
import optparse
import traceback
import glob, os
import re
from PIL import Image
from PIL import ImageOps
import soundfile as sf
from App import App
import base64
import math
import psycopg2
import struct, json
from io import BytesIO
import os, signal

from TidzamDatabase import get_spectrogram
import ChainAPI as ChainAPI


def convertToPNG(im):
    with BytesIO() as f:
        im.save(f, format='PNG')
        return f.getvalue()


class TidzamDatabaseManager():

    def __init__(self, database_folder):
        self.chain           = ChainAPI.ChainAPI()
        self.database_folder = database_folder

    def arrayToPNG(self, array, size):
        res = []
        for i in range(size[0]*size[1]):
            color = 255 - array[0][i] * 255
            color = 255 if color >= 250 else 0
            res.append(color)
        tmp = np.reshape(res, [size[0], size[1]] )

        im = Image.fromarray(np.asarray(tmp, np.uint8))
        im = ImageOps.autocontrast(im)
        im = ImageOps.mirror(im)
        im = im.rotate(180)
        buffered = BytesIO()
        im.save(buffered, format="PNG",optimize=False,quality=100)
        return buffered


    async def add_recording_database_request(self, req):
        file = str(req.rel_url).replace("/add/","")
        file = self.database_folder + "/" + file
        file = file.replace('%5B', '[').replace('%5D', ']');
        self.add_recording_database(file)
        self.conn.commit()

        if self.cur.rowcount:
            return web.Response(text="done "+ file)
        else:
            return web.Response(text="fail adding "+ file)

    async def make_fft(self,request):
        recording = str(request.rel_url).replace("/fft/","")
        recording = self.database_folder + "/" + recording
        recording = recording.replace('%5B', '[').replace('%5D', ']');
        recording = recording.replace("png","wav")
        App.log(2, "FFT for " + recording)
        data, samplerate = sf.read(recording)
        try:
            freq, time, fft, size = get_spectrogram(data, samplerate, show=False, cutoff=[0,170])
        except:
            freq, time, fft, size = get_spectrogram(data[:,0], samplerate, show=False, cutoff=[0,170])

        im = self.arrayToPNG(fft,size)
        im = base64.b64encode(im.getvalue())
        return web.Response(body=im, content_type='image/png')

    def start(self, port=5678):
        app.router.add_get('/fft/{tail:.*}', self.make_fft)
        app.router.add_get('/add/{tail:.*}', self.add_recording_database_request)
        cors.add(app.router.add_static('/database', "out-tidzam"), {
            "*":aiohttp_cors.ResourceOptions(allow_credentials=True)
            })
        web.run_app(app, port=port)


    def get_fileinfo(self,path):
        tidzam_detection = None
        source           = None
        datetime         = None

        recording    = path.replace(self.database_folder,"")

        classe       = recording.split("/")
        classe       = classe[len(classe)-2]
        classe       = classe.split("(")
        origin       = classe[1][:-1] if len(classe) == 2 else None
        classe       = classe[0]

        file      = recording.split("/")
        file      = file[len(file)-1]

        data, samplerate = sf.read(path)
        duration     = len(data)/samplerate

        # Check filename version 3
        file_pattern = re.compile("\['(.*?)'\]\((.*?)\)_(.*?).wav")
        file_matches = file_pattern.findall(file)
        if(len(file_matches)>0):
            if(len(file_matches[0]) == 3):
                tidzam_detection = file_matches[0][0]
                source           = file_matches[0][1]
                datetime         = file_matches[0][2]

        return recording, tidzam_detection, source, samplerate, duration, datetime,classe, origin

    def add_recording_database(self,f):
        try:
            recording, tidzam_detection, source, samplerate, duration, datetime, classe, origin = self.get_fileinfo(f)
            try:
                source_chain = source.split("-")
                source_chain = source_chain[0] + ":"+source_chain[1]+"_"+source_chain[2]
            except:
                source_chain = source
            try:
                geolocation = json.dumps(self.chain.getLocation(source_chain))
            except:
                geolocation = json.dumps({})

            self.cur.execute("INSERT INTO recordings (recording, tidzam_detection, source, samplerate, duration, datetime,classe, origin,geolocation) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (recording,tidzam_detection,source,samplerate, duration,datetime, classe, origin,geolocation, ))

        except:
            print("Error adding the audio file in database ("+f+")") #(recording, tidzam_detection, source, samplerate, duration, datetime,classe, origin)
            traceback.print_exc()
        return False

    def cron_recordings_list(self,chain_url):
        self.chain.connect(chain_url)
        App.log(1,"Read folder " + self.database_folder)
        files = glob.glob(self.database_folder+"**/*.wav", recursive=True)

        for f in files:
            if (os.path.isfile(f)):
                fr = f.replace(self.database_folder,"")
                self.cur.execute("SELECT * FROM recordings WHERE recording=%s",(fr,))
                res = self.cur.fetchone()
                if(res is None):
                    self.add_recording_database(f)
                    App.log(2,"Added " + fr)
                else:
                    App.log(2,"Skip " + fr)
            self.conn.commit()

    def pq_connect(self, db_server,db_port,db_name,db_user,db_pwd):
        try:
            self.conn = psycopg2.connect("host = "+db_server+" port = "+str(db_port)+" dbname = "+db_name+" user = "+db_user+" password = "+db_pwd)
            App.ok(0,"Connected to Postgres server")
            self.cur  = self.conn.cursor()

        except:
            App.error(0,"Unable to connect to postgres (host = "+db_server+" port = "+str(db_port)+" dbname = "+db_name+" user = "+db_user+" password = XXXX)")

    def pq_disconnect(self):
        try:
            self.cur.close()
            self.conn.close()
        except:
            App.error(0,"Unable to disconnect to postgres")

if __name__ == "__main__":
    parser = optparse.OptionParser(usage="python src/TidzamDatabase.py")

    parser.add_option("--database-folder", action="store", type="string", dest="database_folder",
        default=None, help="Define the path to the databse .")

    parser.add_option("--port", action="store", type="int", dest="port",
        default=5678, help="SocketIO server port (default: 5678).")

    parser.add_option("--debug", action="store", type="int", dest="debug",
        default=2, help="Debug level (default: 2).")

    parser.add_option("--cron", action="store_true", dest="cron",
        default=False, help="Start cron jobs (default: false).")

    parser.add_option("--chainAPI", action="store", type="string", dest="chainAPI", default=None,
        help="Provide URL for chainAPI username:password@url (default: None).")

    parser.add_option("--postgres", action="store", type="string", dest="postgres", default=None,
        help="Provide URL for postgres username:password@host/database (default: None).")

    (options, args) = parser.parse_args()
    App.verbose     = options.debug

manager = TidzamDatabaseManager(database_folder=options.database_folder)

if options.postgres is None:
    print("--postgres should be given.")
    exit()

file_pattern = re.compile("(.*?):(.*?)@(.*?):(.*?)/(.*)")
file_matches = file_pattern.findall(options.postgres)
if(len(file_matches[0]) != 5):
    print("Wrong postgres url "+options.postgres)
    exit()
manager.pq_connect(file_matches[0][2], file_matches[0][3], file_matches[0][4], file_matches[0][0],file_matches[0][1])

if (options.cron):
    if options.database_folder is None:
        print("--database-folder should be given.")
        exit()

    if options.chainAPI is None:
        print("--chainAPI should be given.")
        exit()

    manager.cron_recordings_list(options.chainAPI)
    manager.pq_disconnect()
else:
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
            "tidmarsh.media.mit.edu": aiohttp_cors.ResourceOptions(),
        })

    manager.start(options.port)
    manager.pq_disconnect()

App.ok(0,"exit.")
os.kill(os.getpid(), signal.SIGKILL)
