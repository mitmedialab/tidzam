

function DatabaseManager(div_manager, tidzam_url){
  const socket_io = io("//tidzam.media.mit.edu/",
        { path: '/database/socket.io', 'forceNew':true});
  manager           = this
  this.classe       = "unchecked"
  this.limit        = 5
  this.start        = 0
  sample_count      = 0
  selector_position = 0

  //---------------------------- KEYBOARD INTERFACE
  $.getScript( "lib/keymaster/keymaster.js", function( data, textStatus, jqxhr ) {
    console.log( "keymaster librairy loaded." );

    function selector_next(){
      $('#'+selector_position).removeClass("tr_selected")
      found = false
      $('#div_manager_table tbody').children('tr').each(function(i) {
        if (i == 0)                        first = this.id
        if (selector_position == -1)       selector_position = this.id
        else if (selector_position == this.id) {
          selector_position = -1
          found = true
          }
          console.log(this.id)
        });
     if (!found) selector_position = first
     $('#'+selector_position).addClass("tr_selected")
   }
    key('down',selector_next);

    key('up', function(){
      $('#'+selector_position).removeClass("tr_selected")
      prev = 0
      $('#div_manager_table tbody').children('tr').each(function(i) {
        if (selector_position == this.id) {
          if (i == 0) selector_position = this.id
          else        selector_position = prev;
        }
        else                              prev = this.id
      });
      $('#'+selector_position).addClass("tr_selected")
    });

    key('space', function(){
      $("#database_audio_"+selector_position).trigger("play");
    });

    key('e', function(){
      $("#database_btn_extract_"+selector_position).trigger("click");
      $('#'+selector_position).addClass("tr_extracted")
    });

    key('d', function(){
      $("#database_btn_done_"+selector_position).trigger("click");
      selector_position = -1
      selector_next();
    });

    //$("#database_btn_done_"+sample_count)

  });
    //---------------------------- END KEYBOARD INTERFACE

  table_header = '<input type="button" id="btn_prev" value="Previous">'
  table_header += '<input type="button" id="btn_random" value="Random">'
  table_header += '<input type="button" id="btn_next" value="Next">'
  table_header += '<select id="select_classe"><option>unchecked</option></select>'
  table_header += '<select id="select_limit"><option>1</option><option selected>5</option><option>20</option></select><br>'
  table_header += 'Controls: "<"up\>\<down\> Selection \<space\> Play \<e\> Extract \<d\> Delete'
  table_header += '<table id="div_manager_table" cellspacing="0" cellpadding="0"><tbody>';
  table_header += '</tbody></table>'
  $("#div_manager").html(table_header);


  // ******************************** LIST CONTROLER
  this.request_samples = function(limit){
    req = {"samples_list":{
        "classe":manager.classe,
        "limit":limit?limit:manager.limit,
        "start":manager.start,
        }
      };
      console.log(req);
      socket_io.emit("DatabaseManager",req);
    }
    this.request_samples();

  $("#btn_prev").on("click", function(){
    $("#div_manager_table tbody").empty();
    manager.start -= manager.limit;
    if (manager.start < 0) manager.start = 0;
    manager.request_samples();
  })

  $("#btn_random").on("click", function(){
    $("#div_manager_table tbody").empty();
    manager.start = -1;
    manager.request_samples();
  })

  $("#btn_next").on("click", function(){
    $("#div_manager_table tbody").empty();
    manager.start += manager.limit;
    manager.request_samples();
  });

  $("#select_limit").change(function(){
    manager.limit = $("#select_limit").val();
    $("#div_manager_table tbody").empty();
    manager.request_samples();
  });

  $("#select_classe").change(function(){
    manager.classe = $("#select_classe").val();
    $("#div_manager_table tbody").empty();
    manager.request_samples();
  });

  socket_io.on('DatabaseManager',function(obj){
    if (obj.samples_list){
      for (var i=0; i < obj.samples_list.length; i++)
        manager.add_sample(obj.samples_list[i]);

      $('#'+selector_position).addClass("tr_selected")
      socket_io.emit("DatabaseManager",{"classes_list":{}});
    }

    if (obj.classes_list)
      for (classe in obj.classes_list){
        $(".database_select_classe_extract").append("<option>"+obj.classes_list[classe]+"</option>")
        $("#select_classe").append("<option>"+obj.classes_list[classe]+"</option>")
      }
      selects = $(".database_select_classe_extract")
      for (select in selects){
        if (selects[select].id){
        sample_id        = selects[select].id.split("_");
        sample_id        = sample_id[sample_id.length-1];
        $("#database_select_classe_extract_"+sample_id).val( $("#database_title_"+sample_id).text() );
        }
      }
    });


  this.add_sample = function(sample){
    img = []
    padding = 4 - sample.fft.size[1] % 4;
    for (var i=0; i < sample.fft.size[0]*sample.fft.size[1]; i++){
      color = 255 - Math.ceil(sample.fft.data[i] * 255)
      color = color > 250 ? 255 : 0
      img.push(color)
      if (i % sample.fft.size[1] == 0 && i > 0)
        for (var j=0 ; j < padding; j++)
          img.push(0);
    }
    // Extract information from filename
    path = sample.path.split("/")
    if (path[path.length-2] == "unchecked"){
      prediction = path[path.length-1].split("']")[0]
      prediction = prediction.split("['")[1]
      }
    else prediction = path[path.length-2]
    if (prediction)
      prediction = prediction.split("(")[0]

    // Get info on directory container filename
    source = path[path.length-2].split(")")[0]
    source = source.split("(")
    if (source.length <= 1) source = "";
    else source = source[1]
    source_tmp = path[path.length-1].split(")")[0]
    source_tmp = source_tmp.split("(")
    if (source_tmp.length <= 1) source_tmp = "unknown";
    else source_tmp = source_tmp[1]
    if (source != "")    source += " / " + source_tmp
    else source = source_tmp

    date = path[path.length-1].split("_")
    if (date.length <= 1) date = "unknown"
    else date = date[date.length-1].split(".")[0]


    sample_html = '<tr class="tr_'+sample_count+'" id="'+sample_count+'"><td><div id="database_img_'+sample_count+'" class="container"><div class="database_audio_div" id="database_audio_div_'+sample_count+'" ></div></div>';
    sample_html += '<audio controls id="database_audio_'+sample_count+'"><source src="'+tidzam_url+"database/"+sample.path+'" type="audio/ogg"></audio></td>';
    sample_html += '<td style="width:100%;">';
    sample_html += 'Classe: <span class="database_title" id="database_title_'+sample_count+'">'+prediction+'</span><br>';
    sample_html += 'Source: <span class="database_title_source">'+source+'</span><br>';
    sample_html += 'Date: <span class="database_title_date">'+date+'</span><br>';
    sample_html += 'Sample Rate: <span class="database_title_samplerate">'+sample["samplerate"]+'</span><br><br>';
    sample_html += 'Playing: <span id="database_extract_span_'+sample_count+'">0</span> seconds<br>';
    if (path[path.length-2] == "unchecked"){
      sample_html += '<select class="database_select_classe_extract" id="database_select_classe_extract_'+sample_count+'"></select><br>';
      sample_html += '<input type="button" id="database_btn_extract_'+sample_count+'" value="extract">';
      sample_html += '<input type="button" id="database_btn_done_'+sample_count+'" value="Delete">';
    }
    sample_html += '</td></tr>';
    $("#div_manager_table tbody").append(sample_html);

    // Add the spectrogram picture
    $("#database_img_"+sample_count).append( drawArray(img, 8, sample.fft.size) )


    // ******************************** EXTRACTION CONTROLER
    $("#database_btn_extract_"+sample_count).on("click", function(){
      sample_id = this.id.split("_");
      sample_id = sample_id[sample_id.length-1];

      path      = $("#database_audio_"+sample_id+" source").attr("src");
      path      = "unchecked/" + path.split("unchecked/")[1];
      classe    = $("#database_select_classe_extract_"+sample_id).val();
      time      = $("#database_audio_"+sample_id)[0].currentTime;
      duration  = $("#database_audio_"+sample_id)[0].duration;
      time      = time < 0.5 ? 0: time > duration-0.5 ? duration-0.5: time;

      if (!classe){
        console.log("ERROR: A classe must be specified for an extraction.")
        return
      }

      socket_io.emit("DatabaseManager",{"extract":{
          "path":path,
          "time":time,
          "classe":classe,
          "length":0.5
        }
      });
    });

    $("#database_btn_done_"+sample_count).on("click", function(){
      sample_id   = this.id.split("_")
      sample_id   = sample_id[sample_id.length-1]
      path        = $("#database_audio_"+sample_id+" source").attr("src");
      path        = "unchecked/" + path.split("unchecked/")[1];
      socket_io.emit("DatabaseManager",{"delete":{
          "path":path
        }
      });

      $(".tr_"+sample_id).remove();
      manager.start ++;
      manager.request_samples(1);
      console.log("TODO Deletion  " + sample_id)
    });

    // ******************************** AUDIO PLAYER CONTROLER
    update_slider_control = false
    $("#database_audio_"+sample_count).on("seeking", function(){
      sample_id        = this.id.split("_");
      sample_id        = sample_id[sample_id.length-1];
      sample_img_width = $('#database_img_'+sample_id+' img').width() / this.duration;
      pos              = Math.max(0,this.currentTime*sample_img_width);
      $('#database_img_'+sample_id+' img').css({"-webkit-transform": "translateX(-"+pos+"px)" });
      $("#database_extract_span_"+sample_id).text(this.currentTime);
    });

    $("#database_audio_"+sample_count).on("play", function(){
      sample_id = this.id.split("_")
      sample_id = sample_id[sample_id.length-1]
      audio = this
      update_slider_control = true
      sample_img_width = $('#database_img_'+sample_id+' img').width() / this.duration

      function update_slider(){
        pos = Math.max(0,audio.currentTime*sample_img_width - sample_img_width/2)
        pos = Math.max(0,audio.currentTime*sample_img_width)
        $("#database_extract_span_"+sample_id).text(audio.currentTime)
        $('#database_img_'+sample_id+' img').css({"-webkit-transform": "translateX(-"+pos+"px)" });
        if (update_slider_control)
          setTimeout(update_slider,10);
      }
      if (update_slider_control)   update_slider();
    });

    $("#database_audio_"+sample_count).on("pause", function(){
      update_slider_control = false;
    })
    sample_count++;
  };

}


