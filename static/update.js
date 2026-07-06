let peopleData = [];

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

async function init() {
  const res = await fetch("/api/people");
  peopleData = await res.json();

  const select = document.getElementById("personSelect");
  peopleData.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name;
    select.appendChild(opt);
  });

  document.getElementById("dateInput").value = todayISO();

  select.addEventListener("change", renderMetrics);
  document.getElementById("dateInput").addEventListener("change", renderMetrics);
  document.getElementById("submitBtn").addEventListener("click", submitAll);
}

async function renderMetrics() {
  const personId = document.getElementById("personSelect").value;
  const area = document.getElementById("metricsArea");
  const submitBtn = document.getElementById("submitBtn");

  if (!personId) {
    area.innerHTML = "";
    submitBtn.style.display = "none";
    return;
  }

  const person = peopleData.find((p) => String(p.id) === String(personId));
  const dateVal = document.getElementById("dateInput").value;
  const ids = person.metrics.map((m) => m.id).join(",");

  let existing = {};
  if (ids) {
    const res = await fetch(`/api/values?metric_ids=${ids}&date=${dateVal}`);
    existing = await res.json();
  }

  area.innerHTML = person.metrics
    .map((m) => {
      const val = existing[m.id] ?? existing[String(m.id)] ?? "";
      return `
        <div class="metric-row">
          <label for="metric-${m.id}">${m.name}</label>
          <input type="number" min="0" step="1" id="metric-${m.id}" data-metric-id="${m.id}" value="${val}" placeholder="0">
        </div>
      `;
    })
    .join("");

  submitBtn.style.display = person.metrics.length ? "block" : "none";
}

async function submitAll() {
  const dateVal = document.getElementById("dateInput").value;
  const inputs = document.querySelectorAll("#metricsArea input[data-metric-id]");

  const requests = Array.from(inputs)
    .filter((inp) => inp.value !== "")
    .map((inp) =>
      fetch("/api/entry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metric_id: Number(inp.dataset.metricId),
          date: dateVal,
          value: Number(inp.value),
        }),
      })
    );

  await Promise.all(requests);
  showToast();
}

function showToast() {
  const toast = document.getElementById("toast");
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

init();
