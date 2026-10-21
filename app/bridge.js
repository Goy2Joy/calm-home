/* Bridge the reference UI to Calm Home's tested Samsung adapter. */
var TV = (function () {
  'use strict';
  var preview=new URLSearchParams(window.location.search).get('preview')==='1';
  var adapter=CalmTV.createAdapter({tizen:window.tizen,webapis:window.webapis,preview:preview});
  var saver=SaverPolicy.create({setNative:adapter.screenSaver});
  saver.resume();
  document.addEventListener('visibilitychange',function(){if(document.hidden)saver.suspend();else saver.resume();});
  window.addEventListener('pagehide',function(){saver.suspend();});
  window.addEventListener('beforeunload',function(){saver.suspend();});
  window.addEventListener('appcontrol',function(){if(!document.hidden)saver.resume();});
  function leaving(promiseFactory,done){
    var restoreRequired=saver.canUseCustom();
    call(saver.suspend().then(function(restored){
      if(restoreRequired && !restored)throw new Error('Could not restore the TV screensaver. Please try again.');
      return promiseFactory();
    }).catch(function(error){if(!document.hidden)saver.resume();throw error;}),done);
  }
  function report(error) {
    if(window.FreeMyTV)window.FreeMyTV.toast(error.message || String(error));
  }
  function call(promise,done) {
    promise.then(function () {if(done)done(true);},function (error) {report(error);if(done)done(false);});
  }
  if(preview) {
    window.addEventListener('load',function () {
      var badge=document.createElement('span');badge.textContent='Desktop preview';badge.className='preview-badge';document.getElementById('stage').appendChild(badge);
    });
  }
  return {
    name:preview?'browser':'tizen',
    canUseCustomSaver:function(){return preview || saver.canUseCustom();},
    apps:function (done) {
      adapter.listApps().then(function (list) {
        done(list.map(function (app) {return {id:app.id,title:app.name,icon:app.icon,color:''};}));
      },function (error) {report(error);done([]);});
    },
    launch:function (id,params,done) {
      if(preview && window.FreeMyTV)window.FreeMyTV.toast('Preview only');
      if(id.indexOf('source:HDMI:')===0) {
        leaving(function(){return adapter.switchSource('HDMI:'+id.split(':')[2]).then(function () {return adapter.leave('hide');});},done);
      } else if(id==='source:TV:1')leaving(function(){return adapter.launch('org.tizen.tv-viewer');},done);
      else leaving(function(){return adapter.launch(id);},done);
    },
    inputs:function (done) {
      adapter.listSources().then(function (sources) {
        done([{id:'source:TV:1',key:'live',label:'Live TV',symbol:'live_tv',connected:true}].concat(sources.map(function (source) {
          var number=source.id.split(':')[1];return {id:'source:HDMI:'+number,key:'hdmi'+number,label:source.name,symbol:'hdmi',connected:source.connected!==false};
        })));
      },function (error) {report(error);done([{id:'source:TV:1',key:'live',label:'Live TV',symbol:'live_tv',connected:true}]);});
    },
    settings:function (done) {leaving(function(){return adapter.launch(CalmTV.RECOVERY.settings);},done);},
    back:function () {leaving(function(){return adapter.leave('hide');});},
    zone:function () {
      try {if(window.tizen && window.tizen.time)return window.tizen.time.getLocalTimezone() || '';}catch(error){}
      try {return Intl.DateTimeFormat().resolvedOptions().timeZone || '';}catch(error){return '';}
    },
    keys:{left:37,up:38,right:39,down:40,ok:13,back:preview?27:10009}
  };
})();
