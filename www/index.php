<?php
session_start();
?>

<!doctype html>
<html lang="en">
<head>
  <title>Tidzam</title>

  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no, minimum-scale=1, maximum-scale=1, user-scalable=0">

  <link rel="icon" href="static/img/tidzam.png">
  <link rel="stylesheet" type="text/css" href="//fonts.googleapis.com/css?family=Lato">
  <link rel="stylesheet" type="text/css" href="//code.jquery.com/ui/1.11.4/themes/smoothness/jquery-ui.css">
  <link rel="stylesheet" type="text/css" href="//stackpath.bootstrapcdn.com/bootstrap/4.1.1/css/bootstrap.min.css" integrity="sha384-WskhaSGFgHYWDcbwN70/dfYBj47jz9qbsMId/iRN3ewGhXQFZCSftd1LZCfmhktB" crossorigin="anonymous">
  <link rel="stylesheet" type="text/css" href="static/font-awesome/css/all.css">
  <link rel="stylesheet" type="text/css" href="static/tidzam.css">

  <script src="//ajax.aspnetcdn.com/ajax/jQuery/jquery-3.3.1.min.js"></script>
  <script src="//code.jquery.com/ui/1.11.4/jquery-ui.js"></script>
  <script src="//cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js" integrity="sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49" crossorigin="anonymous"></script>
  <script src="//stackpath.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js" integrity="sha384-smHYKdLADwkXOn1EmN1qk/HfnUcbVRZyYmZ4qpPea6sjB/pTJ0euyQp0Mk8ck+5T" crossorigin="anonymous"></script>

  <script src="//cdn.socket.io/socket.io-1.2.0.js"></script>
  <script type="text/javascript" src="//www.google.com/jsapi"></script>
  <script async defer src="//maps.googleapis.com/maps/api/js?key=AIzaSyCt3oSqM5gPmb76_t67pXoP0nqCl6k_BrQ "></script>
  <script src="//rawgit.com/emn178/js-sha512/master/build/sha512.min.js"></script>

  <script type="text/javascript" src="static/js/lib.js"> </script>
  <script type="text/javascript" src="static/js/LiveStream.js"> </script>
  <script type="text/javascript" src="static/js/chainAPI.js"> </script>
  <script type="text/javascript" src="static/js/classifier_chart.js"> </script>

  <script>
  google.load('visualization', '1.1', {'packages':['line','corechart']});

    <!-- END LOGIN / REGISTER PAGE-->

  $( document ).ready(function() {
    set_logging();
    do_action();
    chain = new ChainAPI()
    menu_loader('main',0);
    });
  </script>
</head>

