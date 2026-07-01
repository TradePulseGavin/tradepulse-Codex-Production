(function () {
  var form = document.getElementById('support-ticket-form');
  var result = document.getElementById('support-ticket-result');
  function safe(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
    });
  }
  function show(markup) {
    if (!result) return;
    result.classList.remove('hidden');
    result.innerHTML = markup;
  }
  if (!form) return;
  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    var payload = {
      email: document.getElementById('support-email').value,
      category: document.getElementById('support-category').value,
      subject: document.getElementById('support-subject').value,
      message: document.getElementById('support-message').value
    };
    try {
      var response = await fetch('/api/support/ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      var data = await response.json();
      if (!data.ok) {
        show('<p>' + safe(data.message || 'Support request needs more detail.') + '</p>');
        return;
      }
      var ticket = data.ticket || {};
      show('<p>' + safe(data.message || 'Support request received.') + '</p><div class="metric-card"><span class="muted">Ticket ID</span><br><strong>' + safe(ticket.id || 'received') + '</strong></div><p class="muted">Support contact: ' + safe(data.support_email || '') + '</p>');
      form.reset();
    } catch (error) {
      show('<p>Support request could not be saved right now.</p><p class="muted">Use the listed support email if this happens on the hosted site.</p>');
    }
  });
})();
