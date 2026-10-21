(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.CalmHistory=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  var KEY='calm.opened-titles.v1',LIMIT=12;
  function clean(row){
    if(!row || !Number.isInteger(row.id) || row.id<0 || !/^(tv|movie)$/.test(row.kind) ||
      typeof row.title!=='string' || !row.title.trim() || !/^\/[A-Za-z0-9_.-]+$/.test(row.backdrop) ||
      !/^[A-Za-z0-9_.-]{1,180}$/.test(row.appId) || !Number.isFinite(row.openedAt))return null;
    return {id:row.id,kind:row.kind,title:row.title.slice(0,180),backdrop:row.backdrop,
      appId:row.appId,appTitle:String(row.appTitle||row.appId).slice(0,100),openedAt:row.openedAt};
  }
  function create(store){
    function read(){
      try{var value=JSON.parse(store.getItem(KEY)||'[]');return Array.isArray(value)?value.map(clean).filter(Boolean).sort(function(a,b){return b.openedAt-a.openedAt;}).slice(0,LIMIT):[];}
      catch(error){return [];}
    }
    function write(rows){try{store.setItem(KEY,JSON.stringify(rows));}catch(error){}}
    return {
      list:function(installed){return read().filter(function(row){return installed.indexOf(row.appId)>=0;});},
      record:function(title,at){var row=clean(Object.assign({},title,{openedAt:at===undefined?Date.now():at}));if(!row)return;
        write([row].concat(read().filter(function(old){return !(old.id===row.id&&old.kind===row.kind&&old.appId===row.appId);})).slice(0,LIMIT));},
      clear:function(){write([]);}
    };
  }
  return {create:create};
});
