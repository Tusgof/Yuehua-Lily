const STORAGE_KEY = "trend-following-system-dashboard-v1";

const defaultState = {
  settings: {
    targetVolatility: 10,
    universeCount: 52,
    rebalance: "Weekly",
    mode: "Research"
  },
  phases: [
    {
      range: "0-10",
      title: "Trading plan",
      detail: "เขียน hypothesis, universe, timeframe, data source, entry/exit, sizing, risk limits, execution assumptions และกฎ pause/reduce/retire.",
      progress: 0
    },
    {
      range: "10-20",
      title: "Universe และ Data",
      detail: "เตรียม multi-asset futures ครอบคลุม equities, rates, FX, commodities พร้อม cleaned rolling series, roll rules และ timestamp discipline.",
      progress: 0
    },
    {
      range: "20-35",
      title: "Signal layer",
      detail: "สร้าง baseline 60-day directional count แล้วต่อด้วย multi-lookback t-stat / delta-straddle signals ที่ 32/64/126/252/504 วัน.",
      progress: 0
    },
    {
      range: "35-50",
      title: "Position และ Portfolio",
      detail: "แปลง signal strength เป็น position ด้วย inverse volatility, risk weight และ covariance/correlation-aware risk contribution.",
      progress: 0
    },
    {
      range: "50-60",
      title: "Risk controls",
      detail: "กำหนด portfolio target volatility, leverage cap, exposure cap, concentration cap, trade floor และ rebalance threshold.",
      progress: 0
    },
    {
      range: "60-70",
      title: "Event-driven backtest",
      detail: "จำลอง market, signal, order, fill, rebalance, roll, cost และ portfolio events ให้ใกล้ live assumptions.",
      progress: 0
    },
    {
      range: "70-80",
      title: "Validation",
      detail: "ตรวจ chronological splits, untouched final test, leakage checks, gross/net, turnover, subperiods และ parameter sensitivity.",
      progress: 0
    },
    {
      range: "80-90",
      title: "Paper incubation",
      detail: "เดินระบบแบบ live-like ด้วย signal file, target positions, order list, reconciliation, journal และ operational error tracking.",
      progress: 0
    },
    {
      range: "90-100",
      title: "Limited live -> Monitor",
      detail: "เริ่มขนาดเล็ก, review รายสัปดาห์ และ scale เฉพาะเมื่อ behavior ตรงแผนและ process เสถียร.",
      progress: 0
    }
  ],
  layers: [
    {
      id: "universe",
      title: "Universe",
      label: "Multi-asset futures",
      body: "ใช้ opportunity set ที่กว้างผ่าน equities, rates, FX และ commodities เพื่อลดการกระจุกตัวของ trend timing risk ในตลาดเดียว.",
      checks: ["เลือก liquid instruments", "สร้าง rolling futures series", "บันทึก roll timing ให้ชัดเจน"]
    },
    {
      id: "signal",
      title: "Signal",
      label: "Multi-lookback t-stat",
      body: "แปลง trend estimate เป็น bounded exposure โดยใช้ทั้ง trend strength และ uncertainty แล้วรวมหลาย horizon เข้าด้วยกัน.",
      checks: ["60-day baseline", "candidate 32/64/126/252/504 วัน", "ดู gross และ net แยกตาม horizon"]
    },
    {
      id: "sizing",
      title: "Sizing",
      label: "Signal x risk / vol",
      body: "Raw position ใช้ signal strength, risk weight และ inverse volatility เพื่อให้ asset ที่ volatility ต่างกันเทียบกันได้.",
      checks: ["EWMA volatility", "Risk weights", "Position caps"]
    },
    {
      id: "portfolio",
      title: "Portfolio",
      label: "Correlation aware",
      body: "Covariance/correlation layer ตรวจว่า positions รวมกันแล้วช่วย diversify หรือสร้าง hidden concentration ก่อน scale ระดับ portfolio.",
      checks: ["Risk contribution", "Correlation stress", "HRP/risk-budget variant"]
    },
    {
      id: "vol",
      title: "Target Vol",
      label: "Portfolio-level leverage",
      body: "หลังสร้าง positions แล้วค่อย scale ทั้ง portfolio ไปยัง volatility target ที่เลือก และต้องมี leverage cap ชัดเจน.",
      checks: ["Target vs realized vol", "Leverage distribution", "Exposure cap"]
    },
    {
      id: "cost",
      title: "Cost Control",
      label: "Trade floor",
      body: "ข้ามการเปลี่ยน position เล็กๆ ที่ไม่น่ามีผลเชิงเศรษฐกิจ และเทียบผลก่อน/หลัง realistic costs.",
      checks: ["Trade floor", "Rebalance threshold", "Spread/slippage"]
    },
    {
      id: "validation",
      title: "Validation",
      label: "Out-of-sample gates",
      body: "ใช้ chronological validation, untouched final test, cost sensitivity, subperiod checks และ baseline comparison.",
      checks: ["No lookahead", "Parameter sensitivity", "Baseline comparison"]
    },
    {
      id: "live",
      title: "Live Ops",
      label: "Weekly monitor",
      body: "เมื่อ deploy แล้ว ให้ review signals, positions, fills, PnL, risk, costs, roll status และ deviations สัปดาห์ละครั้ง.",
      checks: ["Journal", "Reconciliation", "Continue/revise/pause decision"]
    }
  ],
  gates: [
    { title: "เขียน Trading plan แล้ว", detail: "มีกฎและ stop conditions ก่อนเข้า final test.", done: false },
    { title: "Data pipeline ทำซ้ำได้", detail: "บันทึก rolling futures, roll dates และ data checks ชัดเจน.", done: false },
    { title: "สร้าง Baseline แล้ว", detail: "มีระบบ 60-day directional-count เพื่อใช้เปรียบเทียบ.", done: false },
    { title: "สร้าง Production signal แล้ว", detail: "ทดสอบ multi-lookback t-stat candidate แยกตาม horizon.", done: false },
    { title: "ทดสอบ Risk engine แล้ว", detail: "แยก inverse vol, risk weights, correlation layer และ target vol ชัดเจน.", done: false },
    { title: "รวม Costs แล้ว", detail: "เปิดใช้ spread, commissions, slippage, thresholds และ trade floors.", done: false },
    { title: "ผ่าน Out-of-sample", detail: "ไม่ได้ใช้ final test ในช่วงเลือก design.", done: false },
    { title: "Paper run เสร็จแล้ว", detail: "Live-like signals และ reconciliation เสถียร.", done: false },
    { title: "อนุมัติ Limited live", detail: "พร้อมเรื่อง size, monitoring และ pause rules.", done: false }
  ],
  weekly: [
    { text: "สร้าง signals และ target positions แล้ว", done: false },
    { text: "Reconcile orders, fills และ broker positions แล้ว", done: false },
    { text: "Review PnL, drawdown, exposure, leverage และ target-vol drift แล้ว", done: false },
    { text: "Review turnover, spread/slippage และ trade-floor skips แล้ว", done: false },
    { text: "ตรวจ roll schedule และ data quality แล้ว", done: false },
    { text: "บันทึก journal decision: continue, revise, pause หรือ stop", done: false }
  ],
  notes: []
};

