console.log("Feature calculations script loaded");

document.addEventListener("DOMContentLoaded", function () {
  // =========================
  // Live ROI/TTV berekening via server
  // =========================
  const inputs = document.querySelectorAll(
    "[name='extra_revenue'], [name='churn_reduction'], [name='cost_savings'], [name='investment_hours'], [name='hourly_rate'], [name='opex'], [name='other_costs'], [name='ttm_weeks'], [name='ttbv_weeks']"
  );

  async function updateCalculations() {
    const form = document.querySelector("form");
    if (!form) return;

    const formData = new FormData(form);

    // ROI ophalen
    const roiResp = await fetch("/features/calc/roi", {
      method: "POST",
      body: formData
    });
    const roiHtml = await roiResp.text();
    const roiContainer = document.querySelector("#roi-results");
    if (roiContainer) roiContainer.innerHTML = roiHtml;

    // TTV ophalen
    const ttvResp = await fetch("/features/calc/ttv", {
      method: "POST",
      body: formData
    });
    const ttvHtml = await ttvResp.text();
    const ttvContainer = document.querySelector("#ttv-results");
    if (ttvContainer) ttvContainer.innerHTML = ttvHtml;
  }

  inputs.forEach(el => el.addEventListener("input", updateCalculations));
  updateCalculations(); // initiale render
});

// =========================
// Wachtwoord toggle (oogje)
// =========================
const togglePassword = document.querySelector('#togglePassword');
const password = document.querySelector('#password');

if (togglePassword && password) {
  togglePassword.addEventListener('click', function () {
    const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
    password.setAttribute('type', type);

    // wissel icoon
    this.classList.toggle('bi-eye');
    this.classList.toggle('bi-eye-slash');
  });
}



// =========================
// Scroll Animatie Logica (Fade-in Up, tweerichtingsverkeer)
// =========================

function checkVisibility() {
    const animatedElements = document.querySelectorAll('.fade-in-scroll');
    
    // De trigger-lijn: wanneer het element 85% van de viewport-hoogte bereikt
    const triggerPoint = window.innerHeight * 0.90;
    
    // De 'wegschuif'-lijn: wanneer de onderkant van het element boven 10% van de viewport komt (bij terugscrollen)
    const hidePoint = window.innerHeight * 0.10;

    animatedElements.forEach(element => {
        const rect = element.getBoundingClientRect(); 

        // 1. ANIMEER IN: Als de bovenkant van het element de triggerPoint passeert (scrollen naar beneden)
        if (rect.top < triggerPoint && rect.bottom > 0) {
            element.classList.add('is-visible');
        } 
        
        // 2. SCHUIF WEG: Als de onderkant van het element boven de hidePoint komt (scrollen naar boven)
        // OF als de bovenkant van het element helemaal uit beeld is (rect.bottom < 0).
        // Hiermee wordt voorkomen dat elementen die al ver boven de viewport zijn alsnog zichtbaar blijven.
        else if (rect.bottom < hidePoint || rect.top > window.innerHeight) {
            element.classList.remove('is-visible');
        }
    });
}

// Luister naar de scroll-gebeurtenis
window.addEventListener('scroll', checkVisibility);

// Controleer direct bij het laden van de pagina voor elementen die al in beeld zijn
document.addEventListener('DOMContentLoaded', checkVisibility);
