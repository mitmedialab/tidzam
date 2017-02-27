function ClassifierChart(parent, names){
  this.selectedClass = "";

  var plots = this.plots = new Array();
  this.dialog_chart_name = "dialog-neural-outputs";
  parent.innerHTML +=
  '<div id="'+  this.dialog_chart_name +'" title="Classifier Management"></div>'+
  '<div id="dialog-info" title="Details" ></div>' +
  '<div id="dialog-info-img" title="Hidden Layers" ></div>' +
  '<div id="dialog-database-new" title="Record database name">'+
  '<input type="text" id="dialog-database-new-input">'+
  '<input type="button" id="dialog-database-new-button" value="Create"></div>';

  var dialog_info = this.dialog_info =  $( "#dialog-info" ).dialog({
    autoOpen: false,
    width:800,
    modal: false,
  });


  var dialog_info_img = this.dialog_info =  $( "#dialog-info-img" ).dialog({
    autoOpen: false,
    width:600,
    modal: false,
    });

  var dialog_info_database_new = this.dialog_info_database_new =  $( "#dialog-database-new" ).dialog({
    autoOpen: false,
    width:350,
    modal: true,
  });

  $( '#dialog-database-new-button' ).click(function(){
    for (i=0; i < plots.length; i++){
      plots[i].data.addColumn('number', '?' + $( '#dialog-database-new-input' ).val());
    }
    $ ('#dialog-database-new').dialog('close');
  });

  function UrlExists(url)
  {
      var http = new XMLHttpRequest();
      http.open('HEAD', url, false);
      http.send();
      return http.status!=404;
  }

  this.dialog_info.update = function(conf){
    var print = "<table style=\"float:left; width:100%;\" class=\"table_info\">"+
      "<tr style=\"font-weight:bold;text-align:center;\"><td>Classifiers</td><td>Under Estimation</td><td>Over Estimation</td> <td>Structure</td> <td>RoI</td> <td>Date</td></tr>";
    for (i=0; i < conf.classifiers.length; i++)
    print += "<tr><td><a href='#?classifier="+conf.classifiers[i].name+"'  class='link_classifier_img'>"+conf.classifiers[i].name + "</a></td>"+
      "<td>" + conf.classifiers[i].errors[0] + "</td>"+
      "<td>" + conf.classifiers[i].errors[1] + "</td>"+
      "<td>" + conf.classifiers[i].structure + "</td>"+
      "<td>" + conf.classifiers[i].roi + "</td>"+
      "<td>"+conf.classifiers[i].date +"</td></tr>";
    print += "</table>";
    print += "<table class=\"table_info\">";
    print += "<tr><td style=\"font-weight:bold;\">Analysis frequency: </td><td> "+conf.frequency*1000+" ms</td></tr>";
    print += "<tr><td style=\"font-weight:bold;\">Filter Low Band: </td><td> "+ (conf.filter.low / 1000) +" KHz</td></tr>";
    print += "<tr><td style=\"font-weight:bold;\">Filter High Band: </td><td> "+ (conf.filter.high / 1000) +" KHz</td></tr>";
    print += "</table>";
    $( "#dialog-info" ).html(print);

    $( '.link_classifier_img' ).on('click',  function(){
      var classifier = this.href.substr(this.href.indexOf('classifier=')+11);
      var html = '';
      for(var i=1; i < 10; i++)
        if (UrlExists('/data/classifiers/classifier-'+classifier+'-L'+i+'.png'))
          html += '<img src="/data/classifiers/classifier-' + classifier + '-L' + i + '.png" width="600">';
      $( '#dialog-info-img ').html(html).dialog('open');
    });

  };


//.OnClick='$(\"#dialog-info-img\").data(\"classifier\",\""+conf.classifiers[i].name+"\").dialog(\"open\");'

  var dialog = this.dialog =   $( '#dialog-neural-outputs'  ).dialog({
    autoOpen: false,
    width:800,
    modal: false,
    dialogClass: 'dialog-neural-outputs',
    buttons: {
      NEW: function(){
        $ ('#dialog-database-new').dialog('open');
      },
      YES: function(){
        cl = $('.dialog-neural-outputs .ui-button-text:contains(YES)').text().substr(4);
        socket.emit('sys', JSON.stringify( {sys:{sample: cl, classe:"+"}} ));
      },
      NO: function(){
        cl = $('.dialog-neural-outputs .ui-button-text:contains(NO)').text().substr(3);
        socket.emit('sys', JSON.stringify( {sys:{sample: cl, classe:"-"}} ));
      },
      On_Off: function(){
        cl = $('.dialog-neural-outputs .ui-button-text:contains(On_Off)').text().substr(7);
        socket.emit('sys', JSON.stringify( {sys:{classifier:{toggle:cl}}} ));
      },
      Information: function(){
        dialog_info.dialog("open");
      }
    }
  });
  $('.dialog-neural-outputs .ui-button-text:contains(On_Off)').text("On_Off");
  $('.dialog-neural-outputs .ui-button-text:contains(NEW)').text("New Database");
  $('.dialog-neural-outputs .ui-button-text:contains(YES)').button().hide();
  $('.dialog-neural-outputs .ui-button-text:contains(NO)').button().hide();
  $('.dialog-neural-outputs .ui-button-text:contains(On_Off)').button().hide();

  this.updateSelectedClass = function(chan, item){
    // If we click on a dataset which is not classifier
    if(item[0] == '!')
      item = item.substr(1);

    if(item[0] != '?'){
      $('.dialog-neural-outputs .ui-button-text:contains(On_Off)').text('On_Off '  + item);
      $('.dialog-neural-outputs .ui-button-text:contains(On_Off)').button().show();
    }
    else  {
      item = item.substr(1);
      $('.dialog-neural-outputs .ui-button-text:contains(On_Off)').button().hide();
    }

    this.selectedClass = item;

    $('.dialog-neural-outputs .ui-button-text:contains(YES)').text('YES '  + this.selectedClass + '('+chan+')');
    $('.dialog-neural-outputs .ui-button-text:contains(YES)').button().show();

    $('.dialog-neural-outputs .ui-button-text:contains(NO)').text('NO ' + this.selectedClass + '('+chan+')');
    $('.dialog-neural-outputs .ui-button-text:contains(NO)').button().show();
  }

  this.show = function(){
    this.dialog.dialog('open');
    socket.emit('sys', JSON.stringify( {sys:{databases:{list:''},classifier: {list:''}}} ));
  }

  this.process = function(json){
    if (json.classifiers)
    this.dialog_info.update(json);

    if (json.analysis){

      // Else simple data for one channel
      var found = false;
      for (i=0; i < plots.length; i++)
      if(plots[i].name == json.chan){
        found = true;
        break;
      }
      if (!found)
        plots.push(new Chart(this, json.chan, this.classifier_list));
      plots[i].updateHistory(json.analysis);
    }

    if (json.sys){
      if (json.sys.classifier)
      if (json.sys.classifier.list)
      for (i=0; i < this.plots.length; i++)
        this.plots[i].classifier_list = json.sys.classifier.list;

    }
  }
}