let state = loadState();

function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return structuredClone(defaultState);
  try {
    return mergeState(structuredClone(defaultState), JSON.parse(saved));
  } catch {
    return structuredClone(defaultState);
  }
}

function mergeProgress(baseItems, incomingItems = []) {
  return baseItems.map((item, index) => ({
    ...item,
    progress: incomingItems[index]?.progress ?? item.progress,
    done: incomingItems[index]?.done ?? item.done
  }));
}

function mergeState(base, incoming) {
  return {
    ...base,
    ...incoming,
    settings: { ...base.settings, ...(incoming.settings || {}) },
    phases: mergeProgress(base.phases, incoming.phases),
    layers: base.layers,
    gates: mergeProgress(base.gates, incoming.gates),
    weekly: mergeProgress(base.weekly, incoming.weekly),
    notes: incoming.notes || base.notes
  };
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state, null, 2));
  renderSummary();
  renderExport();
}

function renderSummary() {
  const weightedProgress = Math.round(
    state.phases.reduce((sum, phase) => sum + Number(phase.progress || 0), 0) / state.phases.length
  );
  const nextPhase = state.phases.find((phase) => Number(phase.progress) < 100) || state.phases[state.phases.length - 1];

  document.getElementById("overallProgress").textContent = `${weightedProgress}%`;
  document.getElementById("modeOutput").textContent = state.settings.mode;
  document.getElementById("nextGate").textContent = nextPhase.title;
  document.getElementById("riskTargetOutput").textContent = `${state.settings.targetVolatility}%`;
}

function renderRoadmap() {
  const container = document.getElementById("roadmapList");
  container.innerHTML = "";

  state.phases.forEach((phase, index) => {
    const row = document.createElement("article");
    row.className = "phase-row";
    row.innerHTML = `
      <div class="phase-range">${phase.range}</div>
      <div class="phase-body">
        <h3>${phase.title}</h3>
        <p>${phase.detail}</p>
      </div>
      <div class="phase-control">
        <span>สำเร็จ ${phase.progress}%</span>
        <input type="range" min="0" max="100" step="5" value="${phase.progress}" aria-label="ความคืบหน้า ${phase.title}">
      </div>
    `;
    row.querySelector("input").addEventListener("input", (event) => {
      state.phases[index].progress = Number(event.target.value);
      row.querySelector(".phase-control span").textContent = `สำเร็จ ${event.target.value}%`;
      saveState();
    });
    container.appendChild(row);
  });
}

