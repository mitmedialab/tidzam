<?php
require "utils.php";
//require 'vendor/autoload.php';
//dl("oggvorbis.so");

control_user();
postgres_connect();


switch($action){
  case "post_abuse":
    $recording      = isset($_POST["recording"])    ? $_POST["recording"]    : NULL;

    $ret = pg_query_params("SELECT * FROM users WHERE \"id\"=$1", array($user_id) );
    $row = pg_fetch_assoc($ret);

    $headers[] = 'MIME-Version: 1.0';
    $headers[] = 'Content-type: text/html; charset=iso-8859-1';
    $headers[] = 'From: No-reply <noreply@tidzam.media.mit.edu>';
    $headers[] = 'Reply-To: No-reply <noreply@tidzam.media.mit.edu>';
    $title  = "Tidzam Abuse Reporting";
    $msg    = '<html><body><h3>Tidzam Abuse Reporting</h3><br>';
    $msg   .= $row["user"].' ('.$row["mail"].') has reported an unappropriate audio file: '.$recording;
    $msg   .= '</body></html>';

    if(!mail($mail_reporting,$title,$msg, implode("\r\n", $headers))){
      echo($return_error."-Unable to report the abuse : ".$recording);
      exit();
    }

    $ret           = pg_query_params("UPDATE recordings SET active='false' WHERE recording=$1", array($recording));
    if(!pg_affected_rows($ret)){
      echo($return_error."-Unable to report the abuse : ".$recording);
      exit();
    }

    echo($return_ok."-Thank you for your reporting. Our team will investigate the situation. The file has been temporary excluded from the platform.");
    exit();
    break;


  case "post_upload":
    $location_name      = isset($_POST["location_name"])    ? pg_escape_string($_POST["location_name"])    : NULL;
    $location_lat       = isset($_POST["location_lat"])     ? $_POST["location_lat"]                       : NULL;
    $location_long      = isset($_POST["location_long"])    ? $_POST["location_long"]                      : NULL;
    $datetime           = isset($_POST["datetime"])         ? $_POST["datetime"]                           : NULL;
    $description        = isset($_POST["description"])      ? pg_escape_string($_POST["description"])      : NULL;

    $dst  = "$RECORDINGS_UPLOAD/['user']($location_name-".(new DateTime())->getTimestamp().")_$datetime";
    $path = upload_file($_FILES["audiofile_files"], $dst, ["ogg","mp3","wav"],5000000);

    $res = [];
    exec ( "ffprobe -show_format \"".$path."\" 2>&1  ", $res, $return_val);
    $samplerate = str_replace(" ","",str_replace(" Hz","",explode(",",$res[16])[1])) ;
    $duration   = explode("=", $res[24])[1];

    if($path == ""){
      echo($return_error."- Unable to upload your audio file.");
      exit();
    }
    $path     = "unchecked".str_replace($RECORDINGS_UPLOAD,"", $path);
    $location = json_encode(array('latitude'=>$location_lat,'longitude'=>$location_long));
    $ret      = pg_query_params("INSERT INTO recordings (\"recording\",\"datetime\",\"source\",\"owner\",\"geolocation\",\"description\",\"duration\",\"samplerate\",\"origin\",\"classe\")
                  VALUES($1,$2,$3,$4,$5,$6,$7,$8,'user_upload','unchecked')",  array($path,$datetime,$location_name,$user_id,$location,$description,$duration,$samplerate) );
    if(!$ret) {
      echo($return_error."-Unable to upload your file in database.");
      exit();
    }

    echo($return_ok);
    exit();
    break;

  case "add_classe":
    $classe_name        = isset($_POST["classe_name"])         ? pg_escape_string($_POST["classe_name"])         : NULL;
    $classe_description = isset($_POST["classe_description"])  ? pg_escape_string($_POST["classe_description"])  : NULL;

    // Check if image file is a actual image or fake image
    $new_classe_img = $CLASSES_UPLOAD . $classe_name;
    $new_classe_img = upload_file($_FILES["new_classe_img"], $new_classe_img, ["jpg","jpeg","png"]);

    // Check if the classe doesn t exist
    $ret           = pg_query_params("SELECT * FROM classes WHERE name=$1", array($classe_name));
    if(pg_num_rows($ret) > 0){
      echo($return_error."-Classe already exist.");
      exit();
    }

    // Add the classe
    $ret           = pg_query_params("INSERT INTO classes (\"name\",\"user\",\"img\",\"description\") VALUES($1,$2,$3,$4)",
                              array($classe_name,$user_id,$new_classe_img,$classe_description));
    if(!$ret) {
      echo($return_error."-Classe already exist.");
      exit();
    }
    exit();
    break;

    case "get_upload":
      $upload = [];
      $ret = pg_query_params("SELECT * FROM recordings WHERE \"owner\"=$1",
                  array($user_id));
      if(!$ret) {
        echo($return_error."-postgres");
        exit();
      }
      while ($row = pg_fetch_assoc($ret)){
        $ret2 = pg_query_params("SELECT * FROM entries WHERE \"recording\"=$1",array($row["recording"]));
        $row["answers"] = pg_num_rows($ret2);
          $upload[] = $row;
      }

      header('Content-Type: application/json');
      echo json_encode($upload);
      exit();
      break;

  case "get_classes":
    $classes = [];
    $ret = pg_query("SELECT * FROM classes");
    if(!$ret) {
      echo($return_error."-postgres");
      exit();
    }

    while ($row = pg_fetch_assoc($ret))
      $classes[] = array('id' => $row["id"], 'name' => $row["name"], 'img' => $row["img"] );

    header('Content-Type: application/json');
    echo json_encode($classes);
    exit();
    break;

  case "get_stats":
    $ret = pg_query_params("SELECT DISTINCT \"recording\" FROM entries WHERE \"user\"=$1 LIMIT $2 OFFSET $3",
                array($user_id, $limit, $start));
    if(!$ret) {
      echo($return_error."-postgres");
      exit();
    }

    $ret = pg_query("SELECT * FROM entries WHERE \"user\"='$user_id'");
    if(!$ret) {
      echo($return_error."-postgres");
      exit();
    }
    echo(pg_num_rows($ret));
    exit();
    break;

  case "get_recording":
    $recording       = isset($_GET["recording"]) ? $_GET["recording"] : NULL;
    $ret = pg_query_params("SELECT * FROM recordings WHERE recording=$1",
              array($recording));

    if(!$ret) {
      echo($return_error."-postgres");
      exit();
    }
    $data = pg_fetch_assoc($ret);
    header('Content-Type: application/json');
    if(count($data))    echo json_encode($data);
    else                echo "{}";
    exit();
    break;



  case "get_recordings":
    $classe       = isset($_GET["classe"]) ? pg_escape_string($_GET["classe"])  : NULL;
    $start        = isset($_GET["start"])  ? intval($_GET["start"])             : 0;
    $limit        = isset($_GET["limit"])  ? intval($_GET["limit"])             : 1;

    $data = [];
    if($classe)
      $ret = pg_query_params("SELECT * FROM recordings l WHERE \"classe\"=$3 AND NOT EXISTS (
               SELECT 1              -- it's mostly irrelevant what you put here
               FROM   entries i
               WHERE  l.recording = i.recording AND \"user\"=$4
               ) LIMIT $1 OFFSET $2;",
                array($limit, $start, $classe, $user_id));
    else
      $ret = pg_query_params("SELECT * FROM recordings LIMIT $1 OFFSET $2",
                array($limit, $start));

    if(!$ret) {
      echo($return_error."-postgres");
      exit();
    }
    while($row = pg_fetch_assoc($ret)){
      $data[] = $row;
    }
    header('Content-Type: application/json');
    echo json_encode($data);

    exit();
    break;

  case "delete_answer":
    $path      = isset($_POST["path"])   ?  pg_escape_string($_POST["path"])   : NULL;
    $classe    = isset($_POST["classe"])  ? pg_escape_string($_POST["classe"]) : NULL;
    $timing    = isset($_POST["timing"])  ? $_POST["timing"]                   : NULL;

    $ret = pg_query("SELECT \"id\" FROM classes WHERE \"name\"='$classe'");
    if(!$ret) {
      echo($return_error."-Classe unknown.");
      exit();
    }
    $ret    = pg_fetch_assoc($ret);
    $answer = $ret["id"];

    $ret = pg_query("DELETE FROM entries WHERE \"user\"='$user_id' AND \"recording\"='$path' AND \"answer\"='$answer' AND abs(\"recording_position\"-abs($timing)) < 0.2");

    if(!$ret) {
      echo($return_error."-Entries unknown.");
      exit();
    }
    echo($return_ok."-Delete ".$classe." at ".$timing." on ".$path);
    exit();
    break;

  case "post_answer":
    $recording    = isset($_POST["recording"])  ? pg_escape_string($_POST["recording"])   : NULL;
    $source       = isset($_POST["source"])     ? pg_escape_string($_POST["source"])      : NULL;
    $datetime     = isset($_POST["datetime"])   ? $_POST["datetime"] : (new DateTime('1970-01-01'))->format('Y-m-d H:i:sP');
    $samplerate   = isset($_POST["samplerate"]) ? $_POST["samplerate"]                    : 0;
    $duration     = isset($_POST["duration"])   ? $_POST["duration"]                      : NULL;
    $position     = isset($_POST["position"])   ? $_POST["position"]                      : NULL;
    $answer       = isset($_POST["answer"])     ? pg_escape_string($_POST["answer"])      : NULL;

    if($datetime == 'null')  $datetime   = (new DateTime('1970-01-01'))->format('Y-m-d H:i:sP');

    $ret = pg_query("SELECT \"id\" FROM classes WHERE \"name\"='$answer'");
    if(!$ret) {
      echo($return_error."-Classe unknown.");
      exit();
    }
    $ret    = pg_fetch_assoc($ret);
    $answer = $ret["id"];

    $ret = pg_query("INSERT INTO entries (\"user\",\"recording\",\"recording_source\",\"recording_datetime\",\"recording_position\",\"recording_samplerate\",\"recording_duration\",\"answer\")
              VALUES('$user_id','$recording','$source','$datetime','$position','$samplerate','$duration','$answer')");
    if(!$ret) {
      echo($return_error."-Entries error.");
      exit();
    }
    echo($return_ok);
    exit();
    break;


  case "get_answers":
      $path         = isset($_GET["path"])   ? $_GET["path"]                      : NULL;
      $start        = isset($_GET["start"])  ? intval($_GET["start"])             : NULL;
      $limit        = isset($_GET["limit"])  ? intval($_GET["limit"])             : NULL;
      $user         = isset($_GET["user"])   ? $_GET["user"]                      : NULL;

      $data = [];

      if($path == NULL)
        $ret = pg_query_params("SELECT DISTINCT \"recording\" FROM entries WHERE \"user\"=$1 LIMIT $2 OFFSET $3",
                        array($user_id, $limit, $start));

      else if($user != '*')
        $ret = pg_query_params("SELECT DISTINCT \"recording\" FROM entries WHERE \"user\"=$1 AND \"recording\"=$2",
                      array($user_id, $path));

      else
        $ret = pg_query_params("SELECT DISTINCT \"recording\" FROM entries WHERE \"recording\"=$1",
                      array($path));



      if(!$ret) {
        echo($return_error."-postgres");
        exit();
      }
      while($row = pg_fetch_assoc($ret)){
        $ret_recordings = pg_query_params("SELECT * from \"recordings\" WHERE \"recording\"=$1",
                        array($row["recording"]));
        $ret_recordings = pg_fetch_assoc($ret_recordings);

        if($user != '*')
          $ret2 = pg_query_params("SELECT * FROM entries WHERE \"user\"=$1 AND \"recording\"=$2",
                    array($user_id, $row["recording"]));
        else
          $ret2 = pg_query_params("SELECT * FROM entries WHERE \"recording\"=$1",
                    array($row["recording"]));

        $answers = [];
        while($row2 = pg_fetch_assoc($ret2))
          $answers[] = $row2;

        $ret_recordings["answers"] = $answers;
        $data[] = $ret_recordings;
      }

      header('Content-Type: application/json');
      echo json_encode($data);
      exit();
      break;

  default:;
}
?>

<script language="javascript">
TIDZAM_URL        = "//tidzam.media.mit.edu/audio-database/"
AVAILABLE_CLASSES = []
COUNT             = 0
START             = 0
UPLOAD_PATH       = "unchecked"
SELECTED_CLASSE   = "unchecked"
VIEW_CARDS        = []

function pq_get_recordings(classe=null, start=0, limit=1, clb){
  view_show_loading();
  $.ajax({
    type: "GET",
    url: "user-game.php?action=get_recordings&limit="+limit+"&start="+start+"&classe="+classe,
    success : function(recordings){
      for (r in recordings)
        view_make_card(recordings[r],function(){
          if (!recordings.length){
            $.ajax({
              type: "GET",
                url: "user-game.php?action=get_recordings&limit="+limit+"&start=0&classe="+classe,
              success : function(recordings){
                for (r in recordings)
                  view_make_card(recordings[r])
                view_hide_loading();
                if(clb) clb(recordings);
                }
              });
            }
          else view_hide_loading();
      });
    }
  });
}

function pq_get_recording(recording, clb){
  view_show_loading();
  $.ajax({
    type: "GET",
    url: "user-game.php?action=get_recording&recording="+recording,
    success : function(recording){
      if(clb) clb(recording)
      view_hide_loading();
      }
    });
}

function pq_get_answers(recording_path, clb, user){
  view_show_loading();
  $.ajax({
    type: "GET",
    url: "user-game.php?action=get_answers&path="+recording_path+"&user="+user,
    success : function(recordings){
      if (recordings.length == 0) if(clb) clb(null);
      for(recording in recordings){
        if(clb) clb(recordings[recording]);
      }
      view_hide_loading();
    }
  });
}

function pq_get_classes(clb){
  $.ajax({
    type: "GET",
    url: "user-game.php?action=get_classes",
    success : function(json){
      AVAILABLE_CLASSES = json;
      populate_classe_selector(AVAILABLE_CLASSES);

      $(".card_fft_container").each(function(){
        card_name = get_card_id(this.id);
        view_card_make_buttons(card_name);
      });

      if (clb) clb(classe)
    }
  });
}

function pq_del_answer(path, classe, timing, clb){
  data = "&path="+path+"&classe="+classe+"&timing="+(timing-0.5);
  $.ajax({
    type: "POST",
    url: "user-game.php?action=delete_answer",
    data: data,
    success : clb
  });
}

function pq_send_answer(card_name, answer, clb){
  path        = $('#card_path_'+card_name).html()
  source      = $('#card_source_'+card_name).text()
  datetime    = $('#card_datetime_'+card_name).text()
  duration    = $('#card_duration_'+card_name).text()
  samplerate  = $('#card_samplerate_'+card_name).text()
  position    = $("#database_audio_control_"+card_name)[0].currentTime-0.5;

  if (position < 0) return;

  data = "&recording="+path+"&source="+source+"&duration="+duration+"&datetime="+datetime+"&samplerate="+samplerate+"&position="+position+"&answer="+answer;
  $.ajax({
    type: "POST",
    url: "user-game.php?action=post_answer",
    data: data,
    success : clb
  });
}

function pq_get_upload(clb){
  $.ajax({
    type: "GET",
    url: "user-game.php?action=get_upload",
    success : clb
  });
}

function pq_report_abuse(recording_path, clb){
  $.ajax({
    type: "POST",
    url: "user-game.php?action=post_abuse",
    data:"&recording="+recording_path,
    success : clb
  });
}

/* ================ GAME VIEW ================ */

function populate_classe_selector(AVAILABLE_CLASSES){
  $("#select_classe").empty();
  for (classe in AVAILABLE_CLASSES){
    cl = AVAILABLE_CLASSES[classe].name.split("-")
    cl = cl[cl.length-1].replace(/_/g," ");
    option = '<option value="'+AVAILABLE_CLASSES[classe].name+'" '+(AVAILABLE_CLASSES[classe].name==SELECTED_CLASSE?"selected":"")+'>'+cl+'</option>';
    $("#select_classe").append(option);
  }
}

function card_ok_animation(){
    $("#card_ok").removeClass("hide");
    $(".sa-success").addClass("hide");
    setTimeout(function() {
      $(".sa-success").removeClass("hide");
      setTimeout(function() {
        $("#card_ok").addClass("hide");
      }, 2000);
    }, 10);
}


function remove_marker(card_name, timing){
  duration = $("#database_audio_control_"+card_name)[0].duration
  recording_img_width = $('#card_fft_img_img_'+card_name).width() / duration;
  pos = Math.max(0,timing * recording_img_width)

  $('#card_fft_img_'+card_name + ' > .card_img').each(function( index ) {
    marker_pos = parseInt(this.style.left.replace("px",""))
    if (Math.abs(Math.abs(marker_pos) - pos + 186) < 10){
      classe = this.id.split("_");
      classe.pop();
      classe.splice(0,4);
      classe = classe.join("_");
      id = this.id;
      path        = $('#card_path_'+card_name).html();
      pq_del_answer(path, classe, timing, function(text){
        if(text.indexOf("success") != -1)
          $('#'+id).remove();
        else {
          $("#alert_box_msg").text("Unable to remove the answer ("+text+")");
          $("#alert_box").show("slow");
        }
      });
    }
  });
}

function card_add_marker(card_name,user,id,answer, pos){
  classe = "";
  for (cl in AVAILABLE_CLASSES)
    if (AVAILABLE_CLASSES[cl].name == answer || AVAILABLE_CLASSES[cl].id == answer){
      classe = AVAILABLE_CLASSES[cl].name;
      img    = AVAILABLE_CLASSES[cl].img;
    }

  if (classe == ""){
    console.log("ERROR : unknown classe " + answer)
    return ;
  }
  marker =  '<div id="card_img_'+user+'_'+id+'_'+classe+'_'+card_name+'" class="card_img" style="left:'+(Math.abs(pos))+'px;">';
  marker += '<img src="'+img+'" class="img"><h3><span>'+classe+'</span></h3>'
  marker += '</div>'
  $("#card_fft_img_"+card_name).append(marker)
}

function card_add_answers(recordings){
    for (card in VIEW_CARDS)
        if(VIEW_CARDS[card].path.join("/") == recordings.recording)
          VIEW_CARDS[card].answers = recordings.answers;

    path_list = $(".card_path").get();
    for (var l = 0; l < path_list.length; l++){
      if(recordings.recording == $("#"+path_list[l].id).text()){
        done = 0
        // Ready to add the markers
        card_name = get_card_id(path_list[l].id);
        for (var i=0; i < recordings.answers.length; i++){
          recording_img_width = $('#card_fft_img_img_'+card_name).width() / recordings.answers[i].recording_duration;
          pos = recording_img_width * recordings.answers[i].recording_position;
          card_add_marker(card_name,recordings.answers[i].user,recordings.answers[i].id,recordings.answers[i].answer, pos);
        }
      };
    };
}

function card_remove_answers(card_name){
  for (card in VIEW_CARDS)
    if(VIEW_CARDS[card].name == card_name)
        VIEW_CARDS[card].answers = [];
  $("#card_fft_img_"+card_name+" .card_img").remove();
  }

  /*==================== HISTORY OR GAME MODE */
  function card_switch_history_game_mode(){
    if ($("#card_usergame_header").hasClass("bg-success")){
      $("#card_usergame_header").removeClass("bg-success").addClass("bg-warning");
      $("#card_usergame_footer").removeClass("bg-success-footer").addClass("bg-warning-footer");
      $('#select_classe_div').hide();
    }
    else {
      $("#card_usergame_header").removeClass("bg-warning").addClass("bg-success");
      $("#card_usergame_footer").removeClass("bg-warning-footer").addClass("bg-success-footer");
      $('#div_user_recording_list').hide('slow');
      $('#select_classe_div').show();
    }
  }

  function is_history_mode(){
      if ($("#card_usergame_header").hasClass("bg-success"))
        return false;
      return true;
  }


  function card_next_history_recording(){
    limit  = parseInt($( "#select_limit option:selected" ).val());
    pq_get_answers_list(function(recordings){
      for(var i=0; i < recordings.length; i++)
        pq_get_answers(recordings[i].recording,function(recording){
          view_make_card(recording,function(){
            setTimeout(function(){card_add_answers(recording);},500);
            })
        });
      }, limit, START);
    }

  /*==================== BUTTON CONTROL */
  function view_btn_show_primary(card_name, classe){
    classe = classe.split("-")
    classe.pop();
    classe = classe.join("-")
    count_sub = classe.split("-").length

    if (classe == "")
      $('#btn_'+card_name+'_-return').hide();

    $('#card_classe_'+card_name).text(classe);

    $(".btn_classe_div").each(function(){
      if(this.id.indexOf(card_name) != -1) {
        if (this.id.indexOf(classe) != -1 && this.id.split("-").length == count_sub)
          $("#"+this.id).show();
        else $("#"+this.id).hide();
      }
    });
  }

function view_btn_show_seconday(card_name, classe){
  $('#btn_'+card_name+'_-return').show();
  hasSecondaryClasse = false;
  btns = $(".btn_classe_div").get();
  for (var i=0; i < btns.length; i++){
    if(btns[i].id.indexOf(card_name) != -1)
      if (btns[i].id.indexOf(classe+"-") != -1)
        hasSecondaryClasse = true;
  }
  if (hasSecondaryClasse)
    $(".btn_classe_div").each(function(){
      if(this.id.indexOf(card_name) != -1) {
        if(this.id.indexOf(classe) != -1
            || this.id.indexOf("return") != -1
            || this.id.indexOf("others") != -1)
          $("#"+this.id).show();
        else $("#"+this.id).hide();
      }
    });
}

function get_card_id(id){
  tmp =   id.split("_");
  return tmp[tmp.length - 1];
}

function view_card_make_buttons(name){
  $('#card_btn_'+name).empty();
  tpl = '<div class="d-inline-flex btn_classe_div"><button type="button" id="btn_'+name+'_-return" class="mx-auto btn btn-light btn_classe" style="background:url(\'static/img/undo.png\');background-position: center; background-repeat:no-repeat;background-size: 75px 60px;">Back</button></div>';
  tpl += '<div class="btn_classe_div"><button type="button" id="btn_'+name+'_delete" class="mx-auto btn btn-light btn_classe" style="background:url(\'static/img/delete.png\');background-position: center; background-repeat:no-repeat;background-size: 75px 60px;">Delete</button></div>';
  tpl += '<div class="btn_classe_div"><button type="button" id="btn_'+name+'_others" class="mx-auto btn btn-light btn_classe" style="background:url(\'static/img/others.png\');background-position: center; background-repeat:no-repeat;background-size: 75px 60px;">Other</button></div>';
  for (classe in AVAILABLE_CLASSES){
    cl = AVAILABLE_CLASSES[classe].name.split("-")
    cl = cl[cl.length-1].replace(/_/g," ");
    tpl += '<div class=" btn_classe_div" id="btn_classe_div_'+name+'_'+AVAILABLE_CLASSES[classe].name+'">';
    tpl += '  <span class="btn_icon_add" id="btn_icon_add_'+name+'_'+AVAILABLE_CLASSES[classe].name+'"><i class="fa fa-plus mr-4" aria-hidden="true"></i></span>'
    tpl += '  <button type="button" id="btn_'+name+'_'+AVAILABLE_CLASSES[classe].name+'" class="btn btn-light btn_classe" style="background:url(\''+AVAILABLE_CLASSES[classe].img+'\');background-position: center; background-repeat:no-repeat;background-size: 75px 60px;">'+cl+'</button>';
    tpl += '</div>';
  }
  $('#card_btn_'+name).append(tpl);
  view_btn_show_primary(name,"");

$(".btn_icon_add").click(function(){
  id        = this.id;
  tmp       = this.id.replace("btn_icon_add_").split("_");
  card_name = tmp.shift();
  classe    = tmp.join("_");
  if (classe != "")  $("#new_classe_name").val(classe+"-");
  else  $("#new_classe_name").val("");
  $("#modal_new_classe").modal("show");
})

$(".btn_classe").click(function(){
  id  = this.id;
  tmp = this.id.split("_");
  tmp.shift();
  card_name = tmp.shift();
  classe    = tmp.join("_");

  if (classe.indexOf("delete") == -1)
    view_btn_show_seconday(card_name, classe);

  if (classe.indexOf("return") != -1){
    classe = $('#card_classe_'+card_name).text().split("-")
    classe.pop();
    classe = classe.join("-");
    view_btn_show_primary(card_name, classe)
    return
  }

  else if (classe.indexOf("delete") != -1){
    remove_marker(card_name, $("#database_audio_control_"+card_name)[0].currentTime);
    return
  }

  else if (classe.indexOf("others") != -1){
    classe = $('#card_classe_'+card_name).text().split("-")
    if (classe != "")  $("#new_classe_name").val(classe+"-");
    else  $("#new_classe_name").val("");
    $("#modal_new_classe").modal("show");
  }

  else pq_send_answer(card_name, classe,function(text){
      if(text.indexOf("success") != -1){
        pos = $("#card_fft_img_"+card_name).position()
        card_add_marker(card_name,<?php echo $user_id; ?>,(new Date().getTime()),classe, (Math.abs(pos.left)-186))
        offset = $("#"+id).offset();
        $("#card_ok").css({top: offset.top-20, left: offset.left, position:'absolute'});
        card_ok_animation()
      }
      else {
        $("#alert_box_msg").text("Please contact the administrator ("+text+")");
        $("#alert_box").show("slow");
      }
    });
    $('#card_classe_'+card_name).text(classe);
  });

}

function view_cards_clear(){
  VIEW_CARDS = [];
  $("#cards").empty();
};


function ViewCard(recording){
  this.name = "slash"+COUNT++;
  this.path = recording.recording.split("/")
  if (this.path[this.path.length-2] == "unchecked"){
    prediction = this.path[this.path.length-1].split("']")[0]
    prediction = prediction.split("['")[1]
    }
  else prediction = this.path[this.path.length-2]
  if (prediction)
    prediction = prediction.split("(")[0]

  this.source       = recording.source
  this.date         = recording.datetime
  this.geolocation  = JSON.parse(recording.geolocation)
  this.answers      = recording.answers

  for(ans in this.answers)
    for (cl in AVAILABLE_CLASSES)
      if (AVAILABLE_CLASSES[cl].id == this.answers[ans].answer)
        this.answers[ans].classe = AVAILABLE_CLASSES[cl].name;

  this.url = TIDZAM_URL+recording.recording;

  tpl  = '  <div class="border border-dark rounded my-2">'
  tpl += '  <div id="card_path_'+this.name+'" style="display:none;" class="card_path">'+recording.recording+'</div>'
  tpl += '  <div class="card_fft_container" id="card_fft_container_'+this.name+'">';
  tpl += '    <div class="card_fft_img" id="card_fft_img_'+this.name+'"><img src="" class="card_fft_img_img" id="card_fft_img_img_'+this.name+'"></div>';
  tpl += '    <div class="card_fft_control_left" id="card_fft_control_left_'+this.name+'"><i class="fa fa-step-backward" aria-hidden="true"></i></div>';
  tpl += '    <div class="card_fft_target" id="card_target_'+this.name+'"><i class="fa fa-play" aria-hidden="true"></i></div>';
  tpl += '    <div id="card_fft_control_right_'+this.name+'" class="card_fft_control_right"><i class="fa fa-step-forward" aria-hidden="true"></i></div>';
  tpl += '    <div class="card_fft_text"><span class="database_title_samplerate" id="database_extract_span_'+this.name+'">0</span> sec</div>';
  tpl += '  </div>';
  tpl += '  <audio class="database_audio_control" controls id="database_audio_control_'+this.name+'"  type="audio/wav"><source src="'+this.url+'"></audio>';
  tpl += '  <div class="card-body">';
  tpl += '    <h5 class="card-title"><div class="d-flex flex-sm-row flex-column justify-content-between">';
  tpl += '      <div>What sound is that ?</div>';
  tpl += '      <div>';
  tpl += '        <i id="card_info_'+this.name+'" class="fa fa-info-circle mr-4" aria-hidden="true" title="Get some informations about the recording"></i>';
  tpl += '        <i id="card_view_all_'+this.name+'" class="fa fa-eye mr-4" aria-hidden="true" title="See other user responses"></i>';
  tpl += '        <i id="card_download_'+this.name+'" class="fa fa-download mr-4" aria-hidden="true" title="Download the audio and metadata files"></i>';
  tpl += '        <i id="card_upload_'+this.name+'" class="fa fa-upload mr-4" aria-hidden="true" title="Upload an audio files"></i>';
  tpl += '        <i id="card_abuse_'+this.name+'" class="fa fa-bullhorn mr-4" aria-hidden="true" title="Reporting an abuse or an inappropriate audio file."></i>';
  tpl += '      </div>';
  tpl += '      </div></h5>';
  tpl += '  <div class="alert alert-warning" style="display: none" id="info_box_'+this.name+'">';
  tpl += '    <span class="close" onclick="$(\'#info_box_'+this.name+'\').hide(\'slow\');">';
  tpl += '      <span aria-hidden="true">&times;</span>';
  tpl += '    </span>';
  tpl += '    <h4 class="alert-heading">Recording Information</h4>';
  tpl += '    <div>From <span id="card_source_'+this.name+'">'+this.source+'</span><br>';
  tpl += '        On <span id="card_datetime_'+this.name+'">'+this.date+'</span><br>';
  tpl += '        Detected as <span id="card_prediction_'+this.name+'">'+prediction+'</span><br>';
  tpl += '        Duration <span id="card_duration_'+this.name+'">'+recording["duration"]+'</span></br>';
  tpl += '        Sampling rate at <span id="card_samplerate_'+this.name+'">'+recording["samplerate"]+'</span> Hz<br>';
  tpl += '        Location <span id="card_location_'+this.name+'">'+recording["location"]+'</span>';
  tpl += '    </div>';
  tpl += '  </div>';
  tpl += '    <span>Category: <span id="card_classe_'+this.name+'"></span></span>';
  tpl += '    <div class="card_btn row" id="card_btn_'+this.name+'"></div>';
  tpl += '  </div>';
  tpl += '</div>';
  $("#cards").append(tpl);

  view_card_make_buttons(this.name);

$('#card_upload_'+this.name).click(function(){
  pq_get_upload(function(uploads){
    categories = []
    for (file in uploads){
      upload_categ = uploads[file].source;
      if (categories.indexOf(upload_categ) == -1){
        categories.push(upload_categ);
        option = '<option value="'+upload_categ+'">'+upload_categ+'</option>';
        $("#new_audiofile_category_select").append(option);
      }
    }
    $("#modal_new_audio_file").modal("show");
  });
});

$("#card_download_"+this.name).click(function(){
  card_name = get_card_id(this.id);

  for (var i=0; i < VIEW_CARDS.length; i++)
    if (VIEW_CARDS[i].name == card_name) {
      $("<a />", {
        "download": "tidzam-metadata-"+VIEW_CARDS[i].source+"-"+VIEW_CARDS[i].date+".json",
        "href" : "data:application/json," + encodeURIComponent( JSON.stringify(VIEW_CARDS[i]) )
      }).appendTo("body")
      .click(function() {
         $(this).remove()
      })[0].click();
      $("<a />", {
        "download": "tidzam-recording-"+VIEW_CARDS[i].source+"-"+VIEW_CARDS[i].date+".wav",
        "href" :  VIEW_CARDS[i].url
      }).appendTo("body")
      .click(function() {
         $(this).remove()
      })[0].click();
    }
});

$("#card_abuse_"+this.name).click(function(){
  card_name       = get_card_id(this.id);
  recording_path  = $('#card_path_'+card_name).text();
  pq_report_abuse(recording_path,function(text){
    $("#alert_box_msg").text(text.replace("success-","").replace("error-",""));
    $("#alert_box").show("slow");
    $("#btn_next").click();
  });
});

// Module for showing response of other users (switching the response colors)
$("#card_view_all_"+this.name).click(function(){
  card_name       = get_card_id(this.id);
  recording_path  = $('#card_path_'+card_name).text();

  if ($("#card_view_all_"+card_name).hasClass("fa-eye")){
    pq_get_answers(recording_path, function(recording){
      if(!recording) return;

      card_add_answers(recording);

      color_users = {}
      $('.card_img').each(function(){
        card_name_img = get_card_id(this.id);
        if (card_name_img != card_name) return;

        // Looking for the user color (or create random one)
        user_id = this.id.replace("card_img_","").replace("_"+card_name,"").split("_")[0];
        if (!color_users[user_id]){
          color = []
          for(var i = 0; i < 3; i++) color.push(Math.floor(Math.random() * 255));
          color_users[user_id] = 'rgb('+ color.join(',') +')';
        }

        // Print the user color box around the marker
        if (user_id != <?php echo $user_id; ?>){
          //$('#'+this.id).css("filter","alpha(opacity=50)");
          //$('#'+this.id).css("opacity","0.5");
          //$('#'+this.id).css("background-color",color_users[user_id]);
          color = color_users[user_id];
          color = 'red';
          $('#'+this.id+' span').css("background-color",color );
          $('#'+this.id+' span').css("color","white" );
        }
      });
    $("#card_view_all_"+card_name).removeClass("fa-eye").addClass("fa-eye-slash")
    }, "*");
  }
  else {
    $("#card_view_all_"+card_name).addClass("fa-eye").removeClass("fa-eye-slash")

    pq_get_answers(recording_path, function(recording){
      card_remove_answers(card_name);
      if(recording) card_add_answers(recording);
      });
    }
  });

$("#card_info_"+this.name).click(function(){
  card_name = get_card_id(this.id);
  $('#info_box_'+card_name).toggle("slow");
});


  /* ================ AUDIO PLAYER CONTROLER ================ */
  // Control
  $('#card_target_'+this.name).click(function(){
    card_name = get_card_id(this.id);

    if ($("#database_audio_control_"+card_name)[0].paused){
      $("#database_audio_control_"+card_name).trigger('play');
      $('#card_target_'+card_name+' i').removeClass("fa-play").addClass("fa-pause");
    }
    else {
      $("#database_audio_control_"+card_name).trigger('pause');
      $('#card_target_'+card_name+' i').removeClass("fa-pause").addClass("fa-play");
    }
  })

  $('#card_fft_control_left_'+this.name).click(function(){
    card_name = get_card_id(this.id);
    $("#database_audio_control_"+card_name)[0].currentTime -= 0.05
  })

  $('#card_fft_control_right_'+this.name).click(function(){
    card_name = get_card_id(this.id);
    $("#database_audio_control_"+card_name)[0].currentTime += 0.05
  })


  update_slider_control = false
  $("#database_audio_control_"+this.name).on("seeking", function(){
    card_name = get_card_id(this.id);

    recording_img_width = $('#card_fft_img_img_'+card_name).width() / this.duration;
    pos              = Math.max(0,this.currentTime*recording_img_width);
    $('#card_fft_img_'+card_name).css({"-webkit-transform": "translateX(-"+pos+"px)" });
    $("#database_extract_span_"+card_name).text(Math.round(this.currentTime * 100) / 100);
  });

  $("#database_audio_control_"+this.name).on("play", function(){
    card_name = get_card_id(this.id);

    audio = this
    update_slider_control = true
    recording_img_width = $('#card_fft_img_img_'+card_name).width() / this.duration
    $('#card_target_'+card_name+' i').removeClass("fa-play").addClass("fa-pause");

    function update_slider(){
      pos = Math.max(0,audio.currentTime*recording_img_width)
      $("#database_extract_span_"+card_name).text(Math.round(audio.currentTime * 100) / 100)
      $('#card_fft_img_'+card_name).css({"-webkit-transform": "translateX(-"+pos+"px)" });

      if (update_slider_control)
        setTimeout(update_slider,10);
    }
    if (update_slider_control)   update_slider();
  });

  $("#database_audio_control_"+this.name).on("pause", function(){
    card_name = get_card_id(this.id);

    update_slider_control = false;
    $('#card_target_'+card_name+' i').removeClass("fa-pause").addClass("fa-play");
  })

  $("#database_audio_control_"+this.name).on("ended", function(){
    card_name = get_card_id(this.id);

    $('#card_target_'+card_name+' i').removeClass("fa-pause").addClass("fa-play");
    update_slider_control = false;
  })

}
/* ================ CONTROLLER ================ */
function pq_get_answers_list(clb, limit=1, start=0, user){
  $.ajax({
    type: "GET",
    url: "user-game.php?action=get_answers&limit="+limit+"&start="+start+"&user="+user,
    success : function(text){
      if(clb) clb(text);
    }
  });
}

function view_make_card(recording, clb){
  img = recording.recording.replace("wav","png")
  $.ajax({
    type: "GET",
    url: "database/fft/"+img,
    success : function(img){
      view = new ViewCard(recording)
      $('#card_fft_img_img_'+view.name).attr('src','data:image/png;base64,' + img)
      VIEW_CARDS.push(view);
      if(clb) clb()
    }
  });
}

function view_show_loading(){
  $("#loader_div").modal("show");
}

function view_hide_loading(){
  setTimeout(function(){
    $("#loader_div").modal("hide");
  }, 500);
}


$("#add_classe").click(function () {
  $("#modal_new_classe").modal("hide");
  var formData = new FormData();

  formData.append('classe_name', $("#new_classe_name").val())
  formData.append('classe_description', $("#new_classe_description").val())
  formData.append('new_classe_img', $("#new_classe_img").get(0).files[0])

  $.ajax({
    type: "POST",
    url: "user-game.php?action=add_classe",
    data : formData,
    contentType: false,
    processData: false,
    cache : false,
    async : false,
    success : function(text){
      pq_get_classes();
    }
  });
});

/* ================ STAT / CONTRIB ================ */
$("#btn_upload_next").click(function(){
  page = $("#span_contrib_count").text().replace("#","");
  page = parseInt(page)
  $("#span_upload_count").text("#" + (page+1));
  card_update_uploads(function(total){
    if (!total)  $("#btn_upload_next").hide();
  });
  $("#btn_upload_prev").show();
});

$("#btn_upload_prev").click(function(){
  page = $("#span_upload_count").text().replace("#","");
  page = parseInt(page)
  if (page > 0){
    $("#span_upload_count").text("#" + (page-1));
    card_update_uploads();
    }
  $("#btn_upload_next").show();
  if (!page) $("#btn_upload_prev").hide();
});

function card_update_uploads(clb){
  pq_get_upload(function(uploads){
    limit = 5;
    nb_print = 0;
    page = parseInt($("#span_upload_count").text().replace("#",""));

    $("#div_user_upload_list_content").empty();
    for (r in uploads){
      try{
        if (r >= limit * page && r < limit * (page + 1)){
          nb_print ++;
          row =  '<div class="row w-100 border my-1 div_user_upload_list_row">';
          row += '  <a href="#game_area" class="col-sm-3" id="a_user_upload'+uploads[r].recording+'">'+uploads[r].source+'</a>';
          row += '  <span class="col-sm-4">'+uploads[r].date+'</span>';
          row += '  <span class="col-sm">'+uploads[r].samplerate+' Hz</span>';
          row += '  <span class="col-sm">'+uploads[r].duration+' sec</span>';
          row += '  <span class="col-sm">'+uploads[r].answers+' answers</span>';
          row += '</div>';
          $("#div_user_upload_list_content").append(row);
        }
      }
      catch(err){
        console.log("ERROR: reception of uploads " + err + " " + JSON.stringify(uploads))
      }
    }

    $(".div_user_upload_list_row a").click(function(){
      recording_path = this.id.split("a_user_upload")[1]
      view_cards_clear();
      START = 0;

      pq_get_answers(recording_path,function(recording){
        if(recording)
          view_make_card(recording,function(){
            setTimeout(function(){card_add_answers(recording);},500);
            });
        else pq_get_recording(recording_path,function(recording){
          view_make_card(recording);
          });
        });
    });
    $("#btn_list_uploads").text(uploads.length + ' files');
    if(clb) clb(nb_print,uploads.length);
  });
}

function card_update_contributions(clb){
  $("#btn_list_files").text('0 file and 0 answer');
  pq_get_answers_list(function(recordings){
    count     = 0;
    limit     = 5;
    nb_print  = 0;
    page      = parseInt($("#span_contrib_count").text().replace("#",""));

    $("#div_user_recording_list_content").empty();
    for (r in recordings){
      try{
        count += recordings[r].answers.length;
        if (r >= limit * page && r < limit * (page + 1)){
          nb_print ++;
          row =  '<div class="row w-100 border my-1 div_user_recording_list_row">';
          row += '  <a href="#game_area" class="col-sm-3" id="a_user_recording'+recordings[r].recording+'">'+recordings[r].answers[0].recording_source+'</a>';
          row += '  <span class="col-sm-4">'+recordings[r].answers[0].recording_datetime+'</span>';
          row += '  <span class="col-sm">'+recordings[r].answers[0].recording_samplerate+' Hz</span>';
          row += '  <span class="col-sm">'+recordings[r].answers[0].recording_duration+' sec</span>';
          row += '  <span class="col-sm">'+recordings[r].answers.length+' answers</span>';
          row += '</div>';
          $("#div_user_recording_list_content").append(row);
        }
      }
      catch(err){
        console.log("ERROR: reception of recordings " + err + " " + JSON.stringify(recordings))
      }
    }
    $(".div_user_recording_list_row a").click(function(){
      recording = this.id.split("a_user_recording")[1]
      if(!is_history_mode())
        card_switch_history_game_mode();

      view_cards_clear();
      START = 0;

      pq_get_answers(recording,function(recording){
        view_make_card(recording,function(){
          setTimeout(function(){card_add_answers(recording);},500);
        });
      });
    });

    $("#btn_list_files").text(recordings.length + ' files and '+count+' answers');
    if(clb) clb(nb_print,count);
  },1000000,0);
}

$('#select_classe').on("change",function(){
  SELECTED_CLASSE  = $( "#select_classe option:selected" ).val();
  view_cards_clear();
  limit = parseInt($( "#select_limit option:selected" ).val());
  START = 0;
  pq_get_recordings(SELECTED_CLASSE, START, limit);
});


$("#card_usergame_title").click(function(){
  card_switch_history_game_mode();
  if ($("#div_user_recording_list").is(':visible') ){
    $("#div_user_recording_list").hide("slow");
    view_cards_clear();
    START = 0;
    limit = parseInt($( "#select_limit option:selected" ).val());
    pq_get_recordings(SELECTED_CLASSE, START, limit);
  }
  else {
    $("#div_user_recording_list").show("slow");
    view_cards_clear();
  }

});

/*==================== CARD CONTROL */
$('#btn_next').click(function(){
  view_cards_clear();
  limit  = parseInt($( "#select_limit option:selected" ).val());
  START += limit;
  if(START > 0 ) $('#btn_prev').show();

  if(is_history_mode())
    card_next_history_recording();
  else{
    pq_get_recordings(SELECTED_CLASSE, START, limit);
  }

  card_update_contributions();
})

$('#btn_prev').click(function(){
  view_cards_clear();
  limit  = parseInt($( "#select_limit option:selected" ).val());
  START -= limit;
  if(START <= 0){
     START = 0;
    $('#btn_prev').hide();
  }
  else $('#btn_prev').show();

  if(is_history_mode())
    card_next_history_recording();
  else
    pq_get_recordings(SELECTED_CLASSE, START, limit);
  card_update_contributions();
})

$('#select_limit').on('change', function(){
  view_cards_clear();
  limit = parseInt($( "#select_limit option:selected" ).val());
  if(is_history_mode())
    card_next_history_recording();
  else
    pq_get_recordings(SELECTED_CLASSE, START, limit);
  START += limit;
})

$("#btn_contrib_next").click(function(){
  page = $("#span_contrib_count").text().replace("#","");
  page = parseInt(page)
  $("#span_contrib_count").text("#" + (page+1));
  card_update_contributions(function(total){
    if (!total)  $("#btn_contrib_next").hide();
  });
  $("#btn_contrib_prev").show();
});

$("#btn_contrib_prev").click(function(){
  page = $("#span_contrib_count").text().replace("#","");
  page = parseInt(page)
  if (page > 0){
    $("#span_contrib_count").text("#" + (page-1));
    card_update_contributions();
    }
  $("#btn_contrib_next").show();
  if (!page) $("#btn_contrib_prev").hide();
});

$("#new_audiofile_category_create").click(function(){
  if($("#new_audiofile_category_select").hasClass("d-sm-none")){
    $("#new_audiofile_category_select").removeClass("d-sm-none");
    $("#new_audiofile_category_input").addClass("d-sm-none");
    $("#new_audiofile_category_create i").addClass("fa-plus").removeClass("fa-bars");
    $("#new_audiofile_category_input").val("");
  }
  else {
    $("#new_audiofile_category_select").addClass("d-sm-none");
    $("#new_audiofile_category_input").removeClass("d-sm-none");
    $("#new_audiofile_category_create i").addClass("fa-bars").removeClass("fa-plus");
  }
})

$("#new_audio_file").click(function (){
  categ = $("#new_audiofile_category_input").val();
  if (categ == "") categ = $( "#new_audiofile_category_select option:selected" ).val()
  if (!categ){
    $("#alert_box_msg").text("Category field should be provided");
    $("#alert_box").show("slow");
    $("#modal_new_audio_file").modal("hide");
    return
  }

  datetime = new Date($("#new_audiofile_datetime").val());
  if (!datetime || datetime == "Invalid Date"){
    $("#alert_box_msg").text("Datetime should be in the right format (yyyy-mm-ddThh:mm:ss)");
    $("#alert_box").show("slow");
    $("#modal_new_audio_file").modal("hide");
    return
  }

  location_name = $("#new_audiofile_name").val();
  if (!location_name || location_name == ""){
    $("#alert_box_msg").text("Location name should be defined");
    $("#alert_box").show("slow");
    $("#modal_new_audio_file").modal("hide");
    return
  }

  var formData = new FormData();
  formData.append('location_name', location_name)
  formData.append('location_lat', $("#new_audiofile_lat").val())
  formData.append('location_long', $("#new_audiofile_long").val())
  formData.append('datetime', $("#new_audiofile_datetime").val())
  formData.append('description', $("#new_audiofile_description").val())
  formData.append('audiofile_files', $("#new_audiofile_file").get(0).files[0])

  $.ajax({
    type: "POST",
    url: "user-game.php?action=post_upload",
    data : formData,
    contentType: false,
    processData: false,
    cache : false,
    async : false,
    success : function(text){
      if (text.indexOf("error") != -1){
        text = text.replace("error-","")
        $("#alert_box_msg").text(text);
        $("#alert_box").show("slow");
      }
      $("#modal_new_audio_file").modal("hide");
      card_update_uploads();
    }
  });
});

function card_update_status(total_contrib){
  text = '<span><?php  echo $user; ?>';
  text += '<?php
    switch ($status) {
      case 3: echo " (admin)"; break;
      case 2: echo " (expert)"; break;
      default: echo" (user)";
    } ?>';
  text += '</span><div class="d-flex">';
  for (var i=0; i <5 ; i++)
    if(Math.pow(10,i) < total_contrib)
      text += '<i class="fas fa-star p-1" style="font-size:14px;"></i>';
    else text += '<i class="far fa-star p-1" style="font-size:14px;"></i>';
  text += '</div>';
  $("#card_usergame_title").html(text);
}


/* ================ INIT ================ */
$(document).ready(function(){
  // Get User stats
  card_update_uploads(function(nb_print, total_upload){
    card_update_contributions(function(nb_print, total_contrib){
      card_update_status(total_upload+total_contrib);
    });
  });

  // Get classe list and then load a recording
  pq_get_classes(function(classes){
    view_cards_clear();
    limit  = parseInt($( "#select_limit option:selected" ).val());
    pq_get_recordings(SELECTED_CLASSE,START, limit);
  });
});

</script>

<style>

#card_usergame_title{
  text-decoration: none;
}

