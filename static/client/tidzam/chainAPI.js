
function ChainAPI(){
  this.chainapiURL = "//chain-api.media.mit.edu";
  this.site_id     = 18

  this.getStreamsInfo = function(){
    streams = []
    rsp = $.ajax({
      type: "GET",
      dataType: 'json',
      url: this.chainapiURL+"/devices/?limit=3000&site_id="+this.site_id,
      async: false
      }).responseText

    sensors = JSON.parse(rsp)._links.items
    for (var i=0; i < sensors.length; i++){
      rsp = $.ajax({
        type: "GET",
        dataType: 'json',
        url: sensors[i].href,
        async: false
        }).responseText
      streams.push(JSON.parse(rsp))
      }
    return streams
  };


  this.list_devices = {}
  this.getData = function(target, callback_update){
    chain = this;
    site_id = 18;
  try {
        list_devices = $.ajax({
            type: "GET",
            url: this.chainapiURL+"/devices/?site_id="+site_id,
        }).done(function(list_devices){
        chain.list_devices = list_devices["_links"].items

        // For each devices
        for (var i=0; i<chain.list_devices.length;i++){
          chain.list_devices[i].href = chain.list_devices[i].href.replace("devices/", "/sensors/?device_id=") // Get sensor list url
          list_sensors = $.ajax({
              type: "GET",
              url: chain.list_devices[i].href,
              deviceID:i
          }).done(function(list_sensors){
          chain.list_devices[this.deviceID].list_sensors = list_sensors["_links"].items;
          for (var j=0; j< chain.list_devices[this.deviceID].list_sensors.length; j++){
              if (target.year){
                if (!target.month){
                  target.month_start = 1
                  target.month_end   = 12
                }
                else target.month_start = target.month_end = target.month
                if (!target.day){
                  target.day_start = 1
                  target.day_end   = (target.month_start<8&&target.month_start%2)||(target.month_start>7&&target.month_start%2==0)?31:30;
                }
                else target.day_start = target.day_end = target.day
                timestamp_gte = new Date(target.year+"-"+target.month_start+"-"+target.day_start+" 0:0:0").getTime()/1000;
                timestamp_lt = new Date(target.year+"-"+target.month_end+"-"+target.day_end+" 23:59:59").getTime()/1000;
              }
              else {
                timestamp_gte = 0
                timestamp_lt = Date.now()/1000;
              }

              chain.list_devices[this.deviceID].list_sensors[j].href = chain.list_devices[this.deviceID].list_sensors[j].href.replace("scalar_sensors/", "scalar_data/?sensor_id=")+"&timestamp__gte="+timestamp_gte+"&timestamp__lt="+timestamp_lt;
              deviceID = this.deviceID
              $.ajax({
                url:chain.list_devices[this.deviceID].list_sensors[j].href,
                list_devices: chain.list_devices,
                deviceID: deviceID,
                sensorID: j
                }).done(function(data){
                  if (callback_update){
                    callback_update("Loading channel " + chain.list_devices[this.deviceID].title +
                          " sensor " + chain.list_devices[this.deviceID].list_sensors[this.sensorID].title + ":  " +
                          data.data.length +" samples.");
                        }

                  chain.list_devices[this.deviceID].list_sensors[this.sensorID].data = data?data.data:[];
                });
              }
            });
          }
        });
      }
      catch(err){
        console.log("Chain API error" + err + "\n" + data)
      }
      return list_devices;
  }
}
