const ID_RADIO_INTEZETI = 'assignment_type-intezeti';
const ID_RADIO_SZAKERTOI = 'assignment_type-szakertoi';
const ID_SELECT_SZAKERTO = 'assigned_expert_id';

function applyExpertToggle() {
  const rIntezeti = document.getElementById(ID_RADIO_INTEZETI);
  const rSzakertoi = document.getElementById(ID_RADIO_SZAKERTOI);
  const select = document.getElementById(ID_SELECT_SZAKERTO);
  if (!rIntezeti || !rSzakertoi || !select) return;

  if (rSzakertoi.checked === true) {
    select.removeAttribute('disabled');
    select.setAttribute('required', '');
  } else {
    select.setAttribute('disabled', '');
    select.removeAttribute('required');
  }
}

function bindInvestigationHandlers() {
  const rIntezeti = document.getElementById(ID_RADIO_INTEZETI);
  const rSzakertoi = document.getElementById(ID_RADIO_SZAKERTOI);
  if (rIntezeti) rIntezeti.addEventListener('change', applyExpertToggle);
  if (rSzakertoi) rSzakertoi.addEventListener('change', applyExpertToggle);
  applyExpertToggle();
}

bindInvestigationHandlers();