#card_usergame_title:hover{
  text-decoration: underline;
}

.card_usergame .card-header i{
  font-size: 24px;
}

.card_ok {
  width: 80px;
  height: 130px;
  margin: 0 auto;
}

.btn_classe {
width:90px;
height:100px;
padding-top:85px;
font-size:10px;
}

.btn_classe_div{
  position:relative;
}
.btn_icon_add{
  position:absolute;
  text-align:right;
  right:0px;
  top:0px;
  width:18px;
}

.btn_icon_add :hover {
  font-size:22px;
}

#btn_return_game{
  font-size:14px;
}

.card_fft_target{
  background-color: green;
  border-style:solid;
  border-color:green;
  opacity:0.5;
  border-width:1px;
  width:186px;
  height:150px;
  position:absolute;
  z-index:100;
  margin-left: calc(50% - 93px);
  font-size:78px;
  text-align:center;
  color:white;
}

.card_img{
  position:absolute;
  width:186px;
  height:150px;
  z-index:999;
  top:0px;
  text-align:center;
  vertical-align: middle;
}

.card_img img{
  position:absolute;
  top:20px;
  left:28px;
  width:130px;
  height:130px;
}

.card_img h3{
  position:absolute;
  display: inline-block;
  top:2px;
  left:2px;
  margin-left:auto;
  margin-right:auto;
  width:95%;
  color:red;
  font-size: 14px;
}

