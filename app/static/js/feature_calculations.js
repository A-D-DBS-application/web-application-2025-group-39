console.log("Feature calculations script loaded");


document.addEventListener("DOMContentLoaded", function () {
  // ROI berekening
  const revenueInput = document.querySelector("[name='extra_revenue']");
  const churnInput = document.querySelector("[name='churn_reduction']");
  const savingsInput = document.querySelector("[name='cost_savings']");
  const devInput = document.querySelector("[name='investment_hours']");
  const opexInput = document.querySelector("[name='opex_hours']");
  const otherInput = document.querySelector("[name='other_costs']");
  const roiOutput = document.querySelector("[name='roi_percent']");

  function calculateROI() {
    const gains =
      (parseFloat(revenueInput.value) || 0) +
      (parseFloat(churnInput.value) || 0) +
      (parseFloat(savingsInput.value) || 0);

    const costs =
      (parseFloat(devInput.value) || 0) +
      (parseFloat(opexInput.value) || 0) +
      (parseFloat(otherInput.value) || 0);

    if (costs > 0) {
      const roi = ((gains - costs) / costs) * 100;
      roiOutput.value = roi.toFixed(2);
    } else {
      roiOutput.value = "";
    }
  }

  [revenueInput, churnInput, savingsInput, devInput, opexInput, otherInput].forEach((el) =>
    el.addEventListener("input", calculateROI)
  );

  // TTV berekening
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

  [ttmInput, ttbvInput].forEach((el) =>
    el.addEventListener("input", calculateTTV)
  );
});