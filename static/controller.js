/****************************************
*
/***************************************/
function Controller(parent){
  this.parent = parent;
  var conf = null;

  var map = this.map       = new DetectionMap(parent)

  // WINDOWS DECLARATION
  this.parent.innerHTML += '<div id="dialog-console" title="JSON WebSocket" ></div>'+
                           '<div id="dialog-console-data" title="JSON WebSocket data" ></div>';

  $( "#dialog-console-data" ).dialog({
    autoOpen: false,
    width: 272,
    modal: false,
  });
  $( "#dialog-console-data" ).html(
    '<div id="dialog-data-output" style="height:230px;"></div>'
  );
  $( "#dialog-console-data" ).attr('style','font-size:12px;');



  $( "#dialog-console" ).dialog({
    autoOpen: false,
    width: 272,
    modal: false,
  });
  $( "#dialog-console" ).html(
    '<div id="dialog-output" style="height:230px;"></div>' +
    '<input type="text" id="dialog-event" style="width:30px;" value="sys">'+
    '<input type="text" id="dialog-input" style="width:160px;">'+
    '<input type="button" id="dialog-send" value="Send">'
  );

  $( "#dialog-send" ).on("click", function(){
    console.log ("click " + $( "#dialog-event" ).val() + " " + $( "#dialog-input" ).val());
    socket.emit($( "#dialog-event" ).val(),$( "#dialog-input" ).val());
  });

  $( "#dialog-console" ).attr('style','font-size:12px;');


  this.openDetectionMap = function (){
    this.map.show();
  }

  this.openConsole = function(){
    $( "#dialog-console" ).dialog("open");
  };

  this.openDataConsole = function(){
    $( "#dialog-console-data" ).dialog("open");
  };

  // SOCKET. IO CONNECTOR
  socket.on('sys', function(msg){
      $( "#dialog-output" ).html(JSON.stringify(msg));
    });

  socket.on('data', function(msg){
    $( "#dialog-data-output" ).html(JSON.stringify(msg));
  });
}
