console.log("🚀 JS de Filtros de Loorent cargado correctamente");

/**
 * admin_filter_dropdown.js
 *
 * Reads Django 4.1+ filter sidebar (<details data-filter-title>) to discover
 * URL parameters and PK values.  Option lists are built from the VISIBLE TABLE
 * CELLS, not from the sidebar, giving cumulative ("Excel-style") filtering:
 * after filtering by Empresa, the Ubicación dropdown shows only the locations
 * present in the current result set.
 *
 * Location.__str__ = "EMPRESA · Nombre · Pueblo", so sidebar labels contain
 * the cell text as a substring — used to recover the PK for FK navigation.
 * Boolean filters (is_cancelled) use a keyword heuristic because Django
 * renders "Sí"/"No" in the sidebar while cells show "🟢 Activo"/"🔴 Cancelado".
 *
 * TomSelect is initialized from the already-filtered <select>, so no
 * clearOptions / addOptions calls are needed after init.
 *
 * All visual styles live in admin_loorent_styles.css.
 */
(function () {
  'use strict';

  // ─── Minimal runtime CSS (sidebar hide must fire immediately) ────────────
  function injectStyle() {
    var el = document.createElement('style');
    el.textContent =
      '#changelist-filter { display: none !important; }\n' +
      '#changelist { width: 100% !important; float: none !important; }';
    document.head.appendChild(el);
  }

  // ─── Parse filter groups from <details data-filter-title> (Django 4.1+) ──
  // Returns [{title, paramName, items:[{label,value}]}]
  // items contains the full sidebar option list — used for PK lookup only.
  function parseGroups(panel) {
    var groups = [];

    panel.querySelectorAll('details').forEach(function (details) {
      var title = (details.getAttribute('data-filter-title') || '').trim();
      if (!title) {
        var summary = details.querySelector('summary');
        if (summary) {
          title = summary.textContent.trim().replace(/^(por|by)\s+/i, '').trim();
        }
      }
      if (!title) return;

      var ul = details.querySelector('ul');
      if (!ul) return;

      var lis = Array.from(ul.querySelectorAll('li'));
      if (lis.length < 2) return;

      // "All" reset link — first <li>
      var allA    = lis[0].querySelector('a');
      var allHref = allA ? (allA.getAttribute('href') || '?') : '?';
      var allQs   = allHref.includes('?') ? allHref.slice(allHref.indexOf('?') + 1) : '';
      var allP    = new URLSearchParams(allQs);

      // First specific option reveals the URL param name
      var specA = null;
      for (var i = 1; i < lis.length; i++) {
        specA = lis[i].querySelector('a');
        if (specA) break;
      }
      if (!specA) return;

      var specHref = specA.getAttribute('href') || '';
      var specQs   = specHref.includes('?') ? specHref.slice(specHref.indexOf('?') + 1) : specHref;
      var specP    = new URLSearchParams(specQs);

      var paramName = null;
      specP.forEach(function (val, key) {
        if (!paramName && !allP.has(key)) paramName = key;
      });
      if (!paramName) {
        specP.forEach(function (val, key) {
          if (!paramName && allP.get(key) !== val) paramName = key;
        });
      }
      if (!paramName) return;

      // Full sidebar option list (label + navigation value / PK)
      var items = [{ label: '— Todos —', value: '' }];
      for (var j = 1; j < lis.length; j++) {
        var a = lis[j].querySelector('a');
        if (!a) continue;
        var href = a.getAttribute('href') || '';
        var qs   = href.includes('?') ? href.slice(href.indexOf('?') + 1) : href;
        var p    = new URLSearchParams(qs);
        var v    = p.get(paramName);
        if (v !== null) items.push({ label: a.textContent.trim(), value: v });
      }

      console.log('[Filtros] Grupo:', title, '→', paramName, '(' + (items.length - 1) + ' opciones)');
      groups.push({ title: title, paramName: paramName, items: items });
    });

    return groups;
  }

  // ─── Column-class candidates from a URL param name ────────────────────────
  // Django URL params use __ as FK separator (location__company__id__exact)
  // but admin column CSS classes use _ from the Python method name
  // (column-location_company).  We add __ → _ normalized variants.
  function paramCandidates(param) {
    var seen = {}, out = [];
    function add(s) { if (s && !seen[s]) { seen[s] = 1; out.push(s); } }
    add(param);
    var a = param.replace(/__exact$/, '');  add(a);
    var b = a.replace(/__id$/, '');         add(b);
    var c = param.replace(/_exact$/, '');   add(c);
    add(param.split('__')[0]);
    add(a.split('__')[0]);
    add(b.split('__')[0]);
    add(c.split('__')[0]);
    // Single-underscore variants: location__company → location_company
    add(b.replace(/__/g, '_'));
    add(a.replace(/__/g, '_'));
    add(param.replace(/__/g, '_'));
    return out;
  }

  // Keyword fallback when both class-based and text-based lookups fail.
  var KEYWORD_MAP = [
    { words: ['cancelado', 'estado'],  cls: 'display_estado'   },
    { words: ['empresa', 'cliente'],   cls: 'location_company' },
    { words: ['ubicaci'],              cls: 'location_name'    },
    { words: ['pueblo', 'poble'],      cls: 'location_town'    },
  ];

  function findTh(group, ths) {
    // 1. Class-based (most reliable)
    var cands = paramCandidates(group.paramName);
    for (var i = 0; i < cands.length; i++) {
      for (var j = 0; j < ths.length; j++) {
        if (ths[j].classList.contains('column-' + cands[i])) return ths[j];
      }
    }
    // 2. Exact / prefix text match on column header
    var key = group.title.toLowerCase();
    for (var k = 0; k < ths.length; k++) {
      var anchor = ths[k].querySelector('.text a, a');
      var txt = ((anchor ? anchor.textContent : ths[k].textContent) || '').trim().toLowerCase();
      if (txt && (txt === key || txt.startsWith(key) || key.startsWith(txt))) return ths[k];
    }
    // 3. Keyword fallback
    for (var m = 0; m < KEYWORD_MAP.length; m++) {
      var entry = KEYWORD_MAP[m];
      var hit   = false;
      for (var n = 0; n < entry.words.length; n++) {
        if (key.indexOf(entry.words[n]) !== -1) { hit = true; break; }
      }
      if (hit) {
        for (var p2 = 0; p2 < ths.length; p2++) {
          if (ths[p2].classList.contains('column-' + entry.cls)) return ths[p2];
        }
      }
    }
    return null;
  }

  // ─── URL navigation ───────────────────────────────────────────────────────
  function doNavigate(paramName, value) {
    var p = new URLSearchParams(window.location.search);
    p.delete('p');
    if (value === '') p.delete(paramName);
    else p.set(paramName, value);
    var qs = p.toString();
    window.location.href = window.location.pathname + (qs ? '?' + qs : '');
  }

  // ─── Match cell text → sidebar item (for recovering PK / nav value) ──────
  // Strategy:
  //   • Location.__str__ = "EMPRESA · Nombre · Pueblo" → sidebar label contains
  //     the location name cell text → endsWith / includes match.
  //   • Company names: exact match.
  //   • TownFilter: value IS the town string → exact match.
  //   • Boolean (is_cancelled): sidebar labels are "Sí"/"No"; cell shows
  //     "🟢 Activo"/"🔴 Cancelado" → keyword heuristic on paramName.
  function matchCellToSidebarItem(cellText, sidebarItems, paramName) {
    var cellLow = cellText.toLowerCase().trim();

    for (var i = 0; i < sidebarItems.length; i++) {
      var item    = sidebarItems[i];
      if (!item.value) continue;
      var itemLow = item.label.toLowerCase().trim();

      if (itemLow === cellLow)                               return item; // exact
      if (cellLow.length > 2 && itemLow.endsWith(cellLow))  return item; // sidebar ends with cell
      if (cellLow.length > 2 && itemLow.includes(cellLow))  return item; // sidebar contains cell
      if (itemLow.length > 2 && cellLow.endsWith(itemLow))  return item; // cell ends with sidebar
      if (itemLow.length > 2 && cellLow.includes(itemLow))  return item; // cell contains sidebar
    }

    // Boolean fallback: Django renders "Sí"/"No" but cell shows "Activo"/"Cancelado"
    if (paramName && paramName.indexOf('cancel') !== -1) {
      if (cellLow.indexOf('activ') !== -1) {
        for (var j = 0; j < sidebarItems.length; j++) {
          if (sidebarItems[j].value === '0') return sidebarItems[j];
        }
      }
      if (cellLow.indexOf('cancel') !== -1) {
        for (var k = 0; k < sidebarItems.length; k++) {
          if (sidebarItems[k].value === '1') return sidebarItems[k];
        }
      }
    }

    return null;
  }

  // ─── Build option list from visible table cells ───────────────────────────
  // Reads unique cell texts from the column corresponding to th, maps each to
  // a sidebar item (for the navigation PK), and returns a deduplicated list.
  //
  // Falls back to group.items when:
  //   • the table has no data rows (empty result set), or
  //   • none of the cell texts could be matched to a sidebar item.
  //
  // The currently active filter value is always preserved in the list so the
  // user can clear it.
  function buildCellBasedOptions(group, th, curParams) {
    var thIndex = Array.from(th.parentElement.children).indexOf(th);
    if (thIndex === -1) return group.items;

    var tbl  = document.getElementById('result_list');
    var rows = Array.from(tbl.querySelectorAll('tbody tr'));
    var seenText = {}, orderedTexts = [];
    rows.forEach(function (row) {
      var cells = Array.from(row.children);
      var cell  = cells[thIndex];
      if (!cell) return;
      var text  = cell.textContent.trim();
      if (!text || text === '—') return;
      if (!seenText[text]) { seenText[text] = true; orderedTexts.push(text); }
    });

    // Empty table → keep full sidebar options so the user can still pick a value
    if (!orderedTexts.length) return group.items;

    var cur        = curParams.get(group.paramName) || '';
    var newItems   = [{ label: '— Todos —', value: '' }];
    var usedValues = {};

    orderedTexts.forEach(function (cellText) {
      var matched = matchCellToSidebarItem(cellText, group.items, group.paramName);
      if (matched && !usedValues[matched.value]) {
        usedValues[matched.value] = true;
        // Use cell text as display label (cleaner than sidebar label which may
        // include "EMPRESA · Nombre · Pueblo" for Location objects)
        newItems.push({ label: cellText, value: matched.value });
      } else if (!matched) {
        console.warn('[Filtros] Sin match sidebar para celda:', JSON.stringify(cellText),
                     '— grupo:', group.paramName);
      }
    });

    // Always keep the current active option so the user can deselect it
    if (cur && !usedValues[cur]) {
      for (var i = 0; i < group.items.length; i++) {
        if (group.items[i].value === cur) {
          newItems.push({ label: group.items[i].label, value: group.items[i].value });
          break;
        }
      }
    }

    // If matching produced no real options, fall back to full sidebar list
    return newItems.length > 1 ? newItems : group.items;
  }

  // ─── Create <select> element from an explicit item list ──────────────────
  function makeSelectFromItems(items, paramName, curParams) {
    var cur = curParams.get(paramName) || '';
    var sel = document.createElement('select');
    items.forEach(function (item) {
      var opt       = document.createElement('option');
      opt.value       = item.value;
      opt.textContent = item.label;
      if (item.value === cur) opt.selected = true;
      sel.appendChild(opt);
    });
    return sel;
  }

  // ─── Initialize Tom Select ────────────────────────────────────────────────
  // The <select> is already populated with filtered options before this call,
  // so TomSelect starts with the correct list — no clearOptions / addOptions.
  function applyTomSelect(sel, group, curParams) {
    var cur = curParams.get(group.paramName) || '';

    if (typeof TomSelect === 'undefined') {
      console.warn('[Filtros] TomSelect no disponible, usando select nativo');
      sel.addEventListener('change', function () {
        doNavigate(group.paramName, this.value);
      });
      return;
    }

    var ts = new TomSelect(sel, {
      create:     false,
      maxOptions: 300,
      sortField:  { field: 'text', direction: 'asc' },
      onChange:   function (value) {
        doNavigate(group.paramName, value);
      },
    });

    ts.wrapper.classList.add('th-flt-ts');
    if (cur) ts.wrapper.classList.add('flt-active');
  }

  // ─── Main ─────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    console.log('[Filtros] DOMContentLoaded');

    var panel = document.getElementById('changelist-filter');
    if (!panel) { console.log('[Filtros] Sin #changelist-filter'); return; }

    injectStyle();

    var tbl = document.getElementById('result_list');
    if (!tbl) { console.log('[Filtros] Sin #result_list'); return; }

    var groups    = parseGroups(panel);
    console.log('[Filtros] Grupos:', groups.length);
    if (!groups.length) return;

    var curParams = new URLSearchParams(window.location.search);
    var ths       = Array.from(tbl.querySelectorAll('thead th'));
    var unmatched = [];

    // ── Inject filters into column headers ───────────────────────────────
    groups.forEach(function (group) {
      var th = findTh(group, ths);
      if (!th) {
        console.warn('[Filtros] Sin columna para:', group.title, '/', group.paramName);
        unmatched.push(group);
        return;
      }
      console.log('[Filtros] Mapeado:', group.title, '→', th.className);

      var items = buildCellBasedOptions(group, th, curParams);

      var sel  = makeSelectFromItems(items, group.paramName, curParams);
      var wrap = document.createElement('div');
      wrap.appendChild(sel);
      th.appendChild(wrap);

      applyTomSelect(sel, group, curParams);
    });

    // ── Extra bar for filters that couldn't be matched to a column ───────
    if (unmatched.length) {
      var bar   = document.createElement('div');
      bar.id    = 'extra-flt-bar';
      var intro = document.createElement('span');
      intro.className   = 'ef-intro';
      intro.textContent = '⚙ Filtros:';
      bar.appendChild(intro);

      unmatched.forEach(function (group) {
        var grp = document.createElement('div');
        grp.className = 'ef-group';
        var lbl = document.createElement('span');
        lbl.className   = 'ef-label';
        lbl.textContent = group.title + ':';
        // Unmatched filters use full sidebar items (no corresponding column to read)
        var sel = makeSelectFromItems(group.items, group.paramName, curParams);
        grp.appendChild(lbl);
        grp.appendChild(sel);
        bar.appendChild(grp);
        applyTomSelect(sel, group, curParams);
      });

      tbl.parentNode.insertBefore(bar, tbl);
    }
  });
})();
