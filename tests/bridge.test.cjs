const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../app/bridge.js'),'utf8');
function fixture(search='',screenSaver=async()=>{}) {
  const calls=[],options=[],toasts=[];
  const adapter={listApps:async()=>[{id:'real.app',name:'Real app',icon:'file:///real.png'}],launch:async id=>{calls.push(['launch',id]);},
    listSources:async()=>[{id:'HDMI:2',name:'HDMI 2'}],switchSource:async id=>{calls.push(['source',id]);},leave:async mode=>{calls.push(['leave',mode]);}};
  const window={location:{search},addEventListener(){},FreeMyTV:{toast:text=>toasts.push(text)}};
  adapter.screenSaver=screenSaver;
  const document={hidden:false,addEventListener(){}};
  const context={URLSearchParams,Intl,window,document,SaverPolicy:require('../app/saver-policy.js'),CalmTV:{createAdapter:o=>{options.push(o);return adapter;},RECOVERY:{settings:'com.samsung.tv.coba.setting'}}};
  vm.runInNewContext(source,context);
  return {tv:context.TV,adapter,calls,options,toasts,document};
}
test('reference UI receives exact app IDs from the tested discovery adapter',async()=>{
 const f=fixture();const apps=await new Promise(resolve=>f.tv.apps(resolve));
 assert.equal(apps[0].id,'real.app');assert.equal(apps[0].title,'Real app');
});
test('TV Settings uses the verified Samsung recovery ID',async()=>{
 const f=fixture();assert.equal(await new Promise(resolve=>f.tv.settings(resolve)),true);
 assert.deepEqual(f.calls,[['launch','com.samsung.tv.coba.setting']]);
});
test('HDMI launch switches the selected real input before hiding the app',async()=>{
 const f=fixture();await new Promise(resolve=>f.tv.launch('source:HDMI:2',null,resolve));
 assert.deepEqual(f.calls,[['source','HDMI:2'],['leave','hide']]);
});
test('a failed app launch reports failure rather than preview success',async()=>{
 const f=fixture();f.adapter.launch=async()=>{throw new Error('Launch failed');};
 assert.equal(await new Promise(resolve=>f.tv.launch('real.app',null,resolve)),false);
 assert.deepEqual(f.toasts,['Launch failed']);
});
test('desktop preview stays explicitly opt-in after the UI replacement',()=>{
 assert.equal(fixture().options[0].preview,false);
 assert.equal(fixture('?preview=1').options[0].preview,true);
});

test('leaving waits for native screensaver restoration before launching',async()=>{
 let restore;const f=fixture('',enabled=>enabled?new Promise(resolve=>restore=resolve):Promise.resolve());
 await Promise.resolve();
 const pending=new Promise(resolve=>f.tv.launch('real.app',null,resolve));
 await Promise.resolve();assert.deepEqual(f.calls,[]);restore();await pending;
 assert.deepEqual(f.calls,[['launch','real.app']]);
});
test('a navigation failure after backgrounding never suppresses native saver again',async()=>{
 const states=[];const f=fixture('',async enabled=>states.push(enabled));await Promise.resolve();
 let rejectLaunch,entered;const started=new Promise(resolve=>entered=resolve);
 f.adapter.launch=()=>new Promise((resolve,reject)=>{rejectLaunch=reject;entered();});
 const pending=new Promise(resolve=>f.tv.launch('real.app',null,resolve));await started;
 f.document.hidden=true;rejectLaunch(new Error('late failure'));await pending;
 assert.deepEqual(states,[false,true]);
});
