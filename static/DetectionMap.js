function DetectionMap(){
  me = this
  this.channel = channel = null
  this.graph   = graph   = {name:null}
  this.current_time = current_time = ""
  chain = new ChainAPI()

  me.statistic_conf = {}
  me.col_name = "";

  const livestream_io = io("//tidzam.media.mit.edu/",
        { path: '/livestream/socket.io'});

  const socket = io("//tidzam.media.mit.edu/",
      { path: '/socket.io' ,
       forceNew:true});

  /*************************************/
  /*            MAP CREATION           */
  /*************************************/
  var location = {lat: 41.901, lng: -70.571101};
  var map = null;
  var markers = Array()

    map = new google.maps.Map(document.getElementById('detection_map_area'), {
      center: location,
      zoom: 16,
      mapTypeId: google.maps.MapTypeId.SATELLITE
    });

    /*************************************/
    /*     TIDZAM OUTPUT VISUALIZATION   */
    /*************************************/

    var infowindow = new google.maps.InfoWindow();
    this.chainAPI = new ChainAPI()
    this.streams  = this.chainAPI.getStreamsInfo();
    for (var i=0; i<this.streams.length; i++){
      try {
        marker = new google.maps.Marker({
          position: {lat: this.streams[i].geoLocation.latitude, lng: this.streams[i].geoLocation.longitude},
          icon:{
            url: "static/img/unknown.png",
            scaledSize: new google.maps.Size(10)
          }
        })
        marker.name = this.streams[i].name
        marker.setMap(map);
        markers.push(marker);

        google.maps.event.addListener(marker, 'click', function() {
          channel = this.name
          stream = 'http://tidzam.media.mit.edu:8000/'+this.name.replace(":","-")+'.ogg'
          $( '#audio_player'  ).attr('src', stream);
          $( '#audio_player'  ).load();
          $( '#audio_player' ).trigger('play');
          infowindow.open(map, this);
          content = '<div id="graph" style="padding:1px"></div>'
          content += "<center>GPS coord: (" + this.getPosition().lat() + ", " + this.getPosition().lng() + ')</center>';
          infowindow.setContent(content)
        });
      }
      catch(err){
        console.log("Unable to load marker for " + this.streams[i].name)
      }
    }

  socket.on('sys', function(msg){
    for (var i=0; i < msg.length; i ++){
      if (msg[i].chan.indexOf("impoundment") != -1)
        current_time = msg[i].analysis.time;
      // Update all Marker icons
      for(var j=0; j < markers.length; j++)
      if (markers[j].name == msg[i].chan){
        markers[j].setIcon({
          url: "static/img/"+ msg[i].analysis.result[msg[i].analysis.result.length-1] +".png" ,
          scaledSize: new google.maps.Size(50, 31)
        });
      }

      // Update graph of the selected one
      if (channel == msg[i].chan){
        if (graph.name != channel){
          graph_div = document.getElementById("graph")
          graph = new Chart(graph_div, channel, null)
          socket.emit('sys', {sys:{classifier: {list:''}}} );
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
  livestream_io.on('sys', function(msg){
    //console.log(JSON.stringify(msg))
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
  setTimeout(function(){
    socket.emit('sys', JSON.stringify({"sys":{"time":""}}));
    livestream_io.emit('sys', JSON.stringify({"sys":{"database":""}}));
  },2000);


  $( "#source_btn" ).on("click", function(){
    var date = $( "#dateselector" ).val().split('/');
    var time = $( "#time_label" ).html();
    source = date[2]+"-"+date[0]+"-"+date[1]+"-"+time
    console.log("Change source : " + source);
    req = {
      "sys":{
        "loadsource":{
          "name":"impoundment",
          "url":"database_" + source,
          "permanent":false
        }
      }
    }
    livestream_io.emit('sys', JSON.stringify(req));
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
    dateFormat: 'yy-mm-dd',
    onClose: function(){
      $("#stats_month").val("Month");
      $("#stats_year").val("Year");
    }
  });
  $( "#stats_day" ).change(function(val){
    val = $( "#stats_day" ).val().split("-")
    load_statistics({"year":val[0],"month":val[1],"day":val[2]},"");
  })
  $('#stats_month').datepicker( {
    changeMonth: true,
    changeYear: true,
    showButtonPanel: true,
    dateFormat: 'yy-mm',
    beforeShow: function() { $('#hide').html('.ui-datepicker-calendar{display:none;}'); },
    onClose: function(dateText, inst) {
      $(this).datepicker('setDate', new Date(inst.selectedYear, inst.selectedMonth, 1));
      setTimeout(function(){$('#hide').html('');},300);
      $("#stats_day").val("Day");
      $("#stats_year").val("Year");
      val = $( "#stats_month" ).val().split("-");
      load_statistics({"year":val[0],"month":val[1]},"");
    }
  });

  $('#stats_year').datepicker( {
    changeYear: true,
    showButtonPanel: true,
    dateFormat: 'yy',
    beforeShow: function() {
      $('#hide').html('.ui-datepicker-calendar{display:none;}');
    },
    onClose: function(dateText, inst) {
      $(this).datepicker('setDate', new Date(inst.selectedYear, 1, 1));
      setTimeout(function(){ $('#hide').html(''); },300);
      $("#stats_day").val("Day");
      $("#stats_month").val("Month");

      val = $( "#stats_year" ).val().split("-");
      load_statistics({"year":val[0]},"");
    }
  });

this.data_view = {}
colors = ["blue", "red", "orange", "green", "purple", "yellow", "brown", "black", "gray"]
function show_statistics(target, subclasse, callback){
  var ready = false;
  var database = {}
  var options = {
    title:'Sensors detections distribution',
    width: $(window).width()*0.8,
    height: $(window).height()*0.2,
    legend: { position: 'top', maxLines: 3 },
    bar: { groupWidth: '75%' },
    isStacked: false,
    colors:colors,
    vAxis: {}
  };

 if (subclasse == "birds")
	options.vAxis.scaleType = 'log';

  try{
    // Build a dictionnary
    for (var dev=0; dev < chain.list_devices.length; dev++){
      for (var sensor=0; sensor < chain.list_devices[dev].list_sensors.length; sensor++){

        if (subclasse == ""){
          // If it is a primary classe
          if (chain.list_devices[dev].list_sensors[sensor].title.indexOf("-") == -1)
            sens = chain.list_devices[dev].list_sensors[sensor].title;
          // Get primary classe name
          else sens = chain.list_devices[dev].list_sensors[sensor].title.split("-")[0]
        }
        // If this sensor is not a subclasse, go to the next
        else if (chain.list_devices[dev].list_sensors[sensor].title.indexOf(subclasse) == -1)
          continue
        else sens = chain.list_devices[dev].list_sensors[sensor].title;

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

          if ("undefined" === typeof database[column])          database[column] = {}
          if ("undefined" === typeof database[column][sens])    database[column][sens] = 0
          else database[column][sens]++;
        }
      }
    }
    ready = true;
    $("#stats_loading_text").text("");
    $("#classe_picture").attr("src","static/img/" + (subclasse != "" ? subclasse : "tidzam") + ".png");
  }
  catch(err){
    console.log("Data loading...")
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
  // Column label
  if("undefined" != typeof target.day) {
    if (column == 0)       data_formatted.push(["12 am"])
    else if (column <= 11)  data_formatted.push([column+" am"])
    else if (column == 12) data_formatted.push(["12 pm"])
    else                   data_formatted.push([column%12+" pm"])
  }
  else if("undefined" != typeof target.month)    data_formatted.push([monthNames[parseInt(target.month)-1]+" "+column])
  else if("undefined" != typeof target.year)     data_formatted.push([monthNames[column]])
  else                                           data_formatted.push([column])


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
  show_statistics(target, subclasse, callback);
},2000);
else if(callback)
callback("done");
}

circles = []
function map_draw(sensor_to_show, color){
  // Compute max value for normalization
  max_count = 0;
  max_count_sensor = 0;
  for (var dev=0; dev < chain.list_devices.length; dev++)
    for (var sensor=0; sensor < chain.list_devices[dev].list_sensors.length; sensor++){
      max_count = Math.max(max_count, chain.list_devices[dev].list_sensors[sensor].count)
      if (sensor_title = chain.list_devices[dev].list_sensors[sensor].title == sensor_to_show)
      max_count_sensor = Math.max(max_count_sensor, chain.list_devices[dev].list_sensors[sensor].count)
    }

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
        var circle = new google.maps.Circle();
        circle.dev = dev;
        circle.sensor = sensor;
        circles.push(circle);
      }

      circle.setOptions({
        strokeColor: color,
        strokeOpacity: Math.max(chain.list_devices[dev].list_sensors[sensor].count/max_count,0.2),
        strokeWeight: 2,
        fillColor: color,
        fillOpacity: Math.max(chain.list_devices[dev].list_sensors[sensor].count/max_count,0.2),
        center: markers[m].position,
        radius: (chain.list_devices[dev].list_sensors[sensor].count/max_count_sensor)*30
      });
      // If this circle is of our sensor, show it else hide it
      if (sensor_title == sensor_to_show)   circle.setMap(map);
      else                                  circle.setMap(null);

    }
  }
}

function load_statistics(conf, subclasse){
  me.statistic_conf = conf;
  $("#stats_loading_div").show();
  chain.getData(conf,function(msg){
    $("#stats_loading_text").text(msg);
  });
  setTimeout(function(){
    show_statistics(conf, subclasse, function(msg){
      $("#stats_loading_div").hide();
      for(var i=0; i < this.data_view.getNumberOfColumns(); i++)
        if (this.data_view.getColumnLabel(i) == "birds")
          break;
      map_draw("birds", colors[i-1]);
    });
  },1000);
}

// Load the data
var chart = new google.visualization.ColumnChart(document.getElementById("stats_area"));

  this.statistic_previous = function(){
    var text  =   $("#statistic_selector").text()
    text      = text.split(" > ")
    text.shift()
    if (text.length > 0)   text.pop()
    $("#statistic_selector").text("tidzam > " + text.join(" > "))

    text = text.join("-")
    show_statistics(me.statistic_conf, text, function(msg){
      $("#stats_loading_div").hide();
      map_draw("", colors[i-1]);
    });
  };

// Listener to draw on the map detection density
google.visualization.events.addListener(chart, 'select', function () {
  var sel = chart.getSelection();
  if (sel.length > 0) {
      var col_name = this.data_view.getColumnLabel(sel[0].column);
      me.col_name = col_name
      $("#statistic_selector").text("tidzam > " + col_name.replace("-", " > "))

      for(var i=0; i < this.data_view.getNumberOfColumns(); i++)
        if (this.data_view.getColumnLabel(i) == col_name)
          break;

      show_statistics(me.statistic_conf, col_name, function(msg){
        $("#stats_loading_div").hide();
        map_draw(col_name, colors[i-1]);
      });
  }
});

$(window).resize(function(){
  show_statistics(me.statistic_conf, me.col_name,function(msg){
  });
});

today = new Date();
load_statistics({"year":today.getFullYear(),"month":today.getMonth()+1,"day":today.getDate()}, "");
}