function drawArray(arr, depth, size) {
  var offset, height, data, image;

  function conv(size) {
    return String.fromCharCode(size&0xff, (size>>8)&0xff, (size>>16)&0xff, (size>>24)&0xff);
  }

  offset = depth <= 8 ? 54 + Math.pow(2, depth)*4 : 54;
  height = Math.ceil(Math.sqrt(arr.length * 8/depth));

  //BMP Header
  data  = 'BM';                          // ID field
  data += conv(offset + arr.length);     // BMP size
  data += conv(0);                       // unused
  data += conv(offset);                  // pixel data offset

  //DIB Header
  data += conv(40);                      // DIB header length
  data += conv(size[1]);                       // image width
  data += conv(size[0]);                     // image height
  data += String.fromCharCode(1, 0);     // colour panes
  data += String.fromCharCode(depth, 0); // bits per pixel
  data += conv(0);                       // compression method
  data += conv(arr.length);              // size of the raw data
  data += conv(2835);                    // horizontal print resolution
  data += conv(2835);                    // vertical print resolution
  data += conv(0);                       // colour palette, 0 == 2^n
  data += conv(0);                       // important colours

  //Grayscale tables for bit depths <= 8
  if (depth <= 8) {
    data += conv(0);

    for (var s = Math.floor(255/(Math.pow(2, depth)-1)), i = s; i < 256; i += s)  {
      data += conv(i + i*256 + i*65536);
    }
  }
  //data += String.fromCharCode.apply(String, arr);
  for (var i = 0; i < arr.length; i++)
      data += String.fromCharCode(arr[i]);

  image = document.createElement('img');
  image.classList.add('database_fft_img');
  image.src = 'data:image/bmp;base64,' + btoa(data);

  return image;
}
