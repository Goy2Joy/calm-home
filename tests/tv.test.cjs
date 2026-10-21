const assert = require('node:assert/strict');
const test = require('node:test');
const TV = require('../app/tv.js');
const {createAdapter} = TV;

test('failed discovery stays a device error instead of silently presenting demo apps', async () => {
  const adapter=createAdapter({tizen:{application:{getAppsInfo(ok,fail){fail({name:'SecurityError'});}}},preview:false});
  await assert.rejects(adapter.listApps(),/SecurityError/);
  assert.equal(adapter.mode,'tv');
});

test('absent device APIs do not opt the TV into preview mode', async () => {
  const adapter=createAdapter({preview:false});
  await assert.rejects(adapter.listApps(),/NotSupported/);
  assert.equal(adapter.mode,'tv');
});

test('discovery keeps user apps but excludes hidden entries, system services and the launcher', async () => {
  const rows=[{id:'org.tizen.netflix-app',name:'Netflix',iconPath:'file:///netflix.png',show:true},
    {id:'LBUAQX1exg.Hulu',name:'Hulu',iconPath:'',show:true},
    {id:'com.samsung.tv.coba.adagent',name:'AdAgent',show:true},
    {id:'hidden.App',name:'Hidden',show:false},{id:'CalmHome01.Home',name:'Calm Home',show:true}];
  const adapter=createAdapter({tizen:{application:{getAppsInfo(ok){ok(rows);}}},preview:false});
  const apps=await adapter.listApps();
  assert.deepEqual(apps.map(app=>app.name),['Netflix','Hulu']);
  assert.equal(apps[0].icon,'file:///netflix.png');
});

test('a stale app launch is rejected and does not become preview success', async () => {
  const adapter=createAdapter({tizen:{application:{launch(id,ok,fail){assert.equal(id,'gone.App');fail({name:'NotFoundError'});}}},preview:false});
  await assert.rejects(adapter.launch('gone.App'),/NotFoundError/);
});

test('Samsung store is retained under a clear app-store name',async()=>{
 const adapter=createAdapter({tizen:{application:{getAppsInfo(ok){ok([{id:'com.samsung.tv.store',name:'APPS',show:true}]);}}}});
 assert.deepEqual((await adapter.listApps()).map(app=>[app.id,app.name]),[['com.samsung.tv.store','Samsung Apps']]);
});

test('invalid application IDs are rejected before a device operation', async () => {
  const adapter=createAdapter({tizen:{application:{launch(){throw new Error('must not launch malformed input');}}},preview:false});
  await assert.rejects(adapter.launch('../bad'),/Invalid/);
});

test('nonresponding TV APIs time out rather than trapping the interface busy', async () => {
  const adapter=createAdapter({tizen:{application:{launch(){}}},preview:false,timeoutMs:15});
  await assert.rejects(adapter.launch('valid.App'),/Timeout/);
});

test('preview actions remain explicitly marked preview', async () => {
  const adapter=createAdapter({preview:true});
  assert.equal(adapter.mode,'preview');
  const apps=await adapter.listApps();
  const result=await adapter.launch(apps[0].id);
  assert.equal(result.preview,true);
  assert.equal(result.id,apps[0].id);
});

test('source switching uses the real connected source descriptor and main window', async () => {
  const source={type:'HDMI',number:2};
  const tizen={systeminfo:{getPropertyValue(property,ok){assert.equal(property,'VIDEOSOURCE');ok({connected:[source,{type:'TV',number:0}]});}},
    tvwindow:{setSource(descriptor,ok,fail,type){assert.equal(descriptor,source);assert.equal(type,'MAIN');ok(source,'MAIN');}}};
  const adapter=createAdapter({tizen,preview:false});
  assert.deepEqual((await adapter.listSources()).map(item=>item.name),['HDMI 2']);
  const result=await adapter.switchSource('HDMI:2');
  assert.equal(result.name,'HDMI 2');
  await assert.rejects(adapter.switchSource('HDMI:9'),/not connected/);
});

test('unsupported source control is an explicit error', async () => {
  const adapter=createAdapter({tizen:{application:{}},preview:false});
  await assert.rejects(adapter.listSources(),/NotSupported/);
});

test('HDMI discovery includes disconnected physical ports and preserves their descriptors',async()=>{
 const connected={type:'HDMI',number:1};const sleeping={type:'HDMI',number:2};let selected;
 const adapter=createAdapter({tizen:{systeminfo:{getPropertyValue(key,ok){ok({connected:[connected],disconnected:[sleeping,connected,{type:'TV',number:0}]});}},tvwindow:{setSource(source,ok){selected=source;ok();}}}});
 const sources=await adapter.listSources();
 assert.deepEqual(sources.map(x=>[x.id,x.connected]),[['HDMI:1',true],['HDMI:2',false]]);
 await adapter.switchSource('HDMI:2');assert.equal(selected,sleeping);
});

test('Samsung Home recovery explicitly targets the stock Home main operation',async()=>{
 let requested;
 function Control(operation){this.operation=operation;}
 const adapter=TV.createAdapter({tizen:{ApplicationControl:Control,application:{
  launchAppControl(control,id,ok){requested={operation:control.operation,id};ok();},
  launch(){throw new Error('generic launch does not open stock Home');}
 }}});
 await adapter.launch(TV.RECOVERY.home);
 assert.deepEqual(requested,{operation:'http://tizen.org/appcontrol/operation/main',id:'com.samsung.tv.csfs'});
});

test('screensaver control uses Samsung’s real constants and reports errors',async()=>{
 const states=[];
 const webapis={appcommon:{AppCommonScreenSaverState:{SCREEN_SAVER_OFF:0,SCREEN_SAVER_ON:1},
   setScreenSaver(state,ok){states.push(state);ok();}}};
 const adapter=createAdapter({webapis});
 await adapter.screenSaver(false);await adapter.screenSaver(true);
 assert.deepEqual(states,[0,1]);
 await assert.rejects(createAdapter({}).screenSaver(false),/NotSupported/);
});
