console.log("Feature calculations script loaded");

document.addEventListener("DOMContentLoaded", function () {
  // =========================
  // ROI berekening
  // =========================
  const revenueInput = document.querySelector("[name='extra_revenue']");
  const churnInput = document.querySelector("[name='churn_reduction']");
  const savingsInput = document.querySelector("[name='cost_savings']");
  const devInput = document.querySelector("[name='investment_hours']");
  const rateInput = document.querySelector("[name='hourly_rate']");
  const opexInput = document.querySelector("[name='opex_hours']");
  const otherInput = document.querySelector("[name='other_costs']");
  const roiOutput = document.querySelector("[name='roi_percent']");

  function calculateROI() {
    const gains =
      (parseFloat(revenueInput.value) || 0) +
      (parseFloat(churnInput.value) || 0) +
      (parseFloat(savingsInput.value) || 0);


    // multiply hours × hourly rate
    const devHours = parseFloat(devInput.value) || 0;
    const hourlyRate = parseFloat(rateInput.value) || 0;
    const devCost = devHours * hourlyRate;

    const costs =
      devCost +
      (parseFloat(opexInput.value) || 0) +
      (parseFloat(otherInput.value) || 0);

    if (costs > 0) {
      const roi = ((gains - costs) / costs) * 100;
      roiOutput.value = roi.toFixed(2);
    } else {
      roiOutput.value = "";
    }
  }

  [revenueInput, churnInput, savingsInput, devInput, rateInput, opexInput, otherInput].forEach((el) => {
    if (el) {
      el.addEventListener("input", calculateROI);
    }
  });

  // =========================
  // TTV berekening
  // =========================
  const ttmInput = document.querySelector("[name='ttm_weeks']");
  const ttbvInput = document.querySelector("[name='ttbv_weeks']");
  const ttvOutput = document.querySelector("[name='ttv_weeks']");

  function calculateTTV() {
    const ttm = parseFloat(ttmInput.value) || 0;
    const ttbv = parseFloat(ttbvInput.value) || 0;
    const ttv = ttm + ttbv;

    if (ttv > 0) {
      ttvOutput.value = ttv;
    } else {
      ttvOutput.value = "";
    }
  }

  [ttmInput, ttbvInput].forEach((el) => {
    if (el) {
      el.addEventListener("input", calculateTTV);
    }
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
});