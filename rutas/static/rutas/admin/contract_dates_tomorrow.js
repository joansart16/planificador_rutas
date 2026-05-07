(function () {
  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function tomorrowIso() {
    var now = new Date();
    var tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    return tomorrow.getFullYear() + '-' + pad(tomorrow.getMonth() + 1) + '-' + pad(tomorrow.getDate());
  }

  function updateShortcuts() {
    var dateRows = document.querySelectorAll('.form-row.field-start_date, .form-row.field-end_date');

    dateRows.forEach(function (row) {
      var input = row.querySelector('input.vDateField');
      var shortcuts = row.querySelector('.datetimeshortcuts');
      if (!input || !shortcuts) {
        return;
      }

      var links = shortcuts.querySelectorAll('a');
      if (!links.length) {
        return;
      }

      var todayLink = links[0];
      todayLink.textContent = 'Mañana';

      todayLink.addEventListener('click', function (event) {
        event.preventDefault();
        input.value = tomorrowIso();
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
    });
  }

  document.addEventListener('DOMContentLoaded', updateShortcuts);
})();
