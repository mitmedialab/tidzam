import optparse
import datetime

import analyzer as Analyzer
from App import App

if __name__ == "__main__":
    usage = 'TidzamAnalyzer.py --nn=build/test [--stream=stream.wav | --jack=jack-output] [OPTIONS]'
    parser = optparse.OptionParser(usage=usage)
    parser.set_defaults(stream=False,dic=False,nn="build/default")

    parser.add_option("-s", "--stream", action="store", type="string", dest="stream",
        default=None,
        help="Input audio stream to analyze.")

    parser.add_option("-c", "--channel", action="store", type="int", dest="channel",
        default=None,
        help="Select a particular channel (only with stream option).")

    parser.add_option("-j", "--jack", action="store", type="string", dest="jack",
        default=None,
        help="List of Jack audio mixer ports to process.")

    parser.add_option("-n", "--nn", action="store", type="string", dest="nn",
        help="Neural Network session to load.")

    parser.add_option("-o", "--out", action="store", type="string", dest="out",
        default="/tmp/tidzam/extraction/",
        help="Output folder for audio sound extraction.")

    parser.add_option("--extract", action="store", type="string", dest="extract",
        default=None,
        help="List of classes to extract (--extract=unknown,birds).")

    parser.add_option("--extract-dd", action="store_true", dest="dd", default=True,
        help="Activate the extraction according to a Dynamic Distribution of extracted sample (Default: True).")

    parser.add_option("--extract-channels", action="store", type="string", dest="extract_channels",
        default="",
        help="Specify an id list of particular channels for the sample extraction (Default: "").")

    parser.add_option("--show", action="store_true", dest="show", default=False,
        help="Play the audio samples and show their spectrogram.")

    parser.add_option("--overlap", action="store", type="float", dest="overlap", default=0,
        help="Overlap value (default:0).")

    parser.add_option("--chainAPI", action="store", type="string", dest="chainAPI", default=None,
        help="Provide URL for chainAPI username:password@url (default: None).")

    parser.add_option("--port", action="store", type="int", dest="port", default=8080,
        help="Socket.IO Web port (default: 8080).")

    parser.add_option("--debug", action="store", type="int", dest="DEBUG", default=0,
        help="Set debug level (Default: 0).")

    (opts, args) = parser.parse_args()

    App.verbose          = opts.DEBUG
    App.socketIOanalyzerAdress = "localhost:" + str(opts.port)

    if (opts.stream or opts.jack) and opts.nn:
        callable_objects = []

        ### Sample Extractor Output Connector
        if opts.out is not None:
            if opts.extract is None:
                opts.extract = ""

            if opts.stream is not None:
                # Build folder to store wav file
                a = opts.stream.split('/')
                a = a[len(a)-1].split('.')[0]
                wav_folder = opts.out + '/' + a + '/'
            else:
                wav_folder = opts.out

            import SampleExtractor as SampleExtractor
            # , 'birds', 'cricket', 'nothing', 'rain','wind'
            list_to_extract = opts.extract.split(",")
            extraction_rules = {}

            extractor = SampleExtractor.SampleExtractor(
                    extraction_rules=extraction_rules,
                    extraction_dest=wav_folder,
                    dd=opts.dd)
            callable_objects.append(extractor)

        ### Socket.IO Output Connector
        import SocketIOServer as socketio
        socket = socketio.create_socket("/")
        callable_objects.append(socket)

        ### Chain API Output Connector
        if opts.chainAPI is not None:
            import ChainAPI as ChainAPI
            from requests.auth import HTTPBasicAuth
            ch = ChainAPI.ChainAPI()
            try:
                tmp = opts.chainAPI.split(":")
                user = tmp[0]
                tmp = tmp[1].split("@")
                pwd = tmp[0]
                url = "http://"+tmp[1]
                ch.connect(url, auth=HTTPBasicAuth(user,pwd))
                callable_objects.append(ch)
            except:
                App.error(0, "Error in parsing chainAPI URL: " + opts.chainAPI)
                quit()

        ### Load ANALYZER
        analyzer = Analyzer.Analyzer(opts.nn, callable_objects=callable_objects)

        callable_objects = []
        callable_objects.append(analyzer)

        ### Load Spectrum Visualizer
        if opts.show is True:
            import analyzer_vizualizer as tv
            vizu     = tv.TidzamVizualizer()
            callable_objects.append(vizu)

        ### Load Stream Player
        if opts.stream is not None:
            import input_audiofile as ca
            connector = ca.TidzamAudiofile(opts.stream,
                callable_objects = callable_objects,
                overlap=opts.overlap,
                channel=opts.channel,
                cutoff=analyzer.cutoff)

        elif opts.jack is not None:
            import input_jack as cj
            connector = cj.TidzamJack(opts.jack.split(","),
            callable_objects=callable_objects,
            overlap=opts.overlap,
            cutoff=analyzer.cutoff)

        connector.start()
        socket.start(opts.port)

    else:
        App.log(0, parser.usage)