<body>
  <!---------------------------- MENU PAGE ------------------------->
  <nav class="navbar navbar-expand-lg navbar-dark navbar-main dropdown">
    <img class="navbar-brand" src="static/img/tidzam-white.png" height="30" class="d-inline-block align-top">
    <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#menu" aria-controls="#menu" aria-expanded="false" aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <div class="navbar-collapse collapse" id="menu">
      <ul class="navbar-nav mr-auto">
        <li class="nav-item">
          <a class="nav-link active" href="#" onclick="menu_loader('main',0);this.classList.add('active');">Home</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#" onclick="menu_loader('main',2);this.classList.add('active');">Tidmarsh</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#" onclick="menu_loader('main',3);this.classList.add('active');">Tid'Play</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#" onclick="menu_loader('main',4);this.classList.add('active');">Live Streams</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#" onclick="menu_loader('main',5);this.classList.add('active');">Identify Me</a>
        </li>
        <?PHP if (isset($_SESSION["status"])) if ($_SESSION["status"] > 1 ) { ?>
        <li class="nav-item dropdown">
          <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            Admin
          </a>
          <div class="dropdown-menu dropdown" aria-labelledby="navbarDropdown" id="menu_admin">
            <a class="dropdown-item" href="#" onclick="menu_loader('main',100);$('#menu_admin>a.active').removeClass('active');this.classList.add('active');">Sample Extractor</a>
            <a class="dropdown-item" href="#" onclick="menu_loader('main',102);$('#menu_admin>a.active').removeClass('active');this.classList.add('active');">Configuration</a>
            <div class="dropdown-divider"></div>
            <a class="dropdown-item" href="#" onclick="menu_loader('main',200);$('#menu_admin>a.active').removeClass('active');this.classList.add('active');">Tensorboard</a>
            <a class="dropdown-item" href="#" onclick="menu_loader('main',201);$('#menu_admin>a.active').removeClass('active');this.classList.add('active');">Logs</a>
            <a class="dropdown-item" href="#" onclick="menu_loader('main',202);$('#menu_admin>a.active').removeClass('active');this.classList.add('active');">Classifiers</a>
          </div>
        </li>
        <?PHP } ?>
      </ul>
    </div>

    <a href="#" id="user_label" class="navbar-text d-flex justify-content-end mr-3" onclick=""></a>
    <p id="mail_label"  class="navbar-text" style="display:none"></p>

    <div class="dropdown">
      <button type="button" class="btn btn-circle btn-xl" aria-label="Login Button" data-toggle="modal" data-target="#login-modal" id="btn_loggin">
        <i class="fa fa-user" aria-hidden="true"></i>
      </button>
      <div class="dropdown-menu dropdown-menu-right" aria-labelledby="dropdownMenuLogged">
        <a class="dropdown-item" href="#" id="btn_reset">Change user / password</a>
        <a class="dropdown-item" href="#" id="btn_logout">Logout</a>
      </div>
    </div>
  </nav>

  <!---------------------------- MODAL INFO ------------------------->
  <div class="modal fade" id="modal_info" style="min-width:250px;">
    <div class="modal-dialog  align-items-center" role="document">
      <div class="modal-content">
        <div class="modal-header  text-white bg-success">
          <h5 class="modal-title" id="modal_info_title"></h5>
        </div>
        <div class="modal-body text-black">
          <p id="modal_info_text"></p>
        </div>
      </div>
    </div>
  </div>

  <!---------------------------- LOGIN PAGE ------------------------->
  <div class="modal fade" id="login-modal" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true" style="display: none;">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header" align="center">
          <img class="img-circle" id="img_logo" src="static/img/tidzam.png" style="width:100%;">
          <button type="button" class="close" data-dismiss="modal" aria-label="Close">
            <span class="fa fa-remove" aria-hidden="true"></span>
          </button>
        </div>

        <!-- Begin # DIV Form -->
        <div id="div-forms">

          <!-- Begin # Login Form -->
          <form id="login-form">
            <div class="modal-body">
              <div id="div-login-msg">
                <div id="icon-login-msg" class="fa fa-chevron-right"></div>
                <span id="text-login-msg">Type your username and password.</span>
              </div>
              <input id="login_username" class="form-control" type="text" placeholder="Username" required>
              <input id="login_password" class="form-control" type="password" placeholder="Password" required>
              <div class="checkbox">
                <label>
                  <input type="checkbox"> Remember me
                </label>
              </div>
            </div>
            <div class="modal-footer">
              <div>
                <button type="submit" class="btn btn-primary btn-lg btn-block">Login</button>
              </div>
              <div>
                <button id="login_lost_btn" type="button" class="btn btn-link">Lost Password?</button>
                <button id="login_register_btn" type="button" class="btn btn-link">Register</button>
              </div>
            </div>
          </form>

          <form id="reset-form" style="display:none;">
            <div class="modal-body">
              <div id="div-login-msg">
                <div id="icon-login-msg" class="fa fa-chevron-right"></div>
                <span id="text-login-msg">Change your user / password.</span>
              </div>
              <input id="reset_username" class="form-control" type="text" placeholder="Username" required>
              <input id="reset_password" class="form-control" type="password" placeholder="Password" required>
            </div>
            <div class="modal-footer">
              <div>
                <button type="submit" class="btn btn-primary btn-lg btn-block">Reset</button>
              </div>
            </div>
          </form>
          <!-- End # Login Form -->

          <!-- Begin | Lost Password Form -->
          <form id="lost-form" style="display:none;">
            <div class="modal-body">
              <div id="div-lost-msg">
                <div id="icon-lost-msg" class="fa fa-chevron-right"></div>
                <span id="text-lost-msg">Type your e-mail.</span>
              </div>
              <input id="lost_email" class="form-control" type="text" placeholder="E-Mail" required>
            </div>
            <div class="modal-footer">
              <div>
                <button type="submit" class="btn btn-primary btn-lg btn-block">Send</button>
              </div>
              <div>
                <button id="lost_login_btn" type="button" class="btn btn-link">Log In</button>
                <button id="lost_register_btn" type="button" class="btn btn-link">Register</button>
              </div>
            </div>
          </form>
          <!-- End | Lost Password Form -->

          <!-- Begin | Register Form -->
          <form id="register-form" style="display:none;">
            <div class="modal-body">
              <div id="div-register-msg">
                <div id="icon-register-msg" class="fa fa-chevron-right"></div>
                <span id="text-register-msg">Register an account.</span>
              </div>
              <input id="register_username" class="form-control" type="text" placeholder="Username" required>
              <input id="register_email" class="form-control" type="text" placeholder="E-Mail" required>
              <input id="register_password" class="form-control" type="password" placeholder="Password" required>
            </div>
            <div class="modal-footer">
              <div>
                <button type="submit" class="btn btn-primary btn-lg btn-block">Register</button>
              </div>
              <div>
                <button id="register_login_btn" type="button" class="btn btn-link">Log In</button>
                <button id="register_lost_btn" type="button" class="btn btn-link">Lost Password?</button>
              </div>
            </div>
          </form>
          <!-- End | Register Form -->

        </div>
        <!-- End # DIV Form -->

      </div>
    </div>
  </div>

  <!---------------------- MAIN PAGE ------------------------->
  <div id="main"></div>
</body>
</html>