/****************************************
*
/***************************************/
function Chart (parent, name, classifier_list) {
  this.name	= name;
  this.classifier_list = null;

  parent = this.parent = parent;
  console.log("New Channel " + this.name);

  div_charts = document.getElementById(parent.dialog_chart_name);
  var div = document.createElement('div');
  div.id = 'plot-'+this.name;
  div.class = 'plot';
  div_charts.appendChild(div);

  var data = this.data 	= new google.visualization.DataTable();
  this.data.addColumn('string', '');
  var chart = this.chart = new google.charts.Line(document.getElementById('plot-'+this.name));
  chart.chan = this.name;
  this.options 	= {
    'height':150,
    'width':'100%',
    chart: {
      title: 'Stream Channel ' + this.name,
      subtitle: 'Deep Belief Network Classifiers'
    },
    axes: 	{
      x: {0: {side: 'bottom'}}
    },
    vAxis: {
      viewWindowMode:'explicit',
      format:"#%",
      viewWindow: {
        max:1,
        min:0
      }
    },
    displayAnnotations: true,
    legend:{textStyle:{fontSize:12, fontName:'TimesNewRoman'}}
  };

  google.visualization.events.addListener(chart, 'select', function () {
    var sel = chart.getSelection();
    if (sel.length > 0) {
      // if row is undefined, we clicked on the legend
      if (sel[0].row === null) {
        var col_name = data.getColumnLabel(sel[0].column);
        parent.updateSelectedClass(chart.chan, col_name);
      }
    }
  });

  this.num = 0;
  this.updateHistory = function(obj){
    try {
      var tmp = new Array();

      // Add column of labelled results
      var result = new String();
      for (var key in obj.result){
        result += obj.result[key] + '\n';
      }
      tmp.push(result);

      if (this.classifier_list){
        for (i=0; i < this.classifier_list.length; i++){
          found = false;
          for (j=1; j < this.data.getNumberOfColumns(); j++){
            n  = this.data.getColumnLabel(j)[0]=='!' || this.data.getColumnLabel(j)[0]=='?' ?this.data.getColumnLabel(j).substr(1): this.data.getColumnLabel(j);
            if ('classifier-' +  n + '.nn' == this.classifier_list[i]){

              running = false;
              for (var key in obj.predicitions)
              if(n == key){
                running = true;
                break;
              }
              found = true;
              break;
            }
          }
          if(found){
          name = this.classifier_list[i].substr(11, this.classifier_list[i].indexOf('.nn') - 11);

          if (running) this.data.setColumnLabel(j, name);
          else         this.data.setColumnLabel(j,'!' + name);
          }
          if (!found){
            name = this.classifier_list[i].substr(11, this.classifier_list[i].indexOf('.nn') - 11);
            this.data.addColumn('number', name);
          }
        }

      }

      // Build row according to the order of column
      for (j=1; j < this.data.getNumberOfColumns(); j++){
        found = false;
        for (var key in obj.predicitions)
        if(this.data.getColumnLabel(j) == key){
          tmp.push(obj.predicitions[key] );
          found = true;
          break;
        }

        if (!found)
        tmp.push(0)
      }


      this.data.addRows([tmp]);

      if(this.data.getNumberOfRows() > 20)
      this.data.removeRow(0);
      this.chart.draw(this.data, google.charts.Line.convertOptions(this.options));
    }
    catch(err){
      console.log("[ERROR] Unable to parse JSON data: " + err);
    }
  }
}
