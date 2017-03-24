function DetectionMap(parent){
  this.parent = parent
  parent.innerHTML += '<div id="detection_map" title="Detection Map" style="width:100%; text-align:center;"></div>'

    $( "#detection_map" ).dialog({
      autoOpen: false,
      width: 750,
      height: 750,
      modal: false,
    });
    $( "#detection_map" ).html(
      '<span id="audio_text"></span><div id="detection_map_area" style="height:750px;"></div>'+
      '<audio controls id="audio_player"><source src="/chan0" type="audio/wav"></audio>'
    );
    $( "#detection_map" ).attr('style','font-size:12px;');


  var location = {lat: 41.8997582, lng: -70.571251};
  var map = null;
  var markers = Array()
  function initMap() {
    map = new google.maps.Map(document.getElementById('detection_map_area'), {
      center: location,
      zoom: 18,
      mapTypeId: google.maps.MapTypeId.SATELLITE
    });

    this.chainAPI = new ChainAPI()
    this.streams  = this.chainAPI.getStreamsInfo();
    for (var i=0; i<this.streams.length; i++){
      marker = new google.maps.Marker({
            position: {lat: this.streams[i].latitude, lng: this.streams[i].longitude},
            icon:"static/img/unknow.png"
            })
      marker.name = this.streams[i].name
      marker.setMap(map);
      markers.push(marker);

      google.maps.event.addListener(marker, 'click', function() {
        stream = 'http://deep-resenv.media.mit.edu:8000/'+this.name+'.ogg'
        $( '#audio_player'  ).attr('src', stream);
        $( '#audio_player'  ).load();
        $( '#audio_player' ).trigger('play');
        $( '#audio_text' ).html("Listening: " + stream)
        });
      }
  }


  this.show = function(){
    if (map == null)
      initMap();
    $( "#detection_map" ).dialog("open");
  }


  socket.on('sys', function(msg){
      for (var i=0; i < msg.length; i ++)
        for(var j=0; j < markers.length; j++)
          if (markers[j].name == "ch"+("0" + msg[i].chan).slice(-2))
            markers[j].setIcon("static/img/"+msg[i].analysis.result+".png");
    });
}
