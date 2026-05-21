/**
 * Google Maps — links ràpids i autocomplete de zona
 *
 * Afegeix "↗ Obrir Google Maps" al costat de:
 *   - id_address       → cerca per text (carrer + població)
 *   - id_coords_cabin  → obre coordenades exactes
 *   - id_coords_entrance → obre coordenades exactes
 *   - id_latitude (DepotConfig) → obre coordenades exactes (combina lat + lng)
 *
 * Si id_address és un <input> (no textarea), activa Google Maps Autocomplete
 * per omplir automàticament població, codi postal i zona al seleccionar.
 */
(function () {
  'use strict';

  // ── Mapa municipio normalizado → zona ──────────────────────────────────
  const TOWN_ZONE = {
    'palma': 'PALMA', 'palma de mallorca': 'PALMA',
    'andratx': 'TRAMUNTANA', 'andrach': 'TRAMUNTANA',
    'banyalbufar': 'TRAMUNTANA', 'bañalbufar': 'TRAMUNTANA',
    'bunyola': 'TRAMUNTANA', 'buñola': 'TRAMUNTANA',
    'calvia': 'TRAMUNTANA',
    'deia': 'TRAMUNTANA', 'deya': 'TRAMUNTANA',
    'escorca': 'TRAMUNTANA',
    'esporles': 'TRAMUNTANA', 'esporlas': 'TRAMUNTANA',
    'estellencs': 'TRAMUNTANA', 'estellenchs': 'TRAMUNTANA',
    'fornalutx': 'TRAMUNTANA', 'fornaluch': 'TRAMUNTANA',
    'pollenca': 'TRAMUNTANA', 'pollensa': 'TRAMUNTANA',
    'puigpunyent': 'TRAMUNTANA', 'puigpunent': 'TRAMUNTANA',
    'soller': 'TRAMUNTANA',
    'valldemossa': 'TRAMUNTANA', 'valldemosa': 'TRAMUNTANA',
    'alaro': 'RAIGUER',
    'alcudia': 'RAIGUER',
    'binissalem': 'RAIGUER',
    'buger': 'RAIGUER',
    'campanet': 'RAIGUER',
    'consell': 'RAIGUER',
    'inca': 'RAIGUER',
    'lloseta': 'RAIGUER',
    'mancor de la vall': 'RAIGUER', 'mancor del valle': 'RAIGUER',
    'marratxi': 'RAIGUER', 'marrachi': 'RAIGUER',
    'sa pobla': 'RAIGUER', 'la puebla': 'RAIGUER',
    'santa maria del cami': 'RAIGUER', 'santa maria del camino': 'RAIGUER',
    'selva': 'RAIGUER',
    'algaida': 'PLA',
    'ariany': 'PLA',
    'costitx': 'PLA', 'costich': 'PLA',
    'lloret de vistalegre': 'PLA', 'lloret de vista alegre': 'PLA',
    'llubi': 'PLA',
    'maria de la salut': 'PLA', 'maria de la salud': 'PLA',
    'montuiri': 'PLA',
    'muro': 'PLA',
    'petra': 'PLA',
    'porreres': 'PLA', 'porreras': 'PLA',
    'sant joan': 'PLA', 'san juan': 'PLA',
    'santa eugenia': 'PLA',
    'santa margalida': 'PLA', 'santa margarita': 'PLA',
    'sencelles': 'PLA', 'sancellas': 'PLA',
    'sineu': 'PLA',
    'vilafranca de bonany': 'PLA', 'villafranca de bonany': 'PLA',
    'campos': 'MIGJORN',
    'felanitx': 'MIGJORN', 'felanich': 'MIGJORN',
    'llucmajor': 'MIGJORN',
    'ses salines': 'MIGJORN', 'las salinas': 'MIGJORN',
    'santanyi': 'MIGJORN',
    'arta': 'LLEVANT',
    'capdepera': 'LLEVANT',
    'manacor': 'LLEVANT',
    'sant llorenc des cardassar': 'LLEVANT', 'san lorenzo del cardezar': 'LLEVANT',
    'son servera': 'LLEVANT',
  };

  const POSTAL_ZONE = {
    '07001': 'PALMA', '07002': 'PALMA', '07003': 'PALMA', '07004': 'PALMA', '07005': 'PALMA',
    '07006': 'PALMA', '07007': 'PALMA', '07008': 'PALMA', '07009': 'PALMA', '07010': 'PALMA',
    '07011': 'PALMA', '07012': 'PALMA', '07013': 'PALMA', '07014': 'PALMA', '07015': 'PALMA',
    '07120': 'PALMA', '07198': 'PALMA', '07199': 'PALMA', '07600': 'PALMA', '07610': 'PALMA',
    '07110': 'TRAMUNTANA', '07193': 'TRAMUNTANA', '07190': 'TRAMUNTANA', '07140': 'TRAMUNTANA',
    '07150': 'TRAMUNTANA', '07157': 'TRAMUNTANA', '07160': 'TRAMUNTANA', '07170': 'TRAMUNTANA',
    '07180': 'TRAMUNTANA', '07181': 'TRAMUNTANA', '07184': 'TRAMUNTANA', '07460': 'TRAMUNTANA',
    '07470': 'TRAMUNTANA', '07340': 'TRAMUNTANA', '07100': 'TRAMUNTANA',
    '07300': 'RAIGUER', '07310': 'RAIGUER', '07320': 'RAIGUER', '07330': 'RAIGUER',
    '07350': 'RAIGUER', '07360': 'RAIGUER', '07141': 'RAIGUER', '07420': 'RAIGUER',
    '07430': 'RAIGUER', '07510': 'RAIGUER',
    '07144': 'PLA', '07210': 'PLA', '07220': 'PLA', '07230': 'PLA', '07240': 'PLA',
    '07250': 'PLA', '07260': 'PLA', '07313': 'PLA', '07440': 'PLA', '07450': 'PLA', '07458': 'PLA',
    '07620': 'MIGJORN', '07630': 'MIGJORN', '07640': 'MIGJORN', '07650': 'MIGJORN',
    '07660': 'MIGJORN', '07670': 'MIGJORN', '07680': 'MIGJORN', '07690': 'MIGJORN',
    '07500': 'LLEVANT', '07550': 'LLEVANT', '07560': 'LLEVANT', '07570': 'LLEVANT',
    '07580': 'LLEVANT', '07590': 'LLEVANT',
  };

  function norm(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }
  function zoneForTown(t)       { return TOWN_ZONE[norm(t)] || ''; }
  function zoneForPostalCode(cp) {
    var d = String(cp || '').replace(/\D/g, '');
    return d.length >= 5 ? (POSTAL_ZONE[d.slice(0, 5)] || '') : '';
  }
  function getComponent(comps, type, useShort) {
    var c = (comps || []).find(function (x) { return x.types.indexOf(type) !== -1; });
    return c ? (useShort ? c.short_name : c.long_name) : '';
  }

  // ── Estil comú per als links ───────────────────────────────────────────
  var LINK_CSS = 'font-size:.8em;color:#1a73e8;white-space:nowrap;display:inline-block;' +
                 'margin-left:8px;vertical-align:top;margin-top:4px;';
  var WRAP_CSS = 'display:flex;align-items:flex-start;gap:6px;';

  function makeLink(text) {
    var a = document.createElement('a');
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = text;
    a.style.cssText = LINK_CSS;
    return a;
  }

  function wrapWithLink(field, link) {
    var wrap = document.createElement('div');
    wrap.style.cssText = WRAP_CSS;
    field.parentNode.insertBefore(wrap, field);
    wrap.appendChild(field);
    wrap.appendChild(link);
  }

  // ── DOM ready ──────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('geocode-search-wrapper')) return;

    // ── 1. Widget de cerca + link al costat del camp Adreça ────────────
    var addrField = document.getElementById('id_address');
    if (addrField) {
      var addrLink = makeLink('↗ Obrir Google Maps');

      function buildAddrHref() {
        var text = addrField.value.trim();
        var town = (document.getElementById('id_town') || {}).value || '';
        var query = text && town ? text + ', ' + town : (text || town);
        return 'https://www.google.com/maps/search/' + encodeURIComponent(query || 'Mallorca');
      }
      function refreshAddrLink() { addrLink.href = buildAddrHref(); }
      refreshAddrLink();
      addrField.addEventListener('input', refreshAddrLink);
      addrField.addEventListener('change', refreshAddrLink);

      wrapWithLink(addrField, addrLink);

      // ── Quadre de cerca Google Maps (sense mapa) ──────────────────
      var wrapper = document.createElement('div');
      wrapper.id = 'geocode-search-wrapper';
      wrapper.style.cssText = 'margin-bottom:10px;padding:8px 10px;background:#f8f9fa;' +
                              'border:1px solid #dee2e6;border-radius:4px;';

      var label = document.createElement('p');
      label.style.cssText = 'margin:0 0 5px;font-weight:bold;font-size:.85em;color:#374151;';
      label.textContent = '🔍 Cercador d\'adreces (Google Maps)';
      wrapper.appendChild(label);

      var row = document.createElement('div');
      row.style.cssText = 'display:flex;gap:6px;align-items:center;';

      var searchInput = document.createElement('input');
      searchInput.id = 'geocode-input';
      searchInput.type = 'text';
      searchInput.placeholder = 'Ex: Avinguda Violetes, 18, Bunyola';
      searchInput.style.cssText = 'flex:1;min-width:240px;padding:5px 8px;';
      searchInput.setAttribute('autocomplete', 'off');

      var statusSpan = document.createElement('span');
      statusSpan.style.cssText = 'font-size:.82em;color:#666;';

      row.appendChild(searchInput);
      row.appendChild(statusSpan);
      wrapper.appendChild(row);

      var addrRow = addrField.closest('.form-row') || addrField.closest('div');
      addrRow.parentNode.insertBefore(wrapper, addrRow);

      // Esperar Google Maps API
      var attempts = 0;
      var timer = setInterval(function () {
        attempts++;
        if (window.google && window.google.maps && window.google.maps.places) {
          clearInterval(timer);
          initSearchWidget(searchInput, statusSpan);
        } else if (attempts > 60) {
          clearInterval(timer);
          statusSpan.textContent = 'Google Maps no disponible (comprova la API key)';
          statusSpan.style.color = '#c00';
        }
      }, 200);
    }

    // ── 2. Links al costat dels camps de coordenades "lat, lng" ────────
    function addCoordsLink(fieldId) {
      var field = document.getElementById(fieldId);
      if (!field) return;

      var link = makeLink('↗ Obrir Google Maps');

      function refresh() {
        var parts = field.value.trim().split(',');
        if (parts.length >= 2) {
          var lat = parseFloat(parts[0]), lng = parseFloat(parts[1]);
          if (!isNaN(lat) && !isNaN(lng)) {
            link.href = 'https://www.google.com/maps?q=' + lat.toFixed(6) + ',' + lng.toFixed(6);
            link.style.display = 'inline-block';
            return;
          }
        }
        link.style.display = 'none';
      }

      wrapWithLink(field, link);
      refresh();
      field.addEventListener('input', refresh);
      field.addEventListener('change', refresh);
    }

    addCoordsLink('id_coords_cabin');
    addCoordsLink('id_coords_entrance');

    // ── 3. Link per a DepotConfig (camps id_latitude + id_longitude) ───
    var latField = document.getElementById('id_latitude');
    var lngField = document.getElementById('id_longitude');
    if (latField && lngField) {
      var depotLink = makeLink('↗ Obrir Google Maps');

      function refreshDepot() {
        var lat = parseFloat(latField.value), lng = parseFloat(lngField.value);
        if (!isNaN(lat) && !isNaN(lng)) {
          depotLink.href = 'https://www.google.com/maps?q=' + lat.toFixed(6) + ',' + lng.toFixed(6);
          depotLink.style.display = 'inline-block';
        } else {
          depotLink.style.display = 'none';
        }
      }

      wrapWithLink(latField, depotLink);
      refreshDepot();
      latField.addEventListener('input', refreshDepot);
      latField.addEventListener('change', refreshDepot);
      lngField.addEventListener('input', refreshDepot);
      lngField.addEventListener('change', refreshDepot);
    }

  });

  // ── Inicialitza el quadre de cerca (sense mapa) ───────────────────────
  function initSearchWidget(searchInput, statusSpan) {
    var ac = new window.google.maps.places.Autocomplete(searchInput, {
      componentRestrictions: { country: 'es' },
      fields: ['address_components', 'geometry'],
      types: ['address'],
    });
    ac.setBounds(new window.google.maps.LatLngBounds(
      { lat: 39.26, lng: 2.30 }, { lat: 39.97, lng: 3.48 }
    ));
    ac.addListener('place_changed', function () {
      var place = ac.getPlace();
      if (!place || !place.address_components) {
        statusSpan.textContent = 'No s\'ha trobat l\'adreça. Torna-ho a provar.';
        return;
      }
      applyComponents(place.address_components);
      if (place.geometry && place.geometry.location) {
        var lat = place.geometry.location.lat();
        var lng = place.geometry.location.lng();
        var latFld = document.getElementById('id_latitude');
        var lngFld = document.getElementById('id_longitude');
        if (latFld) latFld.value = lat.toFixed(6);
        if (lngFld) lngFld.value = lng.toFixed(6);
        if (latFld) latFld.dispatchEvent(new Event('change'));
      }
      statusSpan.textContent = '✔ Seleccionat';
      statusSpan.style.color = '#166534';
      setTimeout(function () { statusSpan.textContent = ''; }, 3000);
      searchInput.value = '';
    });
  }

  function applyComponents(comps) {
    var street   = getComponent(comps, 'route', false);
    var num      = getComponent(comps, 'street_number', false);
    var addrFld  = document.getElementById('id_address');
    if (addrFld && street) addrFld.value = street + (num ? ', ' + num : '');

    var town = getComponent(comps, 'locality', false)
            || getComponent(comps, 'administrative_area_level_3', false);
    var townFld = document.getElementById('id_town');
    if (townFld && town) townFld.value = town;

    var cp = getComponent(comps, 'postal_code', false);
    var cpFld = document.getElementById('id_postal_code');
    if (cpFld && cp) cpFld.value = cp;

    var zone = zoneForPostalCode(cp)
            || zoneForTown(getComponent(comps, 'administrative_area_level_3', false))
            || zoneForTown(town);
    var zoneSel = document.getElementById('id_zone');
    if (zoneSel && zone) {
      zoneSel.value = zone;
      zoneSel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

})();
