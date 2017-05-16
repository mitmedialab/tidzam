function Chart (parent, name, classifier_list) {
  this.name	= name;
  this.classifier_list = null;

  parent = this.parent = parent;
  console.log("New Channel " + this.name);

  //div_charts = document.getElementById(parent.dialog_chart_name);
  div_charts = parent;

  var div = document.createElement('div');
  div.id = 'plot-'+this.name;
  div.class = 'plot';
  div_charts.appendChild(div);

  var data = this.data 	= new google.visualization.DataTable();
  this.data.addColumn('string', '');
  var chart = this.chart = new google.charts.Line(document.getElementById('plot-'+this.name));
  chart.chan = this.name;
  this.options 	= {
    'height':250,
    'width':550,
    chart: {
      title: 'Audio Channel ' + this.name,
      subtitle: 'General classifiers'
    },
    axes: 	{
      x: {0: {side: 'bottom'}}
    },
    series: {
            0: { color: 'green' },
            1: { color: 'yellow' },
            2: { color: 'orange' },
            3: { color: 'blue' },
            4: { color: 'purple' },
            5: { color: 'red' },
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
    legend:"top"
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
      var result = obj.time + '\n';
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
