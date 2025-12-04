console.log("Feature calculations script loaded");

document.addEventListener("DOMContentLoaded", function () {
  // =========================
  // Live ROI/TTV berekening via server
  // =========================
  const inputs = document.querySelectorAll(
    "[name='extra_revenue'], [name='churn_reduction'], [name='cost_savings'], [name='investment_hours'], [name='hourly_rate'], [name='opex_hours'], [name='other_costs'], [name='ttm_weeks'], [name='ttbv_weeks']"
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
