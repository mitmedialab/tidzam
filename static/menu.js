
function Menu (controller, parent) {

  this.parent = parent;
  this.id = new Date().getTime();


  this.recorder = {
    add:function(){
      console.log("add");
    }
  };

  this.parent.innerHTML += '<ul id="menu'+ this.id + '"> \
  <li class="ui-state-disabled">Tid\'Zam</li>\
  <li>Admin\
  <ul> \
    <li>Init \
      <ul><li OnClick="controller.raz();">RAZ - Delete All</li></ul>\
    </li>\
    <li OnClick="controller.openConsole();">System Console</li>\
    <li OnClick="controller.openDataConsole();"> JSON WebSocket data</li>\
  </ul></li>\
  <li OnClick="recorder.show()"> Learning</li>          \
  <li>Interfaces\
  <ul> \
  <li OnClick="controller.openPlayer();">System Control </li>\
  <li OnClick="controller.openSpeakerstats();">Stream Analysis</li>\
  <li OnClick="controller.openNeuralOutputs();">Classifier Management</li>\
  </ul>\
  </li> \
  </ul>\
  ';
  $( '#menu'+ this.id ).menu();
}
