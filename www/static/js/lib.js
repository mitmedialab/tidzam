function GetURLParameter(sParam)
{
    var sPageURL = window.location.search.substring(1);
    var sURLVariables = sPageURL.split('&');
    for (var i = 0; i < sURLVariables.length; i++)
    {
        var sParameterName = sURLVariables[i].split('=');
        if (sParameterName[0] == sParam)
        {
            return sParameterName[1];
        }
    }
}

/* #####################################################################
#
#   Navigation System
#
##################################################################### */
function set_logging(){
  $.ajax("login.php?action=user").done(function(data){
      $("#user_label").text(data.split(",")[0]);
      $("#mail_label").text(data.split(",")[1]);
      if(data != ","){
        $("#btn_loggin").attr('data-target','dropdownMenuLogged');
        $("#btn_loggin").attr('data-toggle','dropdown');
      }
    });
}

function do_action(){
  switch(GetURLParameter("action")){
    case "reset_password":
      id_reset    = GetURLParameter("id");
      user        = GetURLParameter("user");
      $( "#lost-form" ).hide();
      $( "#register-form" ).hide();
      $( "#login-form" ).hide();
      $( "#reset-form").show();
      $( "#reset_username").val(user);
      $( "#reset_password").val("");
      $( "#login-modal").modal("show");
    break;
    default: break;
  }
}

function menu_loader(div_id, page){
  $("#menu").collapse("toggle");
  $("#menu>ul>li>a.active").removeClass("active");
  main = $( "#" + div_id)
  switch(page){
    default: ;
    case 0: $.ajax("static/home.html").done(function(data){main.html(data)});             break;
    case 1:  $.ajax("static/map.html").done(function(data){main.html(data)});             break;
    case 2:  $.ajax("static/tidmarsh.html").done(function(data){main.html(data)});        break;
    case 3: $.ajax("user-game.php").done(function(data){main.html(data)});                break;
    case 4:  $.ajax("static/audio-player.html").done(function(data){main.html(data)});    break;
    case 5:  $.ajax("static/identifyme.html").done(function(data){main.html(data)});      break;
    case 100:  $.ajax("admin-sample-extrator.php").done(function(data){main.html(data)}); break;
    case 102:  $.ajax("admin-control.php").done(function(data){main.html(data)});         break;
    case 200:  window.open("/tensorboard/");                                              break;
    case 201:  window.open("/logs/");                                                     break;
    case 202:  window.open("/classifiers/");                                              break;
  }
}


  <!-- START LOGIN / REGISTER PAGE-->
/* #####################################################################
#
#   Project       : Modal Login with jQuery Effects
#   Author        : Rodrigo Amarante (rodrigockamarante)
#   Version       : 1.0
#   Created       : 07/29/2015
#   Last Change   : 08/04/2015
#
##################################################################### */

