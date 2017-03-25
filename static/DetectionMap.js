function DetectionMap(parent){
  this.parent = parent
  this.channel = channel = null
  this.graph   = graph   = {name:null}
  parent.innerHTML += '<div id="detection_map" title="Detection Map" width=100% text-align:center;"></div>'

    $( "#detection_map" ).dialog({
      autoOpen: false,
      width: 1024,
      height: 850,
      modal: false,
    });
    $( "#detection_map" ).html(
      '<audio controls id="audio_player" style="width:100%">'+
      '<source src="/chan0" type="audio/wav"></audio>'+
      '<div id="detection_map_area" style="height:750px;"></div>'
    );
    $( "#detection_map" ).attr('style','font-size:12px;');


  var location = {lat: 41.8997582, lng: -70.571101};
  var map = null;
  var markers = Array()
  function initMap() {
    map = new google.maps.Map(document.getElementById('detection_map_area'), {
      center: location,
      zoom: 18,
      mapTypeId: google.maps.MapTypeId.SATELLITE
    });

    var infowindow = new google.maps.InfoWindow();
    this.chainAPI = new ChainAPI()
    this.streams  = this.chainAPI.getStreamsInfo();
    for (var i=0; i<this.streams.length; i++){
      marker = new google.maps.Marker({
            position: {lat: this.streams[i].latitude, lng: this.streams[i].longitude},
            icon:"static/img/unknow.png"
            })
      marker.name = this.streams[i].name
      //marker.position = [this.streams[i].latitude, this.streams[i].longitude]
      marker.setMap(map);
      markers.push(marker);

      google.maps.event.addListener(marker, 'click', function() {
        channel = this.name
        stream = 'http://deep-resenv.media.mit.edu:8000/'+this.name+'.ogg'
        $( '#audio_player'  ).attr('src', stream);
        $( '#audio_player'  ).load();
        $( '#audio_player' ).trigger('play');
        infowindow.open(map, this);
        content = '<div id="graph" style="padding:1px"></div>'
        content += "<center>GPS coord: (" + this.getPosition().lat() + ", " + this.getPosition().lng() + ')</center>';
        infowindow.setContent(content)
        });
      }
  }

  this.show = function(){
    $( "#detection_map" ).dialog("open");
  }

  initMap();
  this.show();

  socket.on('sys', function(msg){
      for (var i=0; i < msg.length; i ++){
        // Update all Marker icons
        for(var j=0; j < markers.length; j++)
          if (markers[j].name == "ch"+("0" + msg[i].chan).slice(-2)){
            markers[j].setIcon("static/img/"+msg[i].analysis.result[0]+".png");
          }

        // Update graph of the selected one
        if (channel == "ch"+("0" + msg[i].chan).slice(-2)){
          if (graph.name != channel){
            graph_div = document.getElementById("graph")
            graph = new Chart(graph_div, channel, null)
            // Ask the list of classifier outputs
            socket.emit('sys', JSON.stringify( {sys:{databases:{list:''},classifier: {list:''}}} ));
            }
            graph.updateHistory(msg[i].analysis)
          }
        }

      // Update the list of classifier when received
      if (msg.sys)
      if (msg.sys.classifier)
        if (msg.sys.classifier.list)
          graph.classifier_list = msg.sys.classifier.list;
    });
}
