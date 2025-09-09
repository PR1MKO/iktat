document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.file-upload-form');
  if (!form) return;
  const btn = form.querySelector('.upload-btn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (btn) { btn.disabled = true; btn.dataset._orig = btn.innerHTML; btn.innerHTML = 'Feltöltés...'; }
    try {
      const res = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      if (!res.ok) throw new Error('upload failed');
      await res.json();
      window.location.reload();
    } catch (err) {
      alert('Hiba a feltöltés során. Kérjük, próbáld újra.');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset._orig || 'Feltöltés'; }
    }
  });
});