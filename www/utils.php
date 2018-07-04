<?php

ob_start();
session_start();

ini_set('display_errors', TRUE);
ini_set('display_startup_errors', TRUE);
error_reporting(E_ALL);

$PATH              = "https://tidzam.media.mit.edu";
$RECORDINGS_FOLDER = "/opt/tidzam/out-tidzam/";
$RECORDINGS_UPLOAD = "/opt/tidzam/out-tidzam/unchecked";
$CLASSES_UPLOAD    = "static/img/";

$mail_reporting    = "slash6475@duhart-clement.fr";

$action    = isset($_POST['action'])     ? $_POST['action']      : (isset($_GET['action'])? $_GET['action']   : NULL);
$id        = isset($_POST['id'])         ? $_POST['id']          : (isset($_GET['id'])    ? $_GET['id']       : NULL);
$user      = isset($_POST['user'])       ? $_POST['user']        : (isset($_SESSION["user"])?$_SESSION["user"]:"");
$user_id   = isset($_SESSION["user_id"]) ? $_SESSION["user_id"]  : NULL;
$pwd       = isset($_POST['password'])   ? $_POST['password']    : NULL;
$mail      = isset($_POST['mail'])       ? $_POST['mail']        : (isset($_SESSION["mail"])?$_SESSION["mail"]:"");
$status    = (isset($_SESSION["status"])?$_SESSION["status"]:"");

$return_error = "error";
$return_ok    = "success";

function postgres_connect(){
  $host        = "host = 127.0.0.1";
  $port        = "port = 5432";
  $dbname      = "dbname = tidzam";
  $credentials = "user = tidzam password=tidzam17";

  $db = pg_connect( "$host $port $dbname $credentials"  );
  if(!$db) echo "Error : Unable to open database\n";
  }

function control_admin(){
  $status = isset($_SESSION["status"])?$_SESSION["status"]:0;
  if ($status < 2) exit();
}

function control_user(){
  $status    = (isset($_SESSION["status"])?$_SESSION["status"]:"");
  if ($status < 1) {
    echo "<script language=\"javascript\">$('#login-modal').modal('show');</script>";
    exit();
  }
}

function glob_recursive($pattern, $flags = 0){
  $files = glob($pattern, $flags);
  foreach (glob(dirname($pattern).'/*', GLOB_ONLYDIR|GLOB_NOSORT) as $dir)
    $files = array_merge($files, glob_recursive($dir.'/'.basename($pattern), $flags));
  return $files;
}

function is_recording($file){
  $ret = pg_query_params("SELECT * FROM recordings WHERE \"recording\"=$1",
            array($file));
  if(!$ret) {
    echo($return_error."-postgres");
    exit();
  }
  return pg_num_rows($ret);
}


function upload_file($file, $dst, $type, $sizemax){
  if(!isset($sizemax)) $sizemax = 500000;
  if(isset($file)) {
      $uploadOk = 1;
      $imageFileType = strtolower(pathinfo(basename($file["name"]),PATHINFO_EXTENSION));
      $dst = $dst.".".$imageFileType;
      if (file_exists($dst)) {
        echo "Sorry, file already exists.";
        $uploadOk = 0;
        }
      if ($file["size"] > $sizemax) {
        echo "Sorry, your file is too large. Limit of ".$sizemax." Bytes. ";
        $uploadOk = 0;
        }
      if(isset($type) && !in_array($imageFileType, $type )) {
        echo "Wrong file format shoud be ";
        print_r ($type);
        $uploadOk = 0;
        }
      if ($uploadOk == 1) {
          if (move_uploaded_file($file["tmp_name"], $dst))
            return $dst;
      }
  }
  return "";
}
?>
