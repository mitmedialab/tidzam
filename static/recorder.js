function Recorder (parent){
  this.parent = parent;
  current_player = 'records';
//console.log(parent.innerHTML)

  this.parent.innerHTML +=
  '<div id="dialog-records" title="Neural Knownledge Unit Compilation" style="width:100%; text-align:center;"></div>'+

  '<div id="records_popup" title="Output Record Encoding">'+
    '<div style="text-align:center;" id="records_label_popup"></div>'+
    '<div id="records_out" class="console"></div></div>'+

  '<div id="dataset_popup" title="Output Dataset Construction">'+
    '<div style="text-align:center;" id="dataset_label_popup"></div>'+
    '<div id="dataset_out" class="console"></div></div>'+

  '<div id="training_classifier_popup" title="Output Trainer Learning">'+
    '<div style="text-align:center;" id="training_label_popup"></div>'+
    '<div id="training_out" class="console"></div></div>';

  var records_html =   '<audio id="audio_player_record">'+
  '<source src="/" type="audio/wav" />   '+
  '  </audio>  '+
  '<span id="records_label">records:</span> <select id="records_classe_selection"></select> (F1) -> <span id="dataset_label">dataset:</span> <select id="dataset_classe_selection"></select> (F2) -> <span id="training_label">trainer:</span> <select id="training_classe_selection"></select> (F3) -> NKU<br><br>'+
  '<img src="/record-fft" id="img_record_fft"><br>'+
  '<div id="records_parameters">'+
    '<div id="records_parameters_filter" style="text-center;">'+
      '<div id="slider-records_parameters_filter" style="width:636px;  margin-left: auto;  margin-right: auto;"></div>' +
      '<span id="span_record_fft"></span> <br> '+
      'RoI Range: '+
      '<input type="text" id="filter_low" value="50" maxlength="5" size="5"> - '+
      '<input type="text" id="filter_high" maxlength="5" value="15000" size="5"> Hz</div></div><br>'+
      '<div id="training_div">'+
        'Structure: '+'<input type type="input" id="training_structure" value="16">'+
        'Epoch: <input type="input" id="training_epoch" value="25" size="3">'+
        'Learning rate:<input type="text" id="training_learning_rate" value="0.01" size="5"></div>';

  var popup = $('#records_popup').dialog({
    autoOpen: false,
    width:550,
    height:400
  });

  var dataset_popup = $('#dataset_popup').dialog({
    autoOpen: false,
    width:550,
    height:450,
    close: null
  });

  var classifier_popup = $('#training_classifier_popup').dialog({
    autoOpen: false,
    width:550,
    height:450
  });

  this.dialog = $( '#dialog-records' ).dialog({
    autoOpen: false,
    width: 800,
    modal: false,
    dialogClass: 'dialog-records',
    buttons: {
      Delete: function(){
        socket.emit('sys', '{"sys":{"'+current_player+'":{"delete":"' +$( '#'+current_player+'_classe_selection option:selected' ).val() + '"}}}');
      },
      Listen: function(){
        $( '#audio_player_record' ).load();
        $( '#audio_player_record' ).trigger('play');
      },
      Prev: function(){
        socket.emit('sys', '{"sys":{"'+current_player+'":{"show":"' +$( '#'+current_player+'_classe_selection option:selected' ).val() + '", "do":"prev","filter_low":'+Math.ceil(($('#filter_low').val()-50)*0.042)+', "filter_high":'+Math.ceil((636- Math.ceil($('#filter_high').val()-50)*0.042))+'}}}');
      },
      Next: function(){
        socket.emit('sys', '{"sys":{"'+current_player+'":{"show":"' +$( '#'+current_player+'_classe_selection option:selected' ).val() + '", "do":"next","filter_low":'+Math.ceil(($('#filter_low').val()-50)*0.042)+', "filter_high":'+Math.ceil((636- Math.ceil($('#filter_high').val()-50)*0.042))+'}}}');
      },

      F1: function(){
        $('#records_label_popup').html("Processing ...");
        $('#records_out').html('');
        popup.dialog('open');
        socket.emit('sys', '{ "sys": { "records": { "build": "' + $( '#records_classe_selection option:selected' ).val() + '" } } }');
      },
      F2: function(){
        $('#dataset_label_popup').html("Processing ...");
        $('#dataset_out').html("");
        dataset_popup.dialog('open');
        socket.emit('sys', '{ "sys": { "dataset": { "build": "' + $( '#dataset_classe_selection option:selected' ).val() + '" } } }');
      },
      F3: function(){
        $('#training_label_popup').html("Processing ...");
        $('#training_out').html("");
        classifier_popup.dialog('open');
        socket.emit('sys', '{ "sys": { "training": { '+
        '"build": "' +               $( '#training_classe_selection option:selected' ).val() +
        '", "structure":"'+          $( '#training_structure' ).val()+
        '", "epoch":'+              $( '#training_epoch' ).val()+
        ', "learning_rate":'+       $( '#training_learning_rate' ).val()+
        ', "filter_low":'+Math.ceil(($('#filter_low').val()-50)*0.042)+
        ', "filter_high":'+Math.ceil((636- Math.ceil($('#filter_high').val()-50)*0.042))+' } } }');
      }
    }
  });

  $( '#records_classe_selection option:selected' ).on('change',function(){
    update();
  });

  $( '#dataset_classe_selection option:selected' ).on('change',function(){
    update();
  });



  this.update = function update(){
    socket.emit('sys', JSON.stringify({
      sys:{
        training:{list:''},
        dataset:{list:''},
        records:{
          list:'',
          show:'',
          do:'prev'
        }
      }
    }));
  }

  $( '#training_div' ).hide();
  $( '#dialog-records' ).html(records_html);

  this.show = function(classe){
    this.update();
    this.dialog.dialog('open');
  };

  $( "#slider-records_parameters_filter" ).slider({
      range: true,
      min: 50,
      max: 15000,
      values: [ 50, 15000 ],
      slide: function( event, ui ) {
          $( "#filter_low" ).val(ui.values[ 0 ] );
          $( "#filter_high" ).val(ui.values[ 1 ] );
      }
    });

    $( "#slider-records_parameters_filter" ).css("width:400px;");
    $( '#training_div' ).hide();




  $( '#records_classe_selection' ).on('change', function(ev, ui){
    current_player = 'records';
    if ($('.dialog-records .ui-button-text:contains(Listen)').is(':hidden'))
      $('.dialog-records .ui-button-text:contains(Listen)').show();

    $('.dialog-records .ui-button-text:contains(Prev)').show();
    $('.dialog-records .ui-button-text:contains(Next)').show();
    $('#img_record_fft').show();
    $( '#records_label' ).css('font-weight','bold');
    $( '#dataset_label' ).css('font-weight','normal');
    $( '#training_label' ).css('font-weight','normal');
    $( '#records_parameters_filter').show();

    $( '#training_div' ).hide();
  });

  $( '#dataset_classe_selection'  ).on('change', function(ev, ui){
    current_player = 'dataset';
    $('.dialog-records .ui-button-text:contains(Prev)').show();
    $('.dialog-records .ui-button-text:contains(Next)').show();
    $('#img_record_fft').show();
    $( '#records_parameters_filter').show();
    $( '#records_label' ).css('font-weight','normal');
    $( '#dataset_label' ).css('font-weight','bold');
    $( '#training_label' ).css('font-weight','normal');


    $('.dialog-records .ui-button-text:contains(Listen)').hide();
    $( '#training_div' ).hide();
  });

    $( '#training_classe_selection'  ).on('change', function(ev, ui){
      current_player = 'training';
      $( '#training_div' ).show();
      $('.dialog-records .ui-button-text:contains(Listen)').hide();
      $( '#records_parameters_filter').show();
      $( '#records_label' ).css('font-weight','normal');
      $( '#dataset_label' ).css('font-weight','normal');
      $( '#training_label' ).css('font-weight','bold');
    });



    function updateDatabaseNum (obj){
      setTimeout(function(){document.getElementById('img_record_fft').src = '/record-fft?time='+((new Date()).getTime()) }, 400);

      if (obj.type == 'records'){
        $ ( '#span_record_fft' ).html(obj.num + "("+obj.class+") /" +  + obj.size + " samples");
        $( '#audio_player_record' ).attr('src', '../' + obj.path +'?time='+((new Date()).getTime()));
      }
      else if(obj.type == 'datasets' || obj.type == 'training'){
        $ ( '#span_record_fft' ).html("Dataset: " + obj.dataset.file + "("+obj.dataset.size+") (yes:"+obj.dataset.size_yes+", no:"+obj.dataset.size_no+"): sample "+obj.dataset.num);
      }
    }

  socket.on('sys', function(msg){
    try {
      obj = JSON.parse(msg);
      if (! obj.sys) throw "not a sys object";

      if(obj.sys.records) {
        if (obj.sys.records.list){
          $( '#records_classe_selection' ).empty();
          $( '#records_classe_selection' ).append($("<option> </option>").attr("value", ""));
          for (var i=0; i < obj.sys.records.list.length; i++)
            $( '#records_classe_selection' ).append($("<option></option>").attr("value", obj.sys.records.list[i]).text(obj.sys.records.list[i]));
        }

        if (obj.sys.records.show)
          updateDatabaseNum (obj.sys.records.show);

        if (obj.sys.records.build && obj.sys.records.status)
          $('#records_label_popup').html('Dataset for ' + obj.sys.records.build + ': ' + obj.sys.records.status);

        if (obj.sys.records.build && obj.sys.records.data)
          $('#records_out').html( $('#records_out').html() + obj.sys.records.data.replace(/(?:\r\n|\r|\n)/g,'<br>'));
      }

      if(obj.sys.dataset) {
        if (obj.sys.dataset.show)
          updateDatabaseNum (obj.sys.dataset.show);

        if (obj.sys.dataset.list){
          $( '#dataset_classe_selection' ).empty();
          $( '#dataset_classe_selection' ).append($("<option> </option>").attr("value", ""));
          for (var i=0; i < obj.sys.dataset.list.length; i++)
            $( '#dataset_classe_selection' ).append($("<option></option>").attr("value", obj.sys.dataset.list[i]).text(obj.sys.dataset.list[i]));
        }

        if (obj.sys.dataset.build && obj.sys.dataset.status)
          $('#dataset_label_popup').html('Trainer for ' + obj.sys.dataset.build + ': ' + obj.sys.dataset.status);

        if (obj.sys.dataset.build && obj.sys.dataset.data)
          $('#dataset_out').html( $('#dataset_out').html() + obj.sys.dataset.data.replace(/(?:\r\n|\r|\n)/g,'<br>'));

      }

      if(obj.sys.training) {
        if (obj.sys.training.show)
          updateDatabaseNum (obj.sys.training.show);

        if (obj.sys.training.list){
          $( '#training_classe_selection' ).empty();
          $( '#training_classe_selection' ).append($("<option> </option>").attr("value", ""));
          for (var i=0; i < obj.sys.training.list.length; i++)
            $( '#training_classe_selection' ).append($("<option></option>").attr("value", obj.sys.training.list[i]).text(obj.sys.training.list[i]));
        }
        if (obj.sys.training.build && obj.sys.training.status)
          $('#training_label_popup').html('NKU for ' + obj.sys.training.build + ': ' + obj.sys.training.status);

        if (obj.sys.training.build && obj.sys.training.data)
          $('#training_out').html( $('#training_out').html() + obj.sys.training.data.replace(/(?:\r\n|\r|\n)/g,'<br>'));

      }
    }
    catch (err){
      console.log("WARNING: player socket error " + err);
    }
  });
}