.card_img span{
  background-color:white;
}

.card_fft_target i {
vertical-align: middle;
}

.card_fft_text{
  position:absolute;
  vertical-align:baseline;
  text-align:center;
  width:100%;
  margin-top:100px;
  z-index:101;
  color:white;
  }

.card_fft_container{
    position:relative;
    overflow:hidden;
    height:150px;
  }

  .card_fft_img {
    height:150px;
    position:absolute;
    margin-left: calc(50% + 93px);
    }

.card_fft_img_img {
  position:absolute;
  margin-left: calc(50%);
  display: block;
  height:150px;
  max-height:150px;
  width: auto;
  height: auto;
  border-color:black;
  border-style:solid;
  border-width:1px;
  }

.card_fft_control_left{
  width:calc(50% - 93px);
  height:150px;
  position:absolute;
  z-index:102;
  font-size:78px;
  text-align:center;
}

.card_fft_control_left i {
vertical-align: middle;
}

.card_fft_control_right {
  width:calc(50% - 93px);
  height:150px;
  position:absolute;
  right:0px;
  z-index:102;
  font-size:78px;
  text-align:center;
}

.card_fft_control_right i {
vertical-align: middle;
}

.database_audio_control{
  width:100%;
}
</style>

<div class="modal fade" id="loader_div">
  <div class="modal-dialog modal-dialog-centered text-center" role="document">
    <div class="loader m-auto d-inline-flex align-middle" role="document" id="loader_div"></div>
  </div>
