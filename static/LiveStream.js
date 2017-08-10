window.URL = window.URL || window.webkitURL;
navigator.getUserMedia  = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia;

var LiveStream = function(source){

  const livestream_io = io("//tidzam.media.mit.edu/",
        { path: '/livestream/socket.io'});

  const tidzam_io = io("//tidzam.media.mit.edu/",
      { path: '/socket.io' ,
       forceNew:true});


       livestream_io.emit('sys', JSON.stringify({"sys":{"database":""}}));

  portname = null
  callback = null

  this.start = function(cb) {
    if (navigator.getUserMedia)
    navigator.getUserMedia({audio: true}, onSuccess, onFail);
    else  console.log('navigator.getUserMedia not present');
    callback = cb
  }

  this.stop = function(){
    console.log("Stream terminated")
    mediaStreamContext.close()
    livestream_io.emit("sys", JSON.stringify({sys:{del_livestream:true}}))
    tidzam_io.removeAllListeners(portname);
    portname = null
    callback = null
  }

  function onFail(e) {
    if (callback || false)
      callback('Capture device access: Rejected!' + e)
  };

  function onSuccess(s) {
    var AudioContext = window.AudioContext || window.webkitAudioContext;
    context             = new AudioContext();
    mediaStreamSource   = context.createMediaStreamSource(s);
    mediaStreamContext  = mediaStreamContext = mediaStreamSource.context;
    node                = mediaStreamContext.createScriptProcessor(4096, 2, 2);

    // Request the port name which has been attributed
    if (callback || false){
      livestream_io.on("sys",function(obj){
        if (obj.portname == null)
          livestream_io.emit("sys", JSON.stringify({sys:{add_livestream:true}}));
        else {
          portname = obj.portname.replace(":","-")
          if ( tidzam_io._callbacks[portname] == undefined ){
            console.log("Add event listener on " + portname)
            tidzam_io.on(portname, callback);
          }

        }
      });
    }

    var count = 5
    node.onaudioprocess = function(e){
      data = prepareChunk(e.inputBuffer.getChannelData(0))
      livestream_io.emit("audio",data.buffer)

      // Ask the portname of the stream
      if (count-- == 0 && portname == null ){
        livestream_io.emit("sys", JSON.stringify({sys:{add_livestream:true}}))
        count = 5
      }
    }
    mediaStreamSource.connect(node);
    //node.connect(mediaStreamContext.destination);
    console.log("Samplerate:  " +mediaStreamContext.sampleRate)
  }

  function prepareChunk (samples){
    var buffer = new ArrayBuffer(samples.length * 2);
    var view = new DataView(buffer);
    for (var i = 0, offset=0; i < samples.length; i++, offset+=2){
      var s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return view
  }

};
