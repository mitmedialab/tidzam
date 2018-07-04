function Chart (parent, name, classifier_list) {
  this.name	= name;
  $("#graph").append( '<div id="plot-'+this.name+'" class="plot"> </div>' );

  // Prepare tje datatable and add legend field
  var data = new google.visualization.DataTable();
  data.addColumn('string', '');

  var chart = this.chart = new google.charts.Line(document.getElementById('plot-'+this.name));
  chart.chan = this.name;

  width = $( window ).width() < 992 ? $( window ).width() : 550;
  height = (width == $( window ).width()) ?$( window ).height() : 200;
  this.options 	= {
    'height':height,
    'width':width,
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
    displayAnnotations: false,
    legend: {position: 'none'}
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
          for (j=1; j < data.getNumberOfColumns(); j++){
            n  = data.getColumnLabel(j)[0]=='!' || data.getColumnLabel(j)[0]=='?' ?data.getColumnLabel(j).substr(1): data.getColumnLabel(j);
            if ( n == this.classifier_list[i]){

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
          name = this.classifier_list[i];

          if (running) data.setColumnLabel(j, name);
          else         data.setColumnLabel(j,'!' + name);
          }
          if (!found){
            name = this.classifier_list[i];
            data.addColumn('number', name);
          }
        }

      }

      // Build row according to the order of column
      for (j=1; j < data.getNumberOfColumns(); j++){
        found = false;
        for (var key in obj.predicitions)
        if(data.getColumnLabel(j) == key){
          tmp.push(obj.predicitions[key] );
          found = true;
          break;
        }

        if (!found)
        tmp.push(0)
      }


      data.addRows([tmp]);
      if(data.getNumberOfRows() > 20)
        data.removeRow(0);

      this.chart.draw(data, google.charts.Line.convertOptions(this.options));
    }
    catch(err){
      console.log("[ERROR] Unable to parse JSON data: " + err);
    }
  }
}