</div>

<div class="alert alert-warning" style="display: none" id="alert_box">
  <span class="close" onclick="$('#alert_box').hide('slow');">
    <span aria-hidden="true">&times;</span>
  </span>
  <h4 class="alert-heading">Some information for you !</h4>
  <p id="alert_box_msg">Please contact administrators.</p>
</div>

<div class="modal fade" id="modal_new_classe" style="min-width:250px;">
  <div class="modal-dialog  modal-dialog-centered" role="document">
    <div class="modal-content">
      <div class="modal-header  text-white bg-success">
        <h5 class="modal-title" id="modal_info_title">New category</h5>
      </div>
      <form id="new-classe-form">
        <div class="modal-body">
          <input id="new_classe_name" class="form-control" type="text" placeholder="Category Name" required>
          <div class="custom-file">
            <input id="new_classe_img" class="custom-file-input" type="file" name="new_classe_img">
            <label class="custom-file-label" for="customFile">Category icon</label>
          </div>
          <textarea id="new_classe_description" class="form-control" placeholder="Category description" rows="5"></textarea>
        </div>
          <div class="modal-footer">
              <button type="button" class="btn btn-primary btn-lg btn-block" id="add_classe">Send</button>
              <button type="button" class="btn btn-primary btn-lg btn-block" onclick="$('#modal_new_classe').modal('hide');">Cancel</button>
          </div>
      </form>
    </div>
  </div>
