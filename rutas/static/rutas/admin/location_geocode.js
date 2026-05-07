/**
 * Geocodificación de ubicaciones — Django Admin
 * API: Google Maps (Places Autocomplete + Geocoding)
 *
 * Requiere que la página cargue el script de Google Maps con &libraries=places
 * (lo hace el template admin/rutas/location/change_form.html).
 *
 * Al seleccionar un resultado rellena automáticamente:
 *   address, town, postal_code, zone, latitude, longitude + mapa Google.
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
    // --- PALMA ---
    '07001': 'PALMA', '07002': 'PALMA', '07003': 'PALMA', '07004': 'PALMA', '07005': 'PALMA',
    '07006': 'PALMA', '07007': 'PALMA', '07008': 'PALMA', '07009': 'PALMA', '07010': 'PALMA',
    '07011': 'PALMA', '07012': 'PALMA', '07013': 'PALMA', '07014': 'PALMA', '07015': 'PALMA',
    '07120': 'PALMA', '07198': 'PALMA', '07199': 'PALMA', '07600': 'PALMA', '07610': 'PALMA',

    // --- TRAMUNTANA ---
    '07110': 'TRAMUNTANA',
    '07193': 'TRAMUNTANA',
    '07190': 'TRAMUNTANA',
    '07140': 'TRAMUNTANA',
    '07150': 'TRAMUNTANA',
    '07157': 'TRAMUNTANA',
    '07160': 'TRAMUNTANA',
    '07170': 'TRAMUNTANA',
    '07180': 'TRAMUNTANA',
    '07181': 'TRAMUNTANA',
    '07184': 'TRAMUNTANA',
    '07460': 'TRAMUNTANA',
    '07470': 'TRAMUNTANA',
    '07340': 'TRAMUNTANA',
    '07100': 'TRAMUNTANA',

    // --- RAIGUER ---
    '07300': 'RAIGUER',
    '07310': 'RAIGUER',
    '07320': 'RAIGUER',
    '07330': 'RAIGUER',
    '07350': 'RAIGUER',
    '07360': 'RAIGUER',
    '07141': 'RAIGUER',
    '07420': 'RAIGUER',
    '07430': 'RAIGUER',
    '07510': 'RAIGUER',

    // --- PLA ---
    '07144': 'PLA',
    '07210': 'PLA',
    '07220': 'PLA',
    '07230': 'PLA',
    '07240': 'PLA',
    '07250': 'PLA',
    '07260': 'PLA',
    '07313': 'PLA',
    '07440': 'PLA',
    '07450': 'PLA',
    '07458': 'PLA',

    // --- MIGJORN ---
    '07620': 'MIGJORN',
    '07630': 'MIGJORN',
    '07640': 'MIGJORN',
    '07650': 'MIGJORN',
    '07660': 'MIGJORN',
    '07670': 'MIGJORN',
    '07680': 'MIGJORN',
    '07690': 'MIGJORN',

    // --- LLEVANT ---
    '07500': 'LLEVANT',
    '07550': 'LLEVANT',
    '07560': 'LLEVANT',
    '07570': 'LLEVANT',
    '07580': 'LLEVANT',
    '07590': 'LLEVANT',
  };

  function norm(s) {
    return (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  }
  function zoneForTown(t) { return TOWN_ZONE[norm(t)] || ''; }
  function normalizePostalCode(cp) {
    var digits = String(cp || '').replace(/\D/g, '');
    return digits.length >= 5 ? digits.slice(0, 5) : '';
  }
  function zoneForPostalCode(cp) {
    var normalized = normalizePostalCode(cp);
    return normalized ? (POSTAL_ZONE[normalized] || '') : '';
  }

  /** Extrae el valor de un tipo de componente del result de Google */
  function getComponent(components, type, useShort) {
    var c = (components || []).find(function (x) { return x.types.indexOf(type) !== -1; });
    return c ? (useShort ? c.short_name : c.long_name) : '';
  }

  // ── DOM ready ─────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('geocode-search-wrapper')) return;

    var addrField = document.getElementById('id_address');
    if (!addrField) return;

    var latField       = document.getElementById('id_latitude');
    var lngField       = document.getElementById('id_longitude');
    var townField      = document.getElementById('id_town');
    var municipalityFld = document.getElementById('id_municipality');
    var postalFld      = document.getElementById('id_postal_code');
    var zoneSelect     = document.getElementById('id_zone');
    var geocoder       = null;

    // ── construir widget ─────────────────────────────────────────────
    var wrapper = document.createElement('div');
    wrapper.id = 'geocode-search-wrapper';
    wrapper.style.cssText = 'margin-bottom:10px;padding:10px;background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;';

    var label = document.createElement('p');
    label.style.cssText = 'margin:0 0 6px;font-weight:bold;font-size:.9em;';
    label.textContent = String.fromCodePoint(0x1F5FA) + ' Buscador de direccion (Google Maps)';
    wrapper.appendChild(label);

    var row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;align-items:center;';

    var searchInput = document.createElement('input');
    searchInput.id = 'geocode-input';
    searchInput.type = 'text';
    searchInput.placeholder = 'Ej: Avinguda Violetes, 18, Bunyola';
    searchInput.style.cssText = 'flex:1;min-width:240px;padding:6px 8px;';
    searchInput.setAttribute('aria-label', 'Buscar direccion en Google Maps');

    var statusSpan = document.createElement('span');
    statusSpan.style.cssText = 'font-size:0.85em;color:#666;';

    row.appendChild(searchInput);
    row.appendChild(statusSpan);
    wrapper.appendChild(row);

    var mapDiv = document.createElement('div');
    mapDiv.id = 'geocode-map';
    mapDiv.style.cssText = 'width:100%;height:260px;border:1px solid #ccc;display:none;margin-top:8px;border-radius:4px;';
    wrapper.appendChild(mapDiv);

    var addrRow = addrField.closest('.form-row') || addrField.closest('div');
    addrRow.parentNode.insertBefore(wrapper, addrRow);

    // ── esperar a que la API de Google esté lista ─────────────────────
    var attempts = 0;
    var timer = setInterval(function () {
      attempts++;
      if (window.google && window.google.maps && window.google.maps.places) {
        clearInterval(timer);
        initAutocomplete();
      } else if (attempts > 60) {
        clearInterval(timer);
        statusSpan.textContent = 'Error: Google Maps no cargó. Comprueba la API key en .env';
        statusSpan.style.color = '#c00';
      }
    }, 200);

    // ── mapa existente al editar ──────────────────────────────────────
    if (latField && lngField && latField.value.trim() && lngField.value.trim()) {
      var attempts2 = 0;
      var timer2 = setInterval(function () {
        attempts2++;
        if (window.google && window.google.maps) {
          clearInterval(timer2);
          showMap(parseFloat(latField.value), parseFloat(lngField.value));
        } else if (attempts2 > 60) { clearInterval(timer2); }
      }, 200);
    }

    function initAutocomplete() {
      var autocomplete = new window.google.maps.places.Autocomplete(searchInput, {
        componentRestrictions: { country: 'es' },
        fields: ['address_components', 'geometry', 'formatted_address', 'name'],
        types: ['address'],
      });

      // Centrar sugerencias en Mallorca
      var mallorcaBounds = new window.google.maps.LatLngBounds(
        { lat: 39.26, lng: 2.30 },
        { lat: 39.97, lng: 3.48 }
      );
      autocomplete.setBounds(mallorcaBounds);

      autocomplete.addListener('place_changed', function () {
        var place = autocomplete.getPlace();
        if (!place.geometry) {
          statusSpan.textContent = 'No se encontro la direccion. Prueba de nuevo.';
          return;
        }
        applyPlace(place);
        statusSpan.textContent = String.fromCodePoint(0x2714) + ' Seleccionado';
      });

      geocoder = new window.google.maps.Geocoder();
    }

    function applyAddressComponents(comps, fallbackAddress) {
      // calle + numero
      var street = getComponent(comps, 'route', false);
      var num    = getComponent(comps, 'street_number', false);
      addrField.value = street && num ? street + ', ' + num : (street || fallbackAddress || '');

      // municipio para mostrar en el campo "town"
      var displayTown = getComponent(comps, 'locality', false)
                     || getComponent(comps, 'administrative_area_level_3', false)
                     || getComponent(comps, 'postal_town', false);
      if (townField && displayTown) townField.value = displayTown;

      // municipio administrativo real
      var municipalityVal = getComponent(comps, 'administrative_area_level_3', false)
                         || getComponent(comps, 'locality', false);
      if (municipalityFld && municipalityVal) municipalityFld.value = municipalityVal;

      // codigo postal
      var cp = getComponent(comps, 'postal_code', false);
      if (postalFld && cp) postalFld.value = cp;

      // zona comarca: prioridad por codigo postal y fallback por municipio/poblacion
      var zoneCandidates = [
        getComponent(comps, 'administrative_area_level_3', false),
        getComponent(comps, 'locality', false),
        getComponent(comps, 'postal_town', false),
        getComponent(comps, 'administrative_area_level_2', false),
      ];
      var detectedByPostal = zoneForPostalCode(cp);
      var detectedZone = '';
      var zoneSourceTown = '';
      var zoneSourceLabel = '';

      if (detectedByPostal) {
        detectedZone = detectedByPostal;
        zoneSourceTown = normalizePostalCode(cp);
        zoneSourceLabel = 'CP';
      } else {
        for (var i = 0; i < zoneCandidates.length; i++) {
          if (zoneCandidates[i]) {
            var z = zoneForTown(zoneCandidates[i]);
            if (z) {
              detectedZone = z;
              zoneSourceTown = zoneCandidates[i];
              zoneSourceLabel = 'municipio';
              break;
            }
          }
        }
      }

      if (!zoneSelect) return;

      if (detectedZone) {
        zoneSelect.value = detectedZone;
        zoneSelect.dispatchEvent(new Event('change', { bubbles: true }));
        zoneSelect.style.background = '#d4edda';
        setTimeout(function () { zoneSelect.style.background = ''; }, 2000);
        statusSpan.textContent = String.fromCodePoint(0x2714)
          + ' Seleccionado · Zona: ' + zoneSelect.options[zoneSelect.selectedIndex].text
          + ' (via ' + zoneSourceLabel + ': ' + zoneSourceTown + ')';
      } else {
        statusSpan.textContent = String.fromCodePoint(0x2714)
          + ' Seleccionado (zona no detectada, seleccionala manualmente)';
      }
    }

    function applyPlace(place) {
      var comps = place.address_components || [];
      var lat   = place.geometry.location.lat();
      var lng   = place.geometry.location.lng();

      // coordenadas
      if (latField) latField.value = lat.toFixed(6);
      if (lngField) lngField.value = lng.toFixed(6);

      applyAddressComponents(comps, place.formatted_address || '');

      showMap(lat, lng);
    }

    function updateFromCoordinates() {
      if (!latField || !lngField) return;

      var lat = parseFloat(latField.value);
      var lng = parseFloat(lngField.value);
      if (isNaN(lat) || isNaN(lng)) return;
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        statusSpan.textContent = 'Coordenadas fuera de rango.';
        return;
      }

      if (!window.google || !window.google.maps) {
        statusSpan.textContent = 'Google Maps no esta listo aun.';
        return;
      }
      if (!geocoder) geocoder = new window.google.maps.Geocoder();

      statusSpan.textContent = 'Actualizando campos desde coordenadas...';
      geocoder.geocode({ location: { lat: lat, lng: lng } }, function (results, status) {
        if (status === 'OK' && results && results.length > 0) {
          applyAddressComponents(results[0].address_components || [], results[0].formatted_address || '');
          showMap(lat, lng);
        } else {
          statusSpan.textContent = 'No se pudo resolver la direccion desde lat/lng.';
        }
      });
    }

    if (latField && lngField) {
      latField.addEventListener('change', updateFromCoordinates);
      lngField.addEventListener('change', updateFromCoordinates);
      latField.addEventListener('blur', updateFromCoordinates);
      lngField.addEventListener('blur', updateFromCoordinates);
    }

    function showMap(lat, lng) {
      mapDiv.style.display = 'block';
      var center = { lat: lat, lng: lng };
      var map = new window.google.maps.Map(mapDiv, {
        center: center,
        zoom: 17,
        mapTypeControl: false,
        streetViewControl: false,
      });
      new window.google.maps.Marker({ position: center, map: map });
    }
  });
})();
