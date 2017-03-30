function DetectionMap(parent){
  this.parent = parent
  this.channel = channel = null
  this.graph   = graph   = {name:null}
  this.current_time = current_time = ""

  parent.innerHTML += '<div id="detection_map" title="Detection Map" width=100% text-align:center;"></div>'

    $( "#detection_map" ).dialog({
      autoOpen: false,
      width: 1024,
      height: 890,
      modal: false,
    });
    $( "#detection_map" ).html(
      '<audio controls id="audio_player" style="width:100%">'+
      '<source src="/chan0" type="audio/wav"></audio>'+
      '<div id="detection_map_area" style="height:750px;"></div>'+
      '<table style="width:100%;font-size:28px;margin-top:5px;margin-bottom:5px;"><tr>'+
        '<td width="40"><input type="image" src="static/img/time.png" id="source_btn"></td>'+
        '<td width="65"><input type="text" id="dateselector" style="width:150px;"></td>'+
        '<td><div id="timeselector" style="height:40px;text-align:center;">'+
            '<span id="time_label" style="width:60px;"></span></div></td>'+
      '</tr></table>'
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
        current_time = msg[i].analysis.time;
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

    /*
    Source interface control
    */

      userIsSetting = 0

      $( "#timeselector" ).slider({range: false,
            max: 24 * 60 * 60,
            slide: function(event, ui) {
              userIsSetting = 20;
              var hours   = Math.floor(ui.value / 3600);
              var minutes = Math.floor((ui.value - (hours * 3600)) / 60);
              var seconds = ui.value - (hours * 3600) - (minutes * 60);
               $( "#time_label" ).text(hours+":"+minutes+":"+seconds)
            }
        });
      socket.emit('sys', JSON.stringify({"sys":{"time":""}}));
      socket.emit('sys', JSON.stringify({"sys":{"database":""}}));
      socket.on('sys', function(msg){
        if (!msg.sys)
          return

        if(msg.sys.database){
          var eventDates = {};
          for (var i=0;i<msg.sys.database.length; i++){
              f = msg.sys.database[i]
              start = f[0].split("-");
              start_date = new Date(start[0],start[1]-1,start[2])
              end   = f[1].split("-");
              end_date = new Date(end[0],end[1]-1,end[2])
              for (var d = start_date; d <= end_date; d.setDate(d.getDate() + 1))
                eventDates[d] = new Date(d).toString();
          }
          $( "#dateselector" ).datepicker({
            beforeShowDay: function(date) {
              userIsSetting = 20
              var highlight = eventDates[date];
              if (highlight) return [true, "event", highlight];
              else           return [true, '', ''];
            }
            });
          }
        });

      $( "#source_btn" ).on("click", function(){
          var date = $( "#dateselector" ).val().split('/');
          var time = $( "#time_label" ).html();
          source = date[2]+"-"+date[0]+"-"+date[1]+"T"+time
          console.log("Change source : " + source);
          req = {
            "sys":{
              "source":source
            }
          }
          socket.emit('sys', JSON.stringify(req));
        });


        function update_datetime(){
          if (!userIsSetting){
            try{
              datetime = current_time.split("T")
              date = datetime[0].split("-")
              time = datetime[1].split(".")[0]
              $( "#dateselector" ).val(date[1]+"/"+date[2]+"/"+date[0])
              $( "#time_label" ).text(time)
              time = time.split(":")
              $("#timeselector").slider('value',(time[0]*3600) + (time[1]*60) + parseInt(time[2]));
            }
            catch(err){console.log("No valid datetime." + err)}
          }
          else userIsSetting--;
          setTimeout(update_datetime,1000)
        }
        update_datetime()

}
