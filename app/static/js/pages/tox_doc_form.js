function recalc() {
  let total = 0;
  document.querySelectorAll('input[name$="_minta_count"]').forEach(cnt => {
    const key = cnt.name.replace('_minta_count', '');
    const priceEl = document.querySelector(`input[name="${key}_minta_ara"]`);
    const qty = parseFloat(cnt.value) || 0;
    const price = parseFloat(priceEl.value) || 0;
    total += qty * price;
  });
  const totalEl = document.getElementById('osszesen_ara');
  if (totalEl) {
    totalEl.value = Math.round(total);
  }
}

document.querySelectorAll('input[data-price-per-unit]').forEach(el => {
  el.addEventListener('input', recalc);
});

recalc();

const submitBtn = document.getElementById('tox-generate');
if (submitBtn) {
  submitBtn.addEventListener('click', (e) => {
    if (!window.confirm('Biztosan el szeretné készíteni a dokumentumot? Az OK gomb megnyomása után a dokumentum nem lesz a továbbiakban szerkeszthető')) {
      e.preventDefault();
    }
  });
}