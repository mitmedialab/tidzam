function Dataset (parent){
  this.parent = parent;
//console.log(parent.innerHTML)

  this.parent.innerHTML += '<div id="dialog-dataset" title="Training Dataset" style="width:100%; text-align:center;"></div>'+
  '<div id="dataset_popup" title="Output Training Dataset"><div style="text-align:center;" id="dataset_label"></div><div id="dataset_out" class="console"></div></div>';

  var dataset_html = 'Available databases: <select id="dataset_classe_selection"></select>';

  var popup = $('#dataset_popup').dialog({
    autoOpen: false,
    width:550,
    height:450
  });

  this.dialog = $( '#dialog-dataset' ).dialog({
    autoOpen: false,
    width: 690,
    modal: false,
    buttons: {
      Build: function(){
        $('#dataset_popup').attr('title','Building '+$( '#dataset_classe_selection option:selected' ).val()+' Dataset');
        $('#dataset_label').html("Processing ...");
        $('#dataset_out').html("");
        popup.dialog('open');
        socket.emit('sys', '{ "sys": { "datasets": { "build": "' + $( '#dataset_classe_selection option:selected' ).val() + '" } } }');
      }
    }
  });
  $( '#dialog-dataset' ).html(dataset_html);


  this.show = function(){
    socket.emit('sys', JSON.stringify({sys:{datasets:{list:''}}}));
    this.dialog.dialog('open');
  };



  socket.on('sys', function(msg){
    try {
      obj = JSON.parse(msg);
      if (! obj.sys) throw "not a sys object";

      if(obj.sys.datasets) {
        if (obj.sys.datasets.list){
          $( '#dataset_classe_selection' ).empty();
          for (var i=0; i < obj.sys.datasets.list.length; i++)
            $( '#dataset_classe_selection' ).append($("<option></option>").attr("value", obj.sys.datasets.list[i]).text(obj.sys.datasets.list[i]));
        }

        if (obj.sys.datasets.build && obj.sys.datasets.status)
          $('#dataset_label').html('Status for ' + obj.sys.datasets.build + ': ' + obj.sys.datasets.status);

        if (obj.sys.datasets.build && obj.sys.datasets.data)
          $('#dataset_out').html( $('#dataset_out').html() + obj.sys.datasets.data.replace(/(?:\r\n|\r|\n)/g,'<br>'));

      }
    }
    catch (err){
      console.log("WARNING: Dataset socket error " + err);
    }
  });
}
