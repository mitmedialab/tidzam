function DetectionMap(parent){
  this.parent = parent
  this.channel = channel = null
  this.graph   = graph   = {name:null}
  this.current_time = current_time = ""
  chain = new ChainAPI()

  parent.innerHTML += '<div id="detection_map" title="Detection Map" width=100% text-align:center;"></div>'

  this.show = function(){
    $( "#detection_map" ).dialog("open");
  }

  $( "#detection_map" ).dialog({
    autoOpen: false,
    width: 1024,
    height: 1024,
    modal: false,
  });
  $( "#detection_map" ).html(
    '<div id="stats_loading_div" style="width:100%;height:230px;" class="loading_div"><span id="stats_loading_text">Loading</span></div>' +
    '<div id="stats_control">'+
    '<input type="button" id="stats_prev" value="<<"><input type="button" id="stats_next" value=">>">'+
    '<input type="button" id="stats_day" value="Day">'+
    '<input type="button" id="stats_month" value="Month">'+
    '<input type="button" id="stats_year" value="Year">'+
    '</div>'+
    '<div id="stats_area" style="height:190px;width:100%;margin-top:10px;"></div>'+
    '<audio controls id="audio_player" style="width:100%">'+
    '<source src="/chan0" type="audio/wav"></audio>'+
    '<div id="detection_map_area" style="height:600px;"></div>'+
    '<table style="width:100%;font-size:28px;margin-top:5px;margin-bottom:5px;"><tr>'+
    '<td width="40"><input type="image" src="static/img/time.png" id="source_btn"></td>'+
    '<td width="65"><input type="text" id="dateselector" style="width:150px;"></td>'+
    '<td><div id="timeselector" style="height:40px;text-align:center;">'+
    '<span id="time_label" style="width:60px;"></span></div></td>'+
    '</tr></table>'
  );
  $( "#detection_map" ).attr('style','font-size:12px;');

  /*************************************/
  /*            MAP CREATION           */
  /*************************************/
  var location = {lat: 41.8997582, lng: -70.571101};
  var map = null;
  var markers = Array()

    map = new google.maps.Map(document.getElementById('detection_map_area'), {
      center: location,
      zoom: 18,
      mapTypeId: google.maps.MapTypeId.SATELLITE
    });

    /*************************************/
    /*     TIDZAM OUTPUT VISUALIZATION   */
    /*************************************/

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

  /*************************************/
  /*        INPUT SOURCE CONTROL       */
  /*************************************/
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

  $( "#dateselector" ).datepicker();

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
      catch(err){console.log("No valid datetime.")}
    }
    else userIsSetting--;
    setTimeout(update_datetime,1000)
  }
  update_datetime()


  /*************************************/
  /*      STATISTIC VISUALIZATION      */
  /*************************************/
  $( "#stats_day" ).datepicker({
    dateFormat: 'yy-mm-dd'
  });
  $( "#stats_day" ).change(function(val){
    val = $( "#stats_day" ).val().split("-")
    load_statistics({"year":val[0],"month":val[1],"day":val[2]});
  })
  $('#stats_month').datepicker( {
    changeMonth: true,
    changeYear: true,
    showButtonPanel: true,
    dateFormat: 'yy-mm',
    onClose: function(dateText, inst) {
      $(this).datepicker('setDate', new Date(inst.selectedYear, inst.selectedMonth, 1));
    }
  });
  $( "#stats_month" ).change(function(val){
    val = $( "#stats_month" ).val().split("-");
    load_statistics({"year":val[0],"month":val[1]});
  })
  $('#stats_year').datepicker( {
    changeYear: true,
    showButtonPanel: true,
    dateFormat: 'yy',
    onClose: function(dateText, inst) {
      $(this).datepicker('setDate', new Date(inst.selectedYear, 1, 1));
    }
  });
  $( "#stats_year" ).change(function(val){
    val = $( "#stats_year" ).val().split("-");
    load_statistics({"year":val[0]});
  })

