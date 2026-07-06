let adminPassword = "";
let cachedData = [];

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg || "נשמר בהצלחה ✓";
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2000);
}

async function login() {
  const pw = document.getElementById("passwordInput").value;
  const res = await fetch(`/api/admin/data?password=${encodeURIComponent(pw)}`);
  if (res.status === 401) {
    document.getElementById("loginError").textContent = "סיסמה שגויה";
    return;
  }
  adminPassword = pw;
  cachedData = await res.json();
  document.getElementById("loginBox").style.display = "none";
  document.getElementById("app").style.display = "block";
  render();
}

async function refresh() {
  const res = await fetch(`/api/admin/data?password=${encodeURIComponent(adminPassword)}`);
  cachedData = await res.json();
  render();
}

function render() {
  const list = document.getElementById("peopleList");
  list.innerHTML = cachedData
    .map(
      (p) => `
    <div class="person-card">
      <div class="person-head">
        <input type="text" value="${p.name}" data-person-id="${p.id}" data-field="name" placeholder="שם">
        <input type="email" value="${p.email || ""}" data-person-id="${p.id}" data-field="email" placeholder="אימייל">
        <button class="small-btn primary" onclick="savePerson(${p.id})">שמור</button>
        <button class="small-btn danger" onclick="deletePerson(${p.id}, '${p.name}')">מחק אחראי</button>
      </div>
      ${p.metrics
        .map(
          (m) => `
        <div class="metric-line">
          <input type="text" value="${m.name}" data-metric-id="${m.id}" data-field="name" placeholder="שם הפעילות">
          <input type="number" class="narrow" value="${m.weekly_target ?? ""}" data-metric-id="${m.id}" data-field="weekly_target" placeholder="יעד שבועי">
          <input type="number" class="narrow" value="${m.baseline ?? 0}" data-metric-id="${m.id}" data-field="baseline" placeholder="בסיס">
          <button class="small-btn primary" onclick="saveMetric(${m.id})">שמור</button>
          <button class="small-btn danger" onclick="deleteMetric(${m.id})">מחק</button>
        </div>`
        )
        .join("")}
      <div class="metric-line">
        <input type="text" placeholder="שם פעילות חדשה" id="newMetricName-${p.id}">
        <input type="number" class="narrow" placeholder="יעד שבועי" id="newMetricTarget-${p.id}">
        <button class="small-btn" onclick="addMetric(${p.id})">הוסף פעילות</button>
      </div>
    </div>`
    )
    .join("");
}

function fieldValue(selector) {
  return document.querySelector(selector).value;
}

async function savePerson(id) {
  const name = fieldValue(`input[data-person-id="${id}"][data-field="name"]`);
  const email = fieldValue(`input[data-person-id="${id}"][data-field="email"]`);
  await fetch("/api/admin/person", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: adminPassword, id, name, email }),
  });
  showToast();
  refresh();
}

async function deletePerson(id, name) {
  if (!confirm(`למחוק את ${name} ואת כל הפעילויות והנתונים שלו? פעולה זו בלתי הפיכה.`)) return;
  await fetch("/api/admin/person", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: adminPassword, id, delete: true }),
  });
  showToast("נמחק");
  refresh();
}

async function addPerson() {
  const name = document.getElementById("newPersonName").value.trim();
  const email = document.getElementById("newPersonEmail").value.trim();
  if (!name) return;
  await fetch("/api/admin/person", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: adminPassword, name, email }),
  });
  document.getElementById("newPersonName").value = "";
  document.getElementById("newPersonEmail").value = "";
  showToast("נוסף אחראי");
  refresh();
}

async function saveMetric(id) {
  const name = fieldValue(`input[data-metric-id="${id}"][data-field="name"]`);
  const target = fieldValue(`input[data-metric-id="${id}"][data-field="weekly_target"]`);
  const baseline = fieldValue(`input[data-metric-id="${id}"][data-field="baseline"]`);
  await fetch("/api/admin/metric", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      password: adminPassword,
      id,
      name,
      weekly_target: target === "" ? null : Number(target),
      baseline: baseline === "" ? 0 : Number(baseline),
    }),
  });
  showToast();
  refresh();
}

async function deleteMetric(id) {
  if (!confirm("למחוק את הפעילות הזו ואת כל הנתונים שלה?")) return;
  await fetch("/api/admin/metric", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: adminPassword, id, delete: true }),
  });
  showToast("נמחק");
  refresh();
}

async function addMetric(personId) {
  const name = document.getElementById(`newMetricName-${personId}`).value.trim();
  const target = document.getElementById(`newMetricTarget-${personId}`).value;
  if (!name) return;
  await fetch("/api/admin/metric", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      password: adminPassword,
      person_id: personId,
      name,
      weekly_target: target === "" ? null : Number(target),
      baseline: 0,
    }),
  });
  showToast("נוספה פעילות");
  refresh();
}

document.getElementById("loginBtn").addEventListener("click", login);
document.getElementById("passwordInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") login();
});
document.getElementById("addPersonBtn").addEventListener("click", addPerson);
