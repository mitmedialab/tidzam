<?php
require "utils.php";

postgres_connect();

switch($action){
  case "login":
    $ret = pg_query("SELECT * FROM users WHERE \"user\"='$user' AND \"password\"='$pwd'");
    if(!$ret) echo($return_error."-postgres");
    $row = pg_fetch_assoc($ret);
    if(!$row) {
      echo($return_error."-Bad user / password");
      break;
    }
    if(!$row["status"]){
      echo($return_error."-Account unactivated");
      break;
    }
    $_SESSION["user_id"]   = $row["id"];
    $_SESSION["user"]      = $row["user"];
    $_SESSION["mail"]      = $row["mail"];
    $_SESSION["status"]    = $row["status"];
    echo($return_ok);
    break;

  case "lostmail":
    $ret = pg_query("SELECT * FROM users WHERE \"mail\"='$mail'");
    if(!$ret) echo($return_error."-postgres");
    $row = pg_fetch_assoc($ret);
    if(!$row) {
      echo($return_ok);
      break;
    }
    $headers[] = 'MIME-Version: 1.0';
    $headers[] = 'Content-type: text/html; charset=iso-8859-1';
    $headers[] = 'From: No-reply <noreply@tidzam.media.mit.edu>';
    $headers[] = 'Reply-To: No-reply <noreply@tidzam.media.mit.edu>';
    $title  = "Tidzam Reset Password";
    $msg    = '<html><body><h3>Tid\'Zam Reset Password</h3><br>';
    $msg   .= 'Please click on the following link to reset your password<br> ';
    $msg   .= '<a href="'.$PATH.'/login.php?action=reset_password&id='.$row["activation_code"].'">'.$PATH.'/login.php?action=reset_password&id='.$row["activation_code"].'</a>';
    $msg   .= '</body></html>';

    if(!mail($mail,$title,$msg, implode("\r\n", $headers))){
      echo($return_error."-Internal mail error. Account not created.");
      break;
    }
    echo($return_ok);
    break;

  case "reset_password":
    if(isset($user) && isset($pwd) && isset($id)){
      $activation = hash("sha256", $user.$pwd);
      $ret = pg_query("UPDATE users SET \"user\"='$user',\"password\"='$pwd',\"activation_code\"='$activation' WHERE \"activation_code\"='$id'");
      if(!$ret) {
        echo("Unable to activate the account.");
        echo($return_error."Unable to change user/password");
      }
      else echo($return_ok);
    }
    else if (isset($id)){
      $ret = pg_query("SELECT * FROM users WHERE \"activation_code\"='$id'");
      $row = pg_fetch_assoc($ret);
      if(!$ret) {
        echo("Unable to activate the account.");
        echo(pg_last_error($db));
      }
      header('Location: '.$PATH.'/?action=reset_password&id='.$row["activation_code"].'&user='.$row["user"]);
    }

    break;

  case "register":
    $activation = hash("sha256", $user.$pwd);
    $ret = pg_query("INSERT INTO users (\"user\",\"password\",\"mail\",\"activation_code\") VALUES('$user','$pwd','$mail','$activation')");
    if(!$ret) {
      echo($return_error."-User already exist.");
      break;
    }
    $headers[] = 'MIME-Version: 1.0';
    $headers[] = 'Content-type: text/html; charset=iso-8859-1';
    $headers[] = 'From: No-reply <noreply@tidzam.media.mit.edu>';
    $headers[] = 'Reply-To: No-reply <noreply@tidzam.media.mit.edu>';
    $title  = "Tidzam Account Confirmation";
    $msg    = '<html><body><h3>Tid\'Zam Account Confirmation</h3><br>';
    $msg   .= 'Thanks for signing up.<br>';
    $msg   .= 'Please click on the following link to activate your account<br> ';
    $msg   .= '<a href="'.$PATH.'/login.php?action=account_confirmation&id='.$activation.'">'.$PATH.'/login.php?action=account_confirmation&id='.$activation.'</a>';
    $msg   .= '</body></html>';

    if(!mail($mail,$title,$msg, implode("\r\n", $headers))){
      pg_query("DELETE FROM users WHERE \"user\"='$user'");
      echo($return_error."-Internal mail error. Account not created.");
      break;
    }
    else echo($return_ok);
    break;

  case "account_confirmation":
        $ret = pg_query("UPDATE users SET \"status\"= 1 WHERE \"activation_code\"='$id'");
        if(!$ret) {
          echo("Unable to activate the account.");
          echo(pg_last_error($db));
        }
        $ret = pg_query("SELECT \"id\",\"user\" FROM users WHERE \"activation_code\"='$id'");
        $ret = pg_fetch_assoc($ret);
        $_SESSION["user_id"]     = $ret["id"];
        $_SESSION["user"]        = $ret["user"];
        $_SESSION["mail"]        = $row["mail"];
        $_SESSION["status"]      = $row["status"];
        header('Location: '.$PATH);
        break;

  case "user":
    echo $user.",".$mail;
    break;

  case "logout":
    session_destroy ();
    break;
}
?>
