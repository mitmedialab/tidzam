
function Menu (controller, parent) {

  this.parent = parent;
  this.id = new Date().getTime();

  this.parent.innerHTML += '<ul id="menu'+ this.id + '"> \
  <li class="ui-state-disabled">Tid\'Zam</li>\
  <li OnClick="controller.openConsole();">System Console</li>\
  <li OnClick="controller.openDetectionMap();">Detection Map</li>\
  </ul>\
  ';
  $( '#menu'+ this.id ).menu();
}
