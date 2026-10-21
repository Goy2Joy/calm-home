(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./core.js'));
  else root.CalmTV = factory(root.CalmCore);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Core) {
  'use strict';
  var ID = /^[A-Za-z0-9_.-]{1,180}$/;
  var RECOVERY = {home:'com.samsung.tv.csfs',settings:'com.samsung.tv.coba.setting'};
  var NATIVE = ['org.tizen.netflix-app','org.tizen.primevideo','org.tizen.browser','org.tizen.apple.apple-music',
    'com.samsung.tv.cobalt-yt','com.samsung.tv.cobalt-yttv','com.samsung.tv.cobalt-ytkids','com.samsung.tv.store'];
  var ORDER = ['9Ur5IzDKqV.TizenYouTube','org.tizen.netflix-app','org.tizen.primevideo','LBUAQX1exg.Hulu',
    'MCmYXNxgcu.DisneyPlus','rJeHak5zRg.Spotify','com.samsung.tv.cobalt-yt'];
  var PREVIEW = [
    {id:"com.samsung.tv.store",name:"Samsung Apps"},
    {id:ORDER[0],name:'YouTube'}, {id:ORDER[1],name:'Netflix'}, {id:ORDER[2],name:'Prime Video'},
    {id:ORDER[3],name:'Hulu'}, {id:ORDER[4],name:'Disney+'}, {id:ORDER[5],name:'Spotify'},
    {id:'org.tizen.apple.apple-music',name:'Apple Music'}, {id:'gzcc4LRFBF.Peacock',name:'Peacock'}, {id:'3KA0pm7a7V.TubiTV',name:'Tubi'}, {id:'preview.hbo-max',name:'HBO Max'}, {id:'rJyOSqC6Up.CBSAllAccess',name:'Paramount+'}
  ];

  function apiError(error) {
    var name = error && error.name ? error.name : 'TV request failed';
    return new Error(name + (error && error.message ? ': ' + error.message : ''));
  }

  function createAdapter(options) {
    options = options || {};
    var platform = options.tizen;
    var vendor = options.webapis;
    var preview = options.preview === true;
    var timeout = typeof options.timeoutMs === 'number' && options.timeoutMs > 0 ? options.timeoutMs : 10000;

    function request(operation) {
      return new Promise(function (resolve, reject) {
        var settled = false;
        var timer = setTimeout(function () { finish(new Error('Timeout: the TV did not respond')); },timeout);
        function finish(error, value) {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          if (error) reject(error); else resolve(value);
        }
        try {
          operation(function (value) { finish(null,value); },function (error) { finish(apiError(error)); });
        } catch (error) { finish(apiError(error)); }
      });
    }

    function unavailable() {
      return Promise.reject(new Error('NotSupported: this TV interface is unavailable'));
    }

    function listApps() {
      if (preview) return Promise.resolve(Core.normalizeCatalog(PREVIEW));
      if (!platform || !platform.application || !platform.application.getAppsInfo) return unavailable();
      return request(function (ok, fail) { platform.application.getAppsInfo(ok,fail); }).then(function (rows) {
        var apps = Core.normalizeCatalog((Array.isArray(rows) ? rows : []).filter(function (app) {
          if (!app || app.id === 'CalmHome01.Home') return false;
          return NATIVE.indexOf(app.id) >= 0 || !/^(com\.samsung\.|org\.tizen\.)/.test(app.id);
        }).map(function (app) {
          return {id:app.id,name:app.id==='com.samsung.tv.store'?'Samsung Apps':app.name,icon:app.iconPath || app.icon || '',show:app.show};
        }));
        apps.sort(function (a,b) {
          var ai=ORDER.indexOf(a.id), bi=ORDER.indexOf(b.id);
          ai=ai < 0 ? 100 : ai; bi=bi < 0 ? 100 : bi;
          return ai-bi || a.name.localeCompare(b.name);
        });
        return apps;
      });
    }

    function launch(id) {
      if (typeof id !== 'string' || !ID.test(id)) return Promise.reject(new Error('Invalid application ID'));
      if (preview) return Promise.resolve({id:id,preview:true});
      if (id === RECOVERY.home) {
        if (!platform || !platform.ApplicationControl || !platform.application || !platform.application.launchAppControl) return unavailable();
        return request(function (ok,fail) {
          var control=new platform.ApplicationControl('http://tizen.org/appcontrol/operation/main');
          platform.application.launchAppControl(control,RECOVERY.home,function () {ok({id:id,preview:false});},fail);
        });
      }
      if (!platform || !platform.application || !platform.application.launch) return unavailable();
      return request(function (ok,fail) {
        platform.application.launch(id,function () { ok({id:id,preview:false}); },fail);
      });
    }

    function sourceDescriptors() {
      if (!platform || !platform.systeminfo || !platform.systeminfo.getPropertyValue || !platform.tvwindow || !platform.tvwindow.setSource) return unavailable();
      return request(function (ok,fail) { platform.systeminfo.getPropertyValue('VIDEOSOURCE',ok,fail); }).then(function (value) {
        var seen={},result=[];
        ['connected','disconnected'].forEach(function(group){
          (value && Array.isArray(value[group]) ? value[group] : []).forEach(function(source){
            if(!source || source.type!=='HDMI' || !Number.isInteger(source.number) || source.number<1 || seen[source.number])return;
            seen[source.number]=true;result.push({descriptor:source,connected:group==='connected'});
          });
        });
        return result.sort(function(a,b){return a.descriptor.number-b.descriptor.number;});
      });
    }

    function listSources() {
      if (preview) return Promise.resolve([{id:'HDMI:1',name:'HDMI 1',connected:true,kind:'source'},{id:'HDMI:2',name:'HDMI 2',connected:false,kind:'source'},{id:'HDMI:3',name:'HDMI 3',connected:false,kind:'source'}]);
      return sourceDescriptors().then(function (sources) {
        return sources.map(function (source) { var n=source.descriptor.number;return {id:'HDMI:'+n,name:'HDMI '+n,kind:'source',connected:source.connected}; });
      });
    }

    function switchSource(id) {
      if (preview) return Promise.resolve({id:id,preview:true});
      return sourceDescriptors().then(function (sources) {
        var entry = sources.filter(function (item) { return 'HDMI:'+item.descriptor.number === id; })[0];
        var source=entry && entry.descriptor;
        if (!source) throw new Error('This input is not connected');
        return request(function (ok,fail) {
          platform.tvwindow.setSource(source,function () { ok({id:id,name:'HDMI '+source.number,preview:false}); },fail,'MAIN');
        });
      });
    }

    function leave(action) {
      if (action !== 'hide' && action !== 'exit') return Promise.reject(new Error('Invalid exit action'));
      if (preview) return Promise.resolve({preview:true});
      if (!platform || !platform.application || !platform.application.getCurrentApplication) return unavailable();
      return Promise.resolve().then(function () { platform.application.getCurrentApplication()[action](); });
    }

    function screenSaver(enabled){
      if(preview)return Promise.resolve();
      var common=vendor && vendor.appcommon;
      if(!common || !common.setScreenSaver || !common.AppCommonScreenSaverState)return unavailable();
      var states=common.AppCommonScreenSaverState;
      return request(function(ok,fail){common.setScreenSaver(enabled?states.SCREEN_SAVER_ON:states.SCREEN_SAVER_OFF,ok,fail);});
    }

    return {mode:preview ? 'preview' : 'tv',listApps:listApps,launch:launch,listSources:listSources,switchSource:switchSource,leave:leave,screenSaver:screenSaver};
  }

  return {createAdapter:createAdapter,RECOVERY:RECOVERY};
});
