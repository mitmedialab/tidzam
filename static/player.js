function Player(parent){

  parent.innerHTML +=  '<div id="dialog-player" title="Controller" style="width:100%;"></div>';

  var audio_html =
  '<audio id="audio_player">    \
  <source src="/stream/" type="audio/wav" />    \
  </audio>                                          \
  <span id="state" style="text-align:center;width:100%;">State</span><br> \
  Local:            \
  <select id="audio_selection">\
  <option value="/stream/">stream.ogg</option>\
  </select><br>\
  <div id="remote_div">Remote: <input type="text" id="remote_url" value="http://doppler.media.mit.edu:8000/impoundment.ogg" style="width:350px;"><input type="button" id="remote_button" value="Load"></div>\
  <br>\
  <div id="results">Results</div>\
  <img src="/fft" id="img_fft">\
  ';



  this.dialog = $( '#dialog-player'  ).dialog({
    autoOpen: true,
    width: 690,
    modal: false,
    open:function(){
      socket.emit('sys', JSON.stringify(
        {sys:{streams:''}}
      ));
    },
    buttons: {
      Update: function(){
        socket.emit('sys', JSON.stringify(
          {sys:{streams:''}}
        ));
      },
      Mute: function(){
        if (document.getElementById('audio_player' ).paused == false)
             $( '#audio_player' ).trigger('pause');
        else $('#audio_player' ).trigger('play');
      },
      Resume: function(){
        socket.emit('sys', JSON.stringify(
          {sys:{control:'resume'}}
        ));
        $( '#audio_player'  ).load();
        $( '#audio_player' ).trigger('play');
      },
      Play: function(){
        if(!document.getElementById('audio_player').paused && !document.getElementById('audio_player').played.length)
          $( '#audio_player'  ).attr('src', '/stream/?time='+ ((new Date()).getTime()));
          $( '#audio_player'  ).load();
          $( '#audio_player' ).trigger('play');
        socket.emit('sys', JSON.stringify(
          {sys:{control:'play'}}
        ))
      },
      Pause: function(){
        socket.emit('sys', JSON.stringify(
          {sys:{control:'pause'}}
        ))
      },
      Prev: function(){
        $( '#audio_player'  ).attr('src', '/stream/?time='+ ((new Date()).getTime()));
        $( '#audio_player'  ).load();
        $( '#audio_player' ).trigger('play');
        socket.emit('sys', JSON.stringify(
          {sys:{control:'prev'}}
        ))
      },
      Next: function(){
        $( '#audio_player'  ).attr('src', '/stream/?time='+ ((new Date()).getTime()));
        $( '#audio_player'  ).load();
        $( '#audio_player' ).trigger('play');
        socket.emit('sys', JSON.stringify(
          {sys:{control:'next'}}
        ))
      }
    }
  });
  $('#dialog-player').html(audio_html);

  function check_audio(){
    var audio = document.getElementById("audio_player");
    if(!audio.paused)
      if (isNaN(audio.duration)){
        $( '#audio_player'  ).attr('src', '/stream/?time='+ ((new Date()).getTime()));
        $( '#audio_player'  ).load();
        $( '#audio_player' ).trigger('play');
      }
    setTimeout(check_audio, 250);
  }

  check_audio();

  /****/

  socket.on('sys', function(msg){
    try {
      obj = msg;
      if (! obj.sys) throw "not a sys object";
      $('#state').html('State: ' + obj.sys.state + '<br>Count: ' + obj.sys.sample_count +'<br><br>Source:');
    }
    catch (err){
      console.log("WARNING: player socket error " + err);
    }
  });

  $( '#audio_player'  ).on('ended', function(){
    $( '#audio_player'  ).attr('src', '/stream/?time='+ ((new Date()).getTime()));
    $( '#audio_player'  ).load();
    $( '#audio_player' ).trigger('play');
  });

  $( '#audio_selection'  ).on('change', function(ev, ui){
     if (socket || 0){
      $( '#remote_div' ).show();

      socket.emit('sys', '{ "sys": { "url": "' + $( '#audio_selection option:selected' ).val() + '" } }');
      socket.emit('sys', JSON.stringify(
        {sys:{control:'resume'}}
      ));
      $( '#audio_player'  ).load();
      $( '#audio_player' ).trigger('play');
    }
    else console.log("no socket");
    });

  $( '#remote_button'  ).click(function(){
    socket.emit('sys', '{ "sys": { "url": "' + $( '#remote_url' ).val() + '" } }');
  });


  /****/

  this.show = function(){
    this.dialog.dialog('open');
    socket.emit('sys', JSON.stringify(
      {sys:{streams:''}}
    ));
  }

  this.process = function(json){
    if (json.analysis && json.chan){
        document.getElementById('img_fft').src = '/fft?time='+((new Date()).getTime());
        if (json.analysis.result.indexOf('->') == -1)
        $( '#results' ).html( ''+ json.chan + ' - ' +json.analysis.result);
      }

    if(json.sys)
      // Reload source selector and add default options: Icecast, Microphone and server streams
      if (json.sys.streams){
        $( '#audio_selection' ).empty();
        $( '#audio_selection' ).append($("<option></option>").attr("value", " "));
        $( '#audio_selection' ).append($("<option>Microphone (server)</option>").attr("value", "microphone"));
        for (var i=0; i < json.sys.streams.length; i++)
          $( '#audio_selection' ).append($("<option></option>").attr("value", json.sys.streams[i]).text(json.sys.streams[i]));
        }
    /****/
  }
}
