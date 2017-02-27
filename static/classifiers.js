function Classifier (parent){
  this.parent = parent;
//console.log(parent.innerHTML)

  this.parent.innerHTML += '<div id="dialog-training" title="Training Classifier" style="width:100%; text-align:center;"></div>'+
  '<div id="training_classifier_popup" title="Output Training Classifier"><div style="text-align:center;" id="training_label"></div><div id="training_out" class="console"></div></div>';

  var training_html = 'Available databases: <select id="training_classe_selection"></select>';

  var classifier_popup = $('#training_classifier_popup').dialog({
    autoOpen: false,
    width:550,
    height:450
  });

  this.dialog = $( '#dialog-training' ).dialog({
    autoOpen: false,
    width: 690,
    modal: false,
    buttons: {
      Buildclassifier: function(){
        $('#training_classifier_popup').attr('title','Buildclassifiering '+$( '#training_classe_selection option:selected' ).val()+' Classifier');
        $('#training_label').html("Processing ...");
        $('#training_out').html("");
        classifier_popup.dialog('open');
        socket.emit('sys', '{ "sys": { "training": { "build": "' + $( '#training_classe_selection option:selected' ).val() + '" } } }');
      }
    }
  });
  $( '#dialog-training' ).html(training_html);


  this.show = function(){
    socket.emit('sys', JSON.stringify({sys:{training:{list:''}}}));
    this.dialog.dialog('open');
  };



  socket.on('sys', function(msg){
    try {
      obj = JSON.parse(msg);
      if (! obj.sys) throw "not a sys object";

      if(obj.sys.training) {
        if (obj.sys.training.list){
          $( '#training_classe_selection' ).empty();
          for (var i=0; i < obj.sys.training.list.length; i++)
            $( '#training_classe_selection' ).append($("<option></option>").attr("value", obj.sys.training.list[i]).text(obj.sys.training.list[i]));
        }
        if (obj.sys.training.build && obj.sys.training.status)
          $('#training_label').html('Status for ' + obj.sys.training.build + ': ' + obj.sys.training.status);

        if (obj.sys.training.build && obj.sys.training.data)
          $('#training_out').html( $('#training_out').html() + obj.sys.training.data.replace(/(?:\r\n|\r|\n)/g,'<br>'));

      }
    }
    catch (err){
      console.log("WARNING: Classifier socket error " + err);
    }
  });
}
