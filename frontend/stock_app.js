/* jshint esversion: 6 */
/**
 * Frontend logic for stock web app.
 *
 * Flow:
 *  - Python calls window.initApp(...) on load to seed tickers and default dates.
 *  - User changes inputs -> fetchPlotData() -> ask backend for filtered series.
 *  - Backend calls window.plotStockData(x, y, errorMsg) to render or show an error.
 *  - Stat buttons call toggleStatLine(stat). If turned on, JS asks backend for the stat.
 *  - Backend calls window.drawStatLine(stat, upper, lower, errorMsg) to overlay lines.
 */

// Only keep constants where we expect to tweak copy or reuse the value.
const ERR_INVALID_DATES   = "Please choose valid dates.";
const ERR_START_AFTER_END = "Start date cannot be after end date.";
const LABEL_STD_UPPER = "Mean + Std Dev";
const LABEL_STD_LOWER = "Mean - Std Dev";

// Module state kept simple for readability
let tickers = [], chart = null;
let plotX = [], plotY = [];
let activeStats = { mean: false, median: false, std: false };

/**
 * Initialize UI and draw the initial chart.
 * Called by Python via jsc.eval_js_code("window.initApp([...], 'YYYY-MM-DD', 'YYYY-MM-DD')")
 */
window.initApp = function(tickerList, defaultStart, defaultEnd) {
  tickers = tickerList;

  const tickerSelect = document.getElementById("ticker-select");
  tickerSelect.innerHTML = tickers.map(t => `<option value="${t}">${t}</option>`).join('');

  const startDateInput = document.getElementById("start-date");
  const endDateInput   = document.getElementById("end-date");
  startDateInput.value = defaultStart;
  endDateInput.value   = defaultEnd;

  tickerSelect.onchange   = fetchPlotData;
  startDateInput.onchange = fetchPlotData;
  endDateInput.onchange   = fetchPlotData;

  fetchPlotData();
};

/**
 * Read inputs, perform light validation, reset stat state, and request series from backend.
 */
function fetchPlotData() {
  const ticker         = document.getElementById("ticker-select").value;
  const startDateInput = document.getElementById("start-date");
  const endDateInput   = document.getElementById("end-date");
  const startVal       = startDateInput.value;
  const endVal         = endDateInput.value;

  const plotErrorDiv = document.getElementById("plot-error");

  // Reset UI for a fresh series
  plotErrorDiv.textContent = "";
  startDateInput.classList.remove("input-error");
  endDateInput.classList.remove("input-error");

  ["mean", "median", "std"].forEach((s) => {
    document.getElementById(`${s}-btn`).classList.remove("active");
    const err = document.getElementById(`${s}-error`);
    if (err) err.textContent = "";
    activeStats[s] = false;
  });
  
  if (chart) chart.destroy();

  // Minimal client validation: start <= end
  const startDate = new Date(startVal);
  const endDate = new Date(endVal);
  
  if (startDate > endDate) {
    plotErrorDiv.textContent = ERR_START_AFTER_END;
    startDateInput.classList.add("input-error");
    endDateInput.classList.add("input-error");
    return;
  }

  // Ask backend for filtered Close series
  call_py('get_plot_data', ticker, startVal, endVal);
}

/**
 * Render base series or display an error under the chart.
 * Called by Python: window.plotStockData(x, y, errorMsg).
 */
window.plotStockData = function(x, y, errorMsg) {
  const plotErrorDiv = document.getElementById("plot-error");

  if (errorMsg) {
    plotErrorDiv.textContent = errorMsg;
    if (chart) { chart.destroy(); chart = null; }
    plotX = []; plotY = [];
    return;
  }

  plotErrorDiv.textContent = "";
  plotX = x; plotY = y;

  const ctx = document.getElementById("stock-chart").getContext('2d');

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: x,
      datasets: [{
        label: "Close Price ($)",
        data: y,
        borderColor: "blue",
        fill: false,
        pointRadius: 1.5,
        hidden: false
      }]
    },
    options: {
      responsive: false,
      plugins: { legend: { onClick: () => {} } },
      scales: {
        x: { type: 'category', title: { display: true, text: 'Date' },
             ticks: { autoSkip: true, maxTicksLimit: 12 } },
        y: { title: { display: true, text: 'Price ($)' }, beginAtZero: false }
      }
    }
  });
}