</div>

<div class="modal fade" id="modal_new_audio_file" style="min-width:250px;">
  <div class="modal-dialog  modal-dialog-centered" role="document">
    <div class="modal-content">
      <div class="modal-header  text-white bg-success">
        <h5 class="modal-title" id="modal_info_title">Upload an audio file</h5>
      </div>
      <form id="new-audio_file-form">
        <div class="modal-body">
          <div class="d-flex flex-row">
            <input id="new_audiofile_category_input" class="form-control d-flex d-sm-none" type="text" placeholder="Category Name">
            <select id="new_audiofile_category_select" class="btn btn-gray btn-block d-flex w-100" placeholder="Category Name"></select>
            <button id="new_audiofile_category_create" type="button" class="btn btn-primary btn-lg btn-block h-100" style="width:60px;"><i class="fa fa-plus"></i></button>
          </div>
          <input id="new_audiofile_datetime" class="form-control d-flex" type="text" placeholder="Date & Time (yyyy-mm-ddThh:mm:ss)">
          <hr />
          <div class="custom-file">
            <input id="new_audiofile_file" class="custom-file-input" type="file" name="new_audio_file_img">
            <label class="custom-file-label" for="customFile">Your audio file (ogg / mp3 / wav)</label>
          </div>
          <hr />
          <span>Location</span>
          <div class="d-flex-row">
            <input id="new_audiofile_name" class="form-control d-flex" type="text" placeholder="Location name">
            <input id="new_audiofile_lat" class="form-control d-flex" type="text" placeholder="Latitude">
            <input id="new_audiofile_long" class="form-control d-flex" type="text" placeholder="Longitude">
          </div>
          <hr />
          <textarea id="new_audiofile_description" class="form-control" placeholder="Description" rows="5"></textarea>
          <div class="modal-footer">
              <button type="button" class="btn btn-primary btn-lg btn-block" id="new_audio_file">Send</button>
              <button type="button" class="btn btn-primary btn-lg btn-block" onclick="$('#modal_new_audio_file').modal('hide');">Cancel</button>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="container">
  <h2 class="my-4 text-center">
    Tid'Play
  </h2>
  <div>
    <div class="w-50" style="float:left;">
      <img src="static/img/photo/game.jpg" class="img-fluid border rounded" style="object-fit:contain; max-width:80%;">
    </div>
    <p class="text-justify">
      Tidzam uses deep learning technology in order to identify acoustic ambient sounds as well as bird species.
      Hence the system has to be taught by human which requires a lot of data for its training.
      This game based interface allows every users to help us in this task by labelling the proposed recordings.
    </p>
    <p class="text-justify">
        A system extracts automatically some recordings when Tidzam confidence is not enough high.
        This interface allows you to listen the recordings and write down what you can identify.
        Every information is crucial, even if you are not a bird expert, you can detect them as well as frogs, weather conditions, etc.
        All of yours records will be aggregated with ones of the other contributors in order to figure out what's going on in these recordings.
        And so to improve Tidzam.
    </p>
  </div>
  <br>

  <div class="card mt-3">
    <div class="card-header bg-success text-white">
      <h4>Help Us & Play</h4>
    </div>
    <div class="card-body border rounded m-1 p-2">
      <h5 class="card-title">How To play ?</h5>
      <p class="card-text text-justify">
        <ul>
          <li><b>Play & Navigate</b>: When the recording is played, you can visualize the audio spectrum in real-time.
                                      The footer menu allows you to select the category and the number of recordings that you want to display.
                                      The <q>unchecked</q> recordings are ones automatically extracted by Tidzam.
                                      If you could evaluate them, your help will be strongly appreciated.
          </li>
          <li><b>Write down</b>: When you recognize a sound during your listening, please feel free to drop a marker using the classe buttons.
                                      A classe can be refined, such as the bird classe, by specifing the specie if you know it.
                                      If a classe is missing, feel free to create a new one with the button <q>other</q> (if it's a new specie, go firstly in its sub classe before to create the new specie).
                                      If you make a mistake, you can delete your marker by moving the target area on it and then click on <q>Delete</q>.
          </li>
          <li><b>My History</b>:  The upper title indicates you how many recordings and answers you have already provided.
                                  By clicking on it, you can obtain the history of your contributions that you can visualize and correct if necessary.
          </li>
        </ul>
      </p>
    </div>
  </div>
  <div class="card_ok hide" id="card_ok">
    <div class="sa-icon sa-success animate">
      <span class="sa-line sa-tip animateSuccessTip"></span>
      <span class="sa-line sa-long animateSuccessLong"></span>
      <div class="sa-placeholder"></div>
      <div class="sa-fix"></div>
    </div>
  </div>
  <div>
    <div class="card mt-4 card_usergame">
        <div class="card-header d-flex flex-row align-middle justify-content-between bg-success text-white" id="card_usergame_header">
          <div id="card_usergame_title" class="d-flex w-100 justify-content-between"></div>
        </div>
    </div>
    <div class="alert alert-warning" style="display: none" id="div_user_recording_list">
      <span class="close" onclick="$('#div_user_recording_list').hide('slow');">
        <span aria-hidden="true">&times;</span>
      </span>
      <h4 class="alert-heading">Your audio files <span id="span_upload_count">#0</span></h4>
      <span id="btn_list_uploads"></span>
      <div id="div_user_upload_list_content"></div>
      <div class="d-flex flex-row justify-content-between">
        <div class="w-100 m-1"><input type="button" class="btn btn-gray w-100" value="Prev" id="btn_upload_prev" style="display:none;"></div>
        <div class="w-100 m-1"><input type="button" class="btn btn-gray w-100" value="Next" id="btn_upload_next"></div>
      </div>
      <h4 class="alert-heading">Your contributions <span id="span_contrib_count">#0</span></h4>
      <span id="btn_list_files"></span>
      <div id="div_user_recording_list_content"></div>
      <div class="d-flex flex-row justify-content-between">
        <div class="w-100 m-1"><input type="button" class="btn btn-gray w-100" value="Prev" id="btn_contrib_prev" style="display:none;"></div>
        <div class="w-100 m-1"><input type="button" class="btn btn-gray w-100" value="Next" id="btn_contrib_next"></div>
      </div>
    </div>
    <div id="cards"></div>
    <div class="card-footer row-sm bg-success-footer d-md-flex justify-content-between" id="card_usergame_footer">
      <div id="select_classe_div" class="col-sm-4 m-1" style="line-height:30px;">
        <div class="d-flex flex-row">
          <span class="d-inline align-middle">Category: </span>
          <select id="select_classe" class="btn btn-gray btn-block d-flex w-100"></select>
        </div>
      </div>
      <div class="col-sm-2 d-flex flex-row m-1" style="line-height:40px;">
        <span style="display:inline-block; vertical-align:middle">#</span>
        <div class="w-100 m-1">
          <select id="select_limit" class="btn btn-gray btn-block d-flex w-100">
            <option>1</option>
            <option>3</option>
            <option>5</option>
          </select>
        </div>
      </div>
      <div class="col-sm-1">
      </div>
      <div class="col-sm-2 d-flex flex-row justify-content-between">
        <div class="w-100 m-1"><input type="button" class="btn btn-gray w-100" value="Prev" id="btn_prev" style="display:none;"></div>
        <div class="w-100 m-1"><input type="button" class="btn btn-gray w-100" value="Next" id="btn_next"></div>
      </div>
    </div>
  </div>
  <a name="game_area"></a>
</div>
