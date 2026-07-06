let refDate = new Date();

function fmtISO(d) {
  return d.toISOString().slice(0, 10);
}

function fmtDayLabel(iso) {
  const [y, m, d] = iso.split("-");
  const dt = new Date(iso);
  const weekday = dt.toLocaleDateString("he-IL", { weekday: "short" });
  return `${weekday} ${d}/${m}`;
}

function statusLabel(status) {
  return {
    green: "עומד ביעד",
    yellow: "קרוב ליעד",
    red: "מתחת ליעד",
    neutral: "ללא יעד",
    "no-data": "אין נתונים",
  }[status] || status;
}

function sparkline(history) {
  const max = Math.max(1, ...history);
  const bars = history
    .map((v) => {
      const h = Math.max(2, Math.round((v / max) * 20));
      return `<span class="bar" style="height:${h}px" title="${v}"></span>`;
    })
    .join("");
  return `<span class="sparkline">${bars}</span>`;
}

async function loadDashboard() {
  const iso = fmtISO(refDate);
  const res = await fetch(`/api/dashboard?date=${iso}`);
  const data = await res.json();
  render(data);
}

function render(data) {
  document.getElementById("generatedAt").textContent =
    "עודכן לאחרונה: " + data.generated_at.replace("T", " ");

  const startLabel = fmtDayLabel(data.week_start).split(" ")[1];
  const endLabel = fmtDayLabel(data.week_end).split(" ")[1];
  document.getElementById("weekLabel").textContent = `שבוע ${startLabel} - ${endLabel}`;

  // head row
  const headRow = document.getElementById("headRow");
  let headHtml = `<th class="person-col">אחראי</th><th class="metric-col">פעילות</th>`;
  data.days.forEach((d) => {
    headHtml += `<th>${fmtDayLabel(d)}</th>`;
  });
  headHtml += `<th>סה"כ</th><th>סיכום השבוע</th><th>מגמה (4 שב')</th>`;
  headRow.innerHTML = headHtml;

  // body rows + summary counts
  const counts = { green: 0, yellow: 0, red: 0, neutral: 0, "no-data": 0 };
  const body = document.getElementById("tableBody");
  let rowsHtml = "";

  data.people.forEach((person) => {
    person.metrics.forEach((metric, idx) => {
      counts[metric.status] = (counts[metric.status] || 0) + 1;
      const isFirst = idx === 0;
      rowsHtml += `<tr class="${isFirst ? "person-group-start" : ""}">`;
      if (isFirst) {
        rowsHtml += `<td class="person-cell" rowspan="${person.metrics.length}">${person.name}</td>`;
      }
      rowsHtml += `<td class="metric-cell">${metric.name}</td>`;
      data.days.forEach((d) => {
        const v = metric.daily[d];
        rowsHtml += `<td>${v === null || v === undefined ? '<span class="no-val">—</span>' : v}</td>`;
      });
      rowsHtml += `<td class="total-col">${metric.total || 0}</td>`;
      const pctText = metric.pct !== null && metric.pct !== undefined ? ` (${metric.pct}%)` : "";
      rowsHtml += `<td><span class="chip ${metric.status}">${metric.week_sum}${pctText}</span></td>`;
      rowsHtml += `<td>${sparkline(metric.history)}</td>`;
      rowsHtml += `</tr>`;
    });
  });

  body.innerHTML = rowsHtml;

  const cardsEl = document.getElementById("summaryCards");
  cardsEl.innerHTML = `
    <div class="card green"><div class="num">${counts.green}</div><div class="label">עומדים ביעד</div></div>
    <div class="card yellow"><div class="num">${counts.yellow}</div><div class="label">קרובים ליעד</div></div>
    <div class="card red"><div class="num">${counts.red}</div><div class="label">מתחת ליעד</div></div>
    <div class="card nodata"><div class="num">${counts["no-data"]}</div><div class="label">ללא נתונים</div></div>
  `;
}

document.getElementById("prevWeek").addEventListener("click", () => {
  refDate.setDate(refDate.getDate() - 7);
  loadDashboard();
});
document.getElementById("nextWeek").addEventListener("click", () => {
  refDate.setDate(refDate.getDate() + 7);
  loadDashboard();
});
document.getElementById("todayBtn").addEventListener("click", () => {
  refDate = new Date();
  loadDashboard();
});

loadDashboard();