/**
 * Find a dataset by its label. Used to replace/remove overlays.
 */
function getStatDatasetIndex(label) {
  if (!chart) return -1;
  return chart.data.datasets.findIndex((ds) => ds.label === label);
}

/**
 * Toggle a stat overlay from the UI (buttons call this via onclick).
 * If turning ON, ask backend for the stat; if turning OFF, remove the overlay dataset(s).
 */
function toggleStatLine(stat) {
  activeStats[stat] = !activeStats[stat];
  document.getElementById(`${stat}-btn`)
    .classList.toggle("active", activeStats[stat]);

  const statErrorDiv = document.getElementById(`${stat}-error`);
  if (statErrorDiv) statErrorDiv.textContent = "";

  const ticker         = document.getElementById("ticker-select").value;
  const startDateInput = document.getElementById("start-date");
  const endDateInput   = document.getElementById("end-date");
  const startVal       = startDateInput.value;
  const endVal         = endDateInput.value;

  if (activeStats[stat]) {
    call_py('get_stat_value', ticker, startVal, endVal, stat);
  } else {
    if (!chart) return;

    if (stat === "mean") {
      const i = getStatDatasetIndex("Mean");
      if (i > -1) chart.data.datasets.splice(i, 1);
    }
    if (stat === "median") {
      const i = getStatDatasetIndex("Median");
      if (i > -1) chart.data.datasets.splice(i, 1);
    }
    if (stat === "std") {
      const i1 = getStatDatasetIndex(LABEL_STD_UPPER);
      if (i1 > -1) chart.data.datasets.splice(i1, 1);
      const i2 = getStatDatasetIndex(LABEL_STD_LOWER);
      if (i2 > -1) chart.data.datasets.splice(i2, 1);
    }

    chart.update();
  }
}
window.toggleStatLine = toggleStatLine;

/**
 * Draw or remove stat overlays based on backend response.
 * Only Std Dev can return a specific per‑stat error ('Only one price point').
 */
window.drawStatLine = function(stat, upper, lower, errorMsg) {
  if (errorMsg) {
    const statErrorDiv = document.getElementById(`${stat}-error`);
    if (statErrorDiv) statErrorDiv.textContent = errorMsg;
    if (activeStats[stat]) {
      activeStats[stat] = false;
      document.getElementById(`${stat}-btn`).classList.remove("active");
    }
    return;
  }

  if (!chart) return;

  if (stat === "mean") {
    const i = getStatDatasetIndex("Mean");
    if (i > -1) chart.data.datasets.splice(i, 1);
    chart.data.datasets.push({
      label: "Mean",
      data: plotX.map(() => upper),
      borderColor: "green",
      borderWidth: 2,
      fill: false,
      borderDash: [7, 5],
      pointRadius: 0,
      spanGaps: true
    });
  }

  if (stat === "median") {
    const i = getStatDatasetIndex("Median");
    if (i > -1) chart.data.datasets.splice(i, 1);
    chart.data.datasets.push({
      label: "Median",
      data: plotX.map(() => upper),
      borderColor: "purple",
      borderWidth: 2,
      fill: false,
      borderDash: [7, 5],
      pointRadius: 0,
      spanGaps: true
    });
  }

  if (stat === "std") {
    const i1 = getStatDatasetIndex(LABEL_STD_UPPER);
    if (i1 > -1) chart.data.datasets.splice(i1, 1);
    const i2 = getStatDatasetIndex(LABEL_STD_LOWER);
    if (i2 > -1) chart.data.datasets.splice(i2, 1);

    chart.data.datasets.push(
      {
        label: LABEL_STD_UPPER,
        data: plotX.map(() => upper),
        borderColor: "orange",
        borderWidth: 2,
        fill: false,
        borderDash: [6, 4],
        pointRadius: 0,
        spanGaps: true
      },
      {
        label: LABEL_STD_LOWER,
        data: plotX.map(() => lower),
        borderColor: "red",
        borderWidth: 2,
        fill: false,
        borderDash: [6, 4],
        pointRadius: 0,
        spanGaps: true
      }
    );
  }

  chart.update();
};
