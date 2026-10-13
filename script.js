// Change this if your backend runs on a different host/port.
const API_BASE = "http://localhost:5000/api";

let currentData = null; // holds sample or uploaded records
let chartInstance = null;

const statusEl = document.getElementById("status");
const fileInput = document.getElementById("fileInput");
const horizonInput = document.getElementById("horizon");

document.getElementById("loadSampleBtn").addEventListener("click", loadSample);
document.getElementById("forecastBtn").addEventListener("click", runForecast);

async function loadSample() {
  setStatus("Loading sample data...");
  try {
    const res = await fetch(`${API_BASE}/sample-data`);
    const json = await res.json();
    currentData = json.data;
    setStatus(`Loaded ${currentData.length} sample rows. Click "Run Forecast".`);
  } catch (err) {
    setStatus("Could not reach backend. Is the Flask server running on port 5000?", true);
  }
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(",").map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const cells = line.split(",");
    return { [headers[0]]: cells[0], [headers[1]]: Number(cells[1]) };
  });
}

fileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const text = await file.text();
  currentData = parseCSV(text).map((row) => {
    const keys = Object.keys(row);
    return { date: row[keys[0]], sales: row[keys[1]] };
  });
  setStatus(`Parsed ${currentData.length} rows from ${file.name}. Click "Run Forecast".`);
});

async function runForecast() {
  if (!currentData) {
    setStatus("Load the sample data or upload a CSV first.", true);
    return;
  }
  setStatus("Running forecast...");
  try {
    const res = await fetch(`${API_BASE}/forecast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: currentData, horizon: Number(horizonInput.value) }),
    });
    const json = await res.json();
    if (json.error) throw new Error(json.error);
    renderChart(json.history, json.forecast);
    renderMetrics(json.metrics, json.best_model);
    renderTable(json.forecast);
    setStatus(`Forecast complete · trained on ${json.rows_used} rows.`);
  } catch (err) {
    setStatus(`Error: ${err.message}`, true);
  }
}

function renderChart(history, forecast) {
  const labels = [...history.map((h) => h.date), ...forecast.map((f) => f.date)];
  const historyValues = [...history.map((h) => h.value), ...Array(forecast.length).fill(null)];
  const forecastValues = [...Array(history.length - 1).fill(null), history[history.length - 1].value, ...forecast.map((f) => f.forecast)];

  const ctx = document.getElementById("forecastChart").getContext("2d");
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Historical", data: historyValues, borderColor: "#4f46e5", backgroundColor: "transparent", tension: 0.25 },
        { label: "Forecast", data: forecastValues, borderColor: "#f97316", borderDash: [6, 4], backgroundColor: "transparent", tension: 0.25 },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "top" } },
      scales: { x: { ticks: { maxTicksLimit: 12 } } },
    },
  });
}

function renderMetrics(metrics, bestModel) {
  const grid = document.getElementById("metricsGrid");
  grid.innerHTML = "";
  Object.entries(metrics).forEach(([modelName, m]) => {
    const box = document.createElement("div");
    box.className = "metric-box";
    box.innerHTML = `
      <h3>${modelName.replace("_", " ")}</h3>
      <p>MAE: ${m.mae}</p>
      <p>RMSE: ${m.rmse}</p>
      <p>MAPE: ${m.mape}%</p>
    `;
    grid.appendChild(box);
  });
  document.getElementById("bestModel").textContent = `✅ Best performing model: ${bestModel.replace("_", " ")}`;
  document.getElementById("metricsSection").style.display = "block";
}

function renderTable(forecast) {
  const tbody = document.querySelector("#forecastTable tbody");
  tbody.innerHTML = "";
  forecast.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.date}</td><td>${row.forecast}</td>`;
    tbody.appendChild(tr);
  });
}

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.style.color = isError ? "#dc2626" : "#6b7280";
}