this.data_view = {}
function show_statistics(target, callback){
  var ready = false;
  var database = {}
  var options = {
    width: "100%",
    height: 190,
    legend: { position: 'top', maxLines: 3 },
    bar: { groupWidth: '75%' },
    isStacked: false
  };
  try{
    // Build a dictionnary
    for (var dev=0; dev < chain.list_devices.length; dev++){
      for (var sensor=0; sensor < chain.list_devices[dev].list_sensors.length; sensor++){
        sens = chain.list_devices[dev].list_sensors[sensor].title;
        chain.list_devices[dev].list_sensors[sensor].count = 0;
        for (var d=0; d < chain.list_devices[dev].list_sensors[sensor].data.length; d++){
          chain.list_devices[dev].list_sensors[sensor].count ++;

          if(!target.year)
          column = (new Date(chain.list_devices[dev].list_sensors[sensor].data[d].timestamp)).getYear();
          else if(!target.month)
          column = (new Date(chain.list_devices[dev].list_sensors[sensor].data[d].timestamp)).getMonth();
          else if(!target.day)
          column = (new Date(chain.list_devices[dev].list_sensors[sensor].data[d].timestamp)).getDate();
          else
          column = (new Date(chain.list_devices[dev].list_sensors[sensor].data[d].timestamp)).getHours();

          sens = chain.list_devices[dev].list_sensors[sensor].title;
          if ("undefined" === typeof database[column])
          database[column] = {}
          if ("undefined" === typeof database[column][sens])
          database[column][sens] = 0
          else database[column][sens]++;
        }
      }
    }
    ready = true;
    $("#stats_loading_text").text("");
  }
  catch(err){
    console.log("Data loading..." +err)
  }
  // Conert to database format
  var monthNames = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

// Build the sensor dictionnary
dict = []
for (var column in database)
for (var sensor in database[column]){
  found = false;
  for (var d in dict)
  if (dict[d] == sensor)
  found = true
  if (!found) dict.push(sensor)
}

data_formatted = []
header = ["Month"]
header = header.concat(dict)
i = 0;
for (var column in database){
  // Push the the period label in first position
  if(!target.month) data_formatted.push([monthNames[column]])
  else              data_formatted.push([column])
  for (var d in dict){
    if ( database[column][dict[d]] )
    data_formatted[i].push(database[column][dict[d]])
    else data_formatted[i].push(0);
  }
  i++;
}
data_formatted.unshift(header);
data_array = google.visualization.arrayToDataTable(data_formatted);
this.data_view = new google.visualization.DataView(data_array);
chart.draw(this.data_view, options);

if (!ready)
setTimeout(function(){
  show_statistics(target, callback);
},2000);
else if(callback)
callback("done");
}

circles = []
function map_draw_statistics(sensor_to_show){
  // Compute max value for normalization
  max_count = 0;
  for (var dev=0; dev < chain.list_devices.length; dev++)
    for (var sensor=0; sensor < chain.list_devices[dev].list_sensors.length; sensor++)
      if (sensor_title = chain.list_devices[dev].list_sensors[sensor].title == sensor_to_show)
      max_count = Math.max(max_count, chain.list_devices[dev].list_sensors[sensor].count)

  for (var dev=0; dev < chain.list_devices.length; dev++){
    dev_title = chain.list_devices[dev].title;
    // Looking for device location
    for (var m in markers)
      if (markers[m].name == "ch"+("0" + dev_title).slice(-2))
        break;

    for (var sensor=0; sensor < chain.list_devices[dev].list_sensors.length; sensor++){
        sensor_title = chain.list_devices[dev].list_sensors[sensor].title;

      // Looking for sensor circle of the device
      found = false
      for (var c in circles)
        if (circles[c].dev == dev && circles[c].sensor == sensor){
          found = true;
          circle = circles[c];
          break;
        }
      if (!found){
        var circle = new google.maps.Circle({
          strokeColor: '#FF0000',
          strokeOpacity: chain.list_devices[dev].list_sensors[sensor].count/max_count,
          strokeWeight: 2,
          fillColor: '#FF0000',
          fillOpacity: chain.list_devices[dev].list_sensors[sensor].count/max_count,
          center: markers[m].position,
          radius: 30
        });
        circle.dev = dev;
        circle.sensor = sensor;
        circles.push(circle);
      }
      // If this circle is of our sensor, show it else hide it
      if (sensor_title == sensor_to_show){
        console.log(dev_title + " " + sensor_title + " " + markers[m].position)
        circle.setMap(map);
      }

      else circle.setMap(null);

    }
  }
}


function load_statistics(conf){
  chain.getData(conf,function(msg){
    $("#stats_loading_text").text(msg);
  });

  $("#stats_loading_div").show();
  setTimeout(function(){
    show_statistics(conf, function(msg){
      $("#stats_loading_div").hide();
      map_draw_statistics("birds");
    });
  },1000);
}

// Load the data
var chart = new google.visualization.ColumnChart(document.getElementById("stats_area"));

// Listener to draw on the map detection density
google.visualization.events.addListener(chart, 'select', function () {
  var sel = chart.getSelection();
  if (sel.length > 0) {
    // if row is undefined, we clicked on the legend
    if (sel[0].row === null) {
      var col_name = this.data_view.getColumnLabel(sel[0].column);
      map_draw_statistics(col_name);
    }
  }
});

today = new Date();
load_statistics({"year":today.getFullYear(),"month":today.getMonth()+1,"day":today.getDate()});

  this.show();
}
