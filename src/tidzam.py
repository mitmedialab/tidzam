import optparse

import analyzer as Analyzer

if __name__ == "__main__":
    usage = 'analyzer.py --nn=build/test --stream=stream.wav [--show, -h]'
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
        help="Input audio stream from Jack audio mixer to analyze.")

    parser.add_option("-n", "--nn", action="store", type="string", dest="nn",
        help="Neural Network session to load.")

    parser.add_option("-o", "--out", action="store", type="string", dest="out",
        default="/tmp/tidzam/extraction/",
        help="Output folder for audio sound extraction.")

    parser.add_option("--extract", action="store", type="string", dest="extract",
        default=None,
        help="List of classes to extract (--extract=unknown,birds).")

    parser.add_option("--extract-dd", action="store_true", dest="dd",
        help="Activate the extraction according to a Dynamic Distribution of extracted sample (Default: False).")

    parser.add_option("--show", action="store_true", dest="show", default=False,
        help="Play the audio samples and show their spectrogram.")

    parser.add_option("--overlap", action="store", type="float", dest="overlap", default=0,
        help="Overlap value (default:0).")

    parser.add_option("--chainAPI", action="store", type="string", dest="chainAPI", default=None,
        help="Provide URL for chainAPI username:password@url (default: None).")

    parser.add_option("--debug", action="store", type="int", dest="DEBUG", default=0,
        help="Set debug level (Default: 0).")

    (opts, args) = parser.parse_args()



    if (opts.stream or opts.jack) and opts.nn:
        callable_objects = []

        ### Sample Extractor Output Connector
        if opts.out is not None and opts.extract is not None:
            if opts.stream is not None:
                # Build folder to store wav file
                a = opts.stream.split('/')
                a = a[len(a)-1].split('.')[0]
                wav_folder = opts.out + '/' + a + '/'
            else:
                wav_folder = opts.out

            import connector_SampleExtractor as SampleExtractor
            # , 'birds', 'cricket', 'nothing', 'rain','wind'
            list_to_extract = opts.extract.split(",")
            extractor = SampleExtractor.SampleExtractor(list_to_extract, wav_folder, dd=opts.dd, debug=opts.DEBUG)
            callable_objects.append(extractor)

        ### Socket.IO Output Connector
        import connector_socketio as connector_socketio
        socket = connector_socketio.create_socket("/")
        callable_objects.append(socket)

        ### Chain API Output Connector
        if opts.chainAPI is not None:
            import connector_ChainAPI as ChainAPI
            from requests.auth import HTTPBasicAuth
            ch = ChainAPI.ChainAPI(opts.DEBUG)
            try:
                tmp = opts.chainAPI.split(":")
                user = tmp[0]
                tmp = tmp[1].split("@")
                pwd = tmp[0]
                url = "http://"+tmp[1]
                print("======== CHAIN API ========")
                print("Site: " + url)
                print("user: " + user)
                ch.connect(url, auth=HTTPBasicAuth(user,pwd))
                callable_objects.append(ch)
            except:
                print("Error in parsing chainAPI URL: " + opts.chainAPI)
                quit()

        ### Load ANALYZER
        analyzer = Analyzer.Analyzer(opts.nn, callable_objects=callable_objects, debug=opts.DEBUG)

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
                callable_objects = callable_objects,  overlap=opts.overlap, channel=opts.channel)

        elif opts.jack is not None:
            import input_jack as cj
            connector = cj.TidzamJack(opts.jack, callable_objects=callable_objects, debug=opts.DEBUG, overlap=opts.overlap)

        connector.start()
        #time.sleep(2)
        #date_in_future = (datetime.today() + timedelta(1)).strftime("%Y-%m-%d-%H-%M-%S")
        #socket.load_source(date_in_future)
        socket.start()

    else:
        print(parser.usage)
