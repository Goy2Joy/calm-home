(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.SaverPolicy=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function create(options){
    var generation=0,ready=false;
    return {
      canUseCustom:function(){return ready;},
      resume:function(){
        var current=++generation;ready=false;
        return options.setNative(false).then(function(){if(current===generation)ready=true;return ready;},function(){return false;});
      },
      suspend:function(){++generation;ready=false;return options.setNative(true).then(function(){return true;},function(){return false;});}
    };
  }
  return {create:create};
});