function renderFlow() {
  const container = document.getElementById("flowMap");
  container.innerHTML = "";

  state.layers.forEach((layer, index) => {
    const button = document.createElement("button");
    button.className = `flow-node${index === 1 ? " active" : ""}`;
    button.type = "button";
    button.innerHTML = `<strong>${layer.title}</strong><span>${layer.label}</span>`;
    button.addEventListener("click", () => selectLayer(layer.id));
    container.appendChild(button);
  });

  selectLayer("signal");
}

function selectLayer(id) {
  const layer = state.layers.find((item) => item.id === id) || state.layers[0];
  document.querySelectorAll(".flow-node").forEach((node, index) => {
    node.classList.toggle("active", state.layers[index].id === id);
  });
  document.getElementById("layerTitle").textContent = layer.title;
  document.getElementById("layerBody").textContent = layer.body;
  const checks = document.getElementById("layerChecks");
  checks.innerHTML = "";
  layer.checks.forEach((check) => {
    const li = document.createElement("li");
    li.textContent = check;
    checks.appendChild(li);
  });
}

function renderRiskControls() {
  const target = document.getElementById("riskTargetInput");
  const universe = document.getElementById("universeInput");
  const rebalance = document.getElementById("rebalanceInput");
  const mode = document.getElementById("modeInput");

  target.value = state.settings.targetVolatility;
  universe.value = state.settings.universeCount;
  rebalance.value = state.settings.rebalance;
  mode.value = state.settings.mode;

  target.addEventListener("input", () => {
    state.settings.targetVolatility = Number(target.value);
    saveState();
  });
  universe.addEventListener("input", () => {
    state.settings.universeCount = Number(universe.value);
    saveState();
  });
  rebalance.addEventListener("change", () => {
    state.settings.rebalance = rebalance.value;
    saveState();
  });
  mode.addEventListener("change", () => {
    state.settings.mode = mode.value;
    saveState();
  });
}

function renderGates() {
  const container = document.getElementById("gateGrid");
  container.innerHTML = "";

  state.gates.forEach((gate, index) => {
    const item = document.createElement("label");
    item.className = "gate-item";
    item.innerHTML = `
      <input type="checkbox" ${gate.done ? "checked" : ""} aria-label="${gate.title}">
      <span><strong>${gate.title}</strong><p>${gate.detail}</p></span>
    `;
    item.querySelector("input").addEventListener("change", (event) => {
      state.gates[index].done = event.target.checked;
      saveState();
    });
    container.appendChild(item);
  });
}

function renderWeekly() {
  const container = document.getElementById("weeklyChecklist");
  container.innerHTML = "";

  state.weekly.forEach((item, index) => {
    const row = document.createElement("label");
    row.className = "check-row";
    row.innerHTML = `
      <input type="checkbox" ${item.done ? "checked" : ""} aria-label="${item.text}">
      <span>${item.text}</span>
    `;
    row.querySelector("input").addEventListener("change", (event) => {
      state.weekly[index].done = event.target.checked;
      saveState();
    });
    container.appendChild(row);
  });
}

function renderNotes() {
  const container = document.getElementById("journalList");
  container.innerHTML = "";

  state.notes.slice().reverse().forEach((note) => {
    const item = document.createElement("article");
    item.className = "note-item";
    item.innerHTML = `<time>${note.date}</time><p>${note.text}</p>`;
    container.appendChild(item);
  });
}

function renderExport() {
  document.getElementById("exportArea").value = JSON.stringify(state, null, 2);
}

function bindDataActions() {
  document.getElementById("addNoteButton").addEventListener("click", () => {
    const input = document.getElementById("journalInput");
    const text = input.value.trim();
    if (!text) return;
    state.notes.push({
      date: new Date().toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" }),
      text
    });
    input.value = "";
    renderNotes();
    saveState();
  });

  document.getElementById("exportButton").addEventListener("click", async () => {
    renderExport();
    const data = document.getElementById("exportArea").value;
    await navigator.clipboard?.writeText(data).catch(() => {});
  });

  document.getElementById("importInput").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const text = await file.text();
    try {
      state = mergeState(structuredClone(defaultState), JSON.parse(text));
      saveState();
      renderAll();
    } catch {
      alert("Import ไม่สำเร็จ: JSON ไม่ถูกต้อง");
    } finally {
      event.target.value = "";
    }
  });

  document.getElementById("resetButton").addEventListener("click", () => {
    if (!confirm("Reset สถานะ Dashboard ที่เก็บไว้ใน browser นี้?")) return;
    state = structuredClone(defaultState);
    saveState();
    renderAll();
  });
}

function renderAll() {
  renderSummary();
  renderRoadmap();
  renderFlow();
  renderRiskControls();
  renderGates();
  renderWeekly();
  renderNotes();
  renderExport();
}

bindDataActions();
renderAll();
