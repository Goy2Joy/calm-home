(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CalmCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var ID = /^[A-Za-z0-9_.-]{1,180}$/;
  var THEMES = ['dusk', 'forest', 'ink'];

  function normalizeCatalog(apps) {
    var seen = Object.create(null);
    return (Array.isArray(apps) ? apps : []).filter(function (app) {
      if (!app || typeof app.id !== 'string' || !ID.test(app.id) || seen[app.id]) return false;
      if (app.show === false || app.display === false || app.app_nodisplay === 'true') return false;
      if (app.kind && app.kind !== 'app') return false;
      seen[app.id] = true;
      return true;
    }).map(function (app) {
      var icon = typeof app.icon === 'string' ? app.icon : '';
      if (/^(https?:|data:|javascript:|\/\/)/i.test(icon)) icon = '';
      return {id:app.id, name:typeof app.name === 'string' && app.name.trim() ? app.name.trim() : app.id, icon:icon, kind:'app'};
    });
  }

  function installedFavorites(favorites, catalog) {
    var allowed = Object.create(null), seen = Object.create(null);
    catalog.forEach(function (app) { allowed[app.id] = true; });
    return (Array.isArray(favorites) ? favorites : []).filter(function (id) {
      if (typeof id !== 'string' || !allowed[id] || seen[id]) return false;
      seen[id] = true;
      return true;
    });
  }

  function restorePreferences(raw, apps) {
    var catalog = normalizeCatalog(apps);
    var defaults = {version:1, favorites:catalog.slice(0,6).map(function (app) { return app.id; }), theme:'dusk', clock:true};
    var parsed;
    try { parsed = typeof raw === 'string' ? JSON.parse(raw) : null; }
    catch (error) { return defaults; }
    if (!parsed || Array.isArray(parsed) || parsed.version !== 1) return defaults;
    return {
      version:1,
      favorites:Array.isArray(parsed.favorites) ? installedFavorites(parsed.favorites,catalog) : defaults.favorites,
      theme:THEMES.indexOf(parsed.theme) >= 0 ? parsed.theme : 'dusk',
      clock:typeof parsed.clock === 'boolean' ? parsed.clock : true
    };
  }

  function moveIndex(index, key, count, columns) {
    count = Math.max(0, Math.floor(Number(count) || 0));
    if (!count) return -1;
    columns = Math.max(1, Math.floor(Number(columns) || 1));
    index = Math.max(0, Math.min(count-1, Math.floor(Number(index) || 0)));
    if (key === 'ArrowLeft') return index % columns ? index-1 : index;
    if (key === 'ArrowRight') return index % columns < columns-1 ? Math.min(count-1,index+1) : index;
    if (key === 'ArrowUp') return Math.max(0,index-columns);
    if (key === 'ArrowDown') return Math.min(count-1,index+columns);
    return index;
  }

  function editFavorites(favorites, action, id, apps) {
    var catalog = normalizeCatalog(apps);
    var result = installedFavorites(favorites,catalog);
    var index = result.indexOf(id);
    if (action === 'add' && index < 0 && catalog.some(function (app) { return app.id === id; })) result.push(id);
    if (action === 'remove' && index >= 0) result.splice(index,1);
    var destination = action === 'left' ? index-1 : action === 'right' ? index+1 : -1;
    if (index >= 0 && destination >= 0 && destination < result.length) {
      result.splice(index,1);
      result.splice(destination,0,id);
    }
    return result;
  }

  return {normalizeCatalog:normalizeCatalog, restorePreferences:restorePreferences, moveIndex:moveIndex, editFavorites:editFavorites};
});
