const test=require('node:test');const assert=require('node:assert/strict');
const History=require('../app/history.js');
function fixture(raw){let value=raw;return History.create({getItem:()=>value,setItem:(k,v)=>value=v});}
const title={id:32,kind:'tv',title:'A show',backdrop:'/show.jpg',appId:'netflix.App',appTitle:'Netflix'};
test('history persists only explicitly opened titles and moves a duplicate to the front',()=>{
 const h=fixture();assert.deepEqual(h.list(['netflix.App']),[]);
 h.record(title,100);h.record({...title,id:33,title:'Another'},200);h.record(title,300);
 assert.deepEqual(h.list(['netflix.App']).map(x=>[x.id,x.openedAt]),[[32,300],[33,200]]);
});
test('history drops malformed entries and filters uninstalled apps',()=>{
 const h=fixture('{bad json');assert.deepEqual(h.list([]),[]);
 h.record({...title,backdrop:'https://evil/image'},10);assert.deepEqual(h.list(['netflix.App']),[]);
 h.record(title,20);assert.deepEqual(h.list(['other.App']),[]);
});
test('history is bounded, survives reload, and can be cleared',()=>{
 let value;const store={getItem:()=>value,setItem:(k,v)=>value=v};const h=History.create(store);
 for(let id=0;id<30;id++)h.record({...title,id},id+1);
 assert.equal(History.create(store).list(['netflix.App']).length,12);
 h.clear();assert.deepEqual(h.list(['netflix.App']),[]);
});
