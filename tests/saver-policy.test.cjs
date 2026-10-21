const test=require('node:test');const assert=require('node:assert/strict');
const {create}=require('../app/saver-policy.js');

test('custom saver is allowed only after Samsung suppression succeeds',async()=>{
 const calls=[];const p=create({setNative:async enabled=>calls.push(enabled)});
 assert.equal(p.canUseCustom(),false);await p.resume();assert.equal(p.canUseCustom(),true);
 await p.suspend();assert.equal(p.canUseCustom(),false);assert.deepEqual(calls,[false,true]);
});
test('failure leaves the app saver off so two savers do not stack',async()=>{
 const p=create({setNative:async()=>{throw new Error('unsupported');}});
 assert.equal(await p.resume(),false);assert.equal(p.canUseCustom(),false);
});
test('a stale disable callback cannot reactivate a hidden app saver',async()=>{
 let finish;const calls=[];const p=create({setNative:enabled=>{calls.push(enabled);return enabled?Promise.resolve():new Promise(resolve=>finish=resolve);}});
 const pending=p.resume();await p.suspend();finish();await pending;
 assert.equal(p.canUseCustom(),false);assert.deepEqual(calls,[false,true]);
});