$(function() {

  var $formLogin = $('#login-form');
  var $formLost = $('#lost-form');
  var $formRegister = $('#register-form');
  var $divForms = $('#div-forms');
  var $modalAnimateTime = 300;
  var $msgAnimateTime = 150;
  var $msgShowTime = 2000;

  $("form").submit(function () {
    switch(this.id) {
      case "login-form":
      $.ajax({
        type: "POST",
        url: "login.php",
        data: "&action=login&user=" + $('#login_username').val() + "&password=" + sha512($('#login_password').val()),
        success : function(text){
            if (text.indexOf("success") > -1)  {
              msgChange($('#div-login-msg'), $('#icon-login-msg'), $('#text-login-msg'), "success", "glyphicon-ok", "Login OK");
              $("#login-modal").modal("hide");
              location.reload();
            }
            else {
              msg = text.split("-")[1];
              msgChange($('#div-login-msg'), $('#icon-login-msg'), $('#text-login-msg'), "error", "glyphicon-error", msg);
            }
        }
      });
      return false;
      break;

      case "lost-form":
      var ls_email=$('#lost_email').val();
      $.ajax({
        type: "POST",
        url: "login.php",
        data: "&action=lostmail&mail=" + ls_email,
        success : function(text){
            if (text.indexOf("success") > -1)  {
              msgChange($('#div-lost-msg'), $('#icon-lost-msg'), $('#text-lost-msg'), "success", "glyphicon-ok", "Mail sent to" + ls_email);
              $("#login-modal").modal("hide");
              $("#modal_info_title").text("Reset password");
              $("#modal_info_text").text("An email has been sent to "+ls_email);
              $("#modal_info").modal("show");
            }
            else {
              msg = text.split("-")[1];
              msgChange($('#div-lost-msg'), $('#icon-lost-msg'), $('#text-lost-msg'), "error", "glyphicon-ok", msg);
          }
        }
      });
      return false;
      break;

      case "register-form":
      var $rg_username=$('#register_username').val();
      var $rg_email=$('#register_email').val();
      var $rg_password=$('#register_password').val();
      $.ajax({
        type: "POST",
        url: "login.php",
        data: "&action=register&user="+$rg_username+"&password="+sha512($rg_password)+"&mail=" + $rg_email,
        success : function(text){
            if (text.indexOf("success") > -1)  {
              msgChange($('#div-register-msg'), $('#icon-register-msg'), $('#text-register-msg'), "success", "glyphicon-ok", "Registration OK");
              $("#login-modal").modal("hide");
              $("#modal_info_title").text("Account creation");
              $("#modal_info_text").text("An email of confirmation has been sent to "+$rg_email);
              $("#modal_info").modal("show");
            }
            else {
              msg = text.split("-")[1];
              msgChange($('#div-register-msg'), $('#icon-register-msg'), $('#text-register-msg'), "error", "glyphicon-error", msg);
            }
        }
      });
      return false;
      break;

      case "reset-form":
      var $rg_username=$('#reset_username').val();
      var $rg_password=$('#reset_password').val();
      $.ajax({
        type: "POST",
        url: "login.php",
        data: "&action=reset_password&user="+$rg_username+"&password="+sha512($rg_password)+"&id=" + id_reset,
        success : function(text){
            $("#modal_info_title").text("Reset Password / User");
            if (text.indexOf("success") > -1)
              $("#modal_info_text").text("The password / user have been changed.");
            else {
              msg = text.split("-")[1];
              $("#modal_info_text").text(msg);
            }
        window.location.assign(location.protocol + '//' + location.host + location.pathname);
        }
      });
      return false;
      break;

      default:
      return false;
    }
  });

  $('#login_register_btn').click( function () { modalAnimate($formLogin, $formRegister) });
  $('#register_login_btn').click( function () { modalAnimate($formRegister, $formLogin); });
  $('#login_lost_btn').click( function () { modalAnimate($formLogin, $formLost); });
  $('#lost_login_btn').click( function () { modalAnimate($formLost, $formLogin); });
  $('#lost_register_btn').click( function () { modalAnimate($formLost, $formRegister); });
  $('#register_lost_btn').click( function () { modalAnimate($formRegister, $formLost); });

  $('#btn_logout').click(function(){
    $.ajax({
      url:"login.php?action=logout",
      success:function(){
        location.reload();
      }
    });
  })

  $('#btn_reset').click(function(){
    ls_email = $("#mail_label").text();
    $.ajax({
      type: "POST",
      url: "login.php",
      data: "&action=lostmail&mail=" + ls_email,
      success : function(text){
          if (text.indexOf("success") > -1)  {
            $("#modal_info_title").text("Reset password");
            $("#modal_info_text").text("An email has been sent to "+ls_email);
            $("#modal_info").modal("show");
          }
      }
    });
  });


  function modalAnimate ($oldForm, $newForm) {
    var $oldH = $oldForm.height();
    var $newH = $newForm.height();
    $divForms.css("height",$oldH);
    $oldForm.fadeToggle($modalAnimateTime, function(){
      $divForms.animate({height: $newH}, $modalAnimateTime, function(){
        $newForm.fadeToggle($modalAnimateTime);
      });
    });
  }

  function msgFade ($msgId, $msgText) {
    $msgId.fadeOut($msgAnimateTime, function() {
      $(this).text($msgText).fadeIn($msgAnimateTime);
    });
  }

  function msgChange($divTag, $iconTag, $textTag, $divClass, $iconClass, $msgText) {
    var $msgOld = $divTag.text();
    msgFade($textTag, $msgText);
    $divTag.addClass($divClass);
    $iconTag.removeClass("glyphicon-chevron-right");
    $iconTag.addClass($iconClass + " " + $divClass);
    setTimeout(function() {
      msgFade($textTag, $msgOld);
      $divTag.removeClass($divClass);
      $iconTag.addClass("glyphicon-chevron-right");
      $iconTag.removeClass($iconClass + " " + $divClass);
    }, $msgShowTime);
  }
});
