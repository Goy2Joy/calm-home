const assert = require('node:assert/strict');
const test = require('node:test');
const core = require('../app/core.js');
const apps = [{id:'yt',name:'YouTube',kind:'app'}, {id:'nf',name:'Netflix',kind:'app'}, {id:'sp',name:'Spotify',kind:'app'}];

test('catalog excludes non-display services and invalid identifiers, preserving distinct apps', () => {
  const catalog = core.normalizeCatalog([...apps, apps[0], {id:'service',name:'Service',kind:'service'}, {id:'hidden',name:'Hidden',show:false}, {id:'../bad',name:'Bad'}, null]);
  assert.deepEqual(catalog.map(app => app.id), ['yt','nf','sp']);
});

test('catalog does not retain remote tracking images as app icons', () => {
  const rows=core.normalizeCatalog([{id:'a',name:'A',icon:'https://tracking.example/pixel'}, {id:'b',name:'B',icon:'file:///usr/apps/b/icon.png'}]);
  assert.equal(rows[0].icon,'');
  assert.equal(rows[1].icon,'file:///usr/apps/b/icon.png');
});

test('corrupt preferences recover to usable installed favorites', () => {
  const recovered = core.restorePreferences('{broken', apps);
  assert.equal(recovered.version, 1);
  assert.deepEqual(recovered.favorites, ['yt','nf','sp']);
  assert.equal(recovered.theme,'dusk');
  assert.equal(recovered.clock,true);
});

test('stale and duplicate favorites are removed without losing saved order', () => {
  const raw = JSON.stringify({version:1,favorites:['gone','sp','yt','sp'],theme:'dusk',clock:false});
  assert.deepEqual(core.restorePreferences(raw, apps), {version:1,favorites:['sp','yt'],theme:'dusk',clock:false});
});

test('an intentionally empty favorites list stays empty', () => {
  assert.deepEqual(core.restorePreferences(JSON.stringify({version:1,favorites:[]}),apps).favorites, []);
});

test('invalid preference fields cannot replace valid defaults', () => {
  const restored=core.restorePreferences(JSON.stringify({version:1,favorites:'bad',theme:'../remote',clock:'false'}),apps);
  assert.deepEqual(restored,{version:1,favorites:['yt','nf','sp'],theme:'dusk',clock:true});
});

test('directional keys respect partial-grid and row boundaries', () => {
  const cases = [[0,'ArrowLeft',5,4,0],[4,'ArrowRight',5,4,4],[3,'ArrowDown',5,4,4],[0,'ArrowUp',5,4,0],[3,'ArrowRight',5,4,3],[4,'ArrowLeft',5,4,4],[4,'ArrowUp',5,4,0],[0,'Enter',5,4,0],[0,'ArrowDown',0,4,-1],[0,'ArrowRight',1,4,0]];
  for (const [at,key,count,cols,want] of cases) assert.equal(core.moveIndex(at,key,count,cols),want,JSON.stringify([at,key]));
});

test('editing reorders favorites without mutating saved state', () => {
  const original=['yt','nf','sp'];
  assert.deepEqual(core.editFavorites(original,'left','nf',apps),['nf','yt','sp']);
  assert.deepEqual(core.editFavorites(original,'right','yt',apps),['nf','yt','sp']);
  assert.deepEqual(original,['yt','nf','sp']);
});

test('add/remove operations reject missing apps and never duplicate a favorite', () => {
  assert.deepEqual(core.editFavorites(['yt'],'add','nf',apps),['yt','nf']);
  assert.deepEqual(core.editFavorites(['yt'],'add','yt',apps),['yt']);
  assert.deepEqual(core.editFavorites(['yt'],'add','missing',apps),['yt']);
  assert.deepEqual(core.editFavorites(['yt','nf'],'remove','yt',apps),['nf']);
});

test('reset restores only launcher preferences and leaves the catalog unchanged', () => {
  const before=JSON.stringify(apps);
  assert.deepEqual(core.restorePreferences(null,apps).favorites,['yt','nf','sp']);
  assert.equal(JSON.stringify(apps),before);
});
