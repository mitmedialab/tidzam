
function ChainAPI(){
  this.getStreamsInfo = function(){
    streams = []
    try {
        list_streams = $.ajax({
            type: "GET",
            url: "http://chain-api.media.mit.edu/sensors/?device_id=22403",
            async: false
        }).responseText;
        list_streams = JSON.parse(list_streams)._links

        for (var i=0; i < list_streams.items.length; i++){
          stream = $.ajax({
              type: "GET",
              url: list_streams.items[i].href,
              async: false
          }).responseText;
          stream = JSON.parse(stream).geoLocation
          stream.name = list_streams.items[i].title
          streams.push(stream)
        }
      }
    catch(err){
      console.log("Chain API error" + err + "\n" + list_streams)
    }
    return streams
  };
}
