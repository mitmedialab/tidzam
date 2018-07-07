import inspect
import datetime

class App:
    verbose = 0
    socketIOanalyzerAdress = "localhost:8001"

    def log(level, msg):
        if App.verbose >= level:
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            print(str(datetime.datetime.now()) + "\t" + module.__name__ + "\t[LOG] ", msg)

    def ok(level, msg):
        if App.verbose >= level:
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            print(str(datetime.datetime.now()) + "\t" + module.__name__ + "\t[\033[32mOK\033[0m] ", msg)

    def warning(level, msg):
        if App.verbose >= level:
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            print(str(datetime.datetime.now()) + "\t" + module.__name__ + "\t[\033[33mWARNING\033[0m] ", msg)

    def error(level, msg):
        if App.verbose >= level:
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            print(str(datetime.datetime.now()) + "\t" + module.__name__ + "\t[\033[31mERROR\033[0m] ", msg)

global App
