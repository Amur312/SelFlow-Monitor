const pages = [
  ["dashboard", "Панель мониторинга", "home"],
  ["input", "Ввод данных", "send"],
  ["analytics", "Аналитика", "chart"],
  ["database", "База данных", "table"],
  ["events", "История событий", "clock"],
  ["profile", "Личный кабинет", "user"],
];

const factorLabels = {
  precipitation: "Осадки",
  temperature: "Температура",
  humidity: "Влажность",
  waterFlow: "Расход",
  snowWater: "Снег",
  seismicActivity: "Сейсмика",
};

const levelColors = {
  "Низкий": "#28dd62",
  "Повышенный": "#ffc642",
  "Высокий": "#ff9f32",
  "Критический": "#ec3f8c",
};

const state = {
  page: "dashboard",
  river: "Баксан",
  rivers: [],
  history: [],
  events: [],
  authenticated: false,
  authMode: "login",
  surfacePeriod: "month",
  token: localStorage.getItem("selflow-token") || "",
  user: null,
};

const surfaceState = {
  yaw: -0.65,
  pitch: 0.72,
  dragging: false,
  lastX: 0,
  lastY: 0,
};

const app = document.querySelector("#app");
const nav = document.querySelector("#nav");
const authScreen = document.querySelector("#authScreen");
const appShell = document.querySelector("#appShell");
const accountButton = document.querySelector("#accountButton");
const logoutButton = document.querySelector("#logoutButton");
const profilePanel = document.querySelector("#profilePanel");
const accountInitials = document.querySelector("#accountInitials");
const profileName = document.querySelector("#profileName");
const profileRole = document.querySelector("#profileRole");
const profileLogin = document.querySelector("#profileLogin");

function authHeaders(extra = {}) {
  return {
    ...extra,
    ...(state.token ? { authorization: `Bearer ${state.token}` } : {}),
  };
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: authHeaders(options.headers || {}),
  });
  if (response.status === 401) {
    clearSession();
    render();
    throw new Error("Требуется авторизация");
  }
  return response;
}

function setSession(token, user) {
  state.token = token;
  state.user = user;
  state.authenticated = true;
  localStorage.setItem("selflow-token", token);
}

function clearSession() {
  state.token = "";
  state.user = null;
  state.authenticated = false;
  localStorage.removeItem("selflow-token");
}

function icon(name) {
  const icons = {
    home: '<path d="M3 10.5 12 3l9 7.5v9a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H4.5A1.5 1.5 0 0 1 3 19.5v-9Z"/>',
    send: '<path d="M21 3 3 10.5l7.5 2L12.5 21 21 3Z"/>',
    chart: '<path d="M4 19V5h2v14H4Zm7 0V9h2v10h-2Zm7 0V3h2v16h-2Z"/>',
    table: '<path d="M4 5h16v14H4V5Zm2 4h12V7H6v2Zm0 4h5v-2H6v2Zm7 0h5v-2h-5v2Zm-7 4h5v-2H6v2Zm7 0h5v-2h-5v2Z"/>',
    clock: '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 5h-2v6l5 3 1-1.7-4-2.3V7Z"/>',
    grid: '<path d="M4 4h7v7H4V4Zm9 0h7v7h-7V4ZM4 13h7v7H4v-7Zm9 0h7v7h-7v-7Z"/>',
    user: '<path d="M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9Zm0 2c-4.4 0-8 2.2-8 5v1h16v-1c0-2.8-3.6-5-8-5Z"/>',
  };
  return `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">${icons[name]}</svg>`;
}

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, Number(value)));
}

function normalize(value, low, high) {
  if (high <= low) return 0;
  return clamp((Number(value) - low) / (high - low));
}

function temperatureScore(value) {
  const temperature = Number(value);
  if (temperature <= -5) return 0.05;
  if (temperature < 0) return 0.15;
  if (temperature <= 22) return normalize(temperature, 0, 22);
  return clamp(1 - (temperature - 22) / 28, 0.45, 1);
}

function calculateRisk(values, river) {
  const tempFactor = temperatureScore(values.temperature);
  const snowBase = normalize(values.snowWater, 0, 800);
  const scores = {
    precipitation: normalize(values.precipitation, 0, 80),
    waterFlow: normalize(values.waterFlow, 5, 220),
    humidity: normalize(values.humidity, 35, 100),
    snowWater: clamp(snowBase * (0.45 + 0.55 * tempFactor)),
    temperature: tempFactor,
    seismicActivity: normalize(values.seismicActivity, 0, 8),
  };
  const weighted =
    scores.precipitation * 0.25 +
    scores.waterFlow * 0.22 +
    scores.humidity * 0.15 +
    scores.snowWater * 0.15 +
    scores.temperature * 0.08 +
    scores.seismicActivity * 0.15;
  return Math.round(clamp(weighted * river.riskCoefficient) * 1000) / 10;
}

function classifyRisk(risk) {
  if (risk < 30) return "Низкий";
  if (risk < 55) return "Повышенный";
  if (risk < 75) return "Высокий";
  return "Критический";
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
  }).format(new Date(value));
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function latestByRiver() {
  return state.rivers.map((river) => {
    const records = state.history
      .filter((item) => item.river === river.name)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    return records[records.length - 1];
  });
}

function currentRiver() {
  return state.rivers.find((river) => river.name === state.river) || state.rivers[0];
}

function currentHistory() {
  return state.history
    .filter((item) => item.river === state.river)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

const periodConfig = {
  day: { label: "День", days: 1, caption: "Последние сутки", precipitationMax: 90, flowMax: 240 },
  week: { label: "Неделя", days: 7, caption: "Последние 7 дней", precipitationMax: 100, flowMax: 260 },
  month: { label: "Месяц", days: 30, caption: "Последние 30 дней", precipitationMax: 110, flowMax: 290 },
};

function periodRecords() {
  const config = periodConfig[state.surfacePeriod] || periodConfig.month;
  return currentHistory().slice(-config.days);
}

function averageRecord(records) {
  const source = records.length ? records : currentHistory().slice(-1);
  const result = {
    precipitation: 0,
    temperature: 0,
    humidity: 0,
    waterFlow: 0,
    snowWater: 0,
    seismicActivity: 0,
    risk: 0,
  };
  source.forEach((item) => {
    Object.keys(result).forEach((key) => {
      result[key] += Number(item[key] || 0);
    });
  });
  Object.keys(result).forEach((key) => {
    result[key] /= Math.max(1, source.length);
  });
  return result;
}

function userInitials(user = state.user) {
  const source = user?.fullName || user?.login || "SM";
  return source
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function updateAccountView() {
  const user = state.user || { fullName: "Оператор мониторинга", login: "operator", role: "Оператор" };
  accountInitials.textContent = userInitials(user);
  profileName.textContent = user.fullName;
  profileRole.textContent = user.role || "Оператор";
  profileLogin.textContent = `Логин: ${user.login}`;
}

function renderNav() {
  nav.innerHTML = pages
    .map(
      ([id, label, iconName]) => `
        <button class="nav-button ${state.page === id ? "active" : ""}" data-page="${id}" type="button">
          <span class="nav-icon">${icon(iconName)}</span>
          <span>${label}</span>
        </button>
      `,
    )
    .join("");

  nav.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      state.page = button.dataset.page;
      render();
    });
  });
}

function lineChart(records) {
  const points = records.slice(-32);
  const width = 760;
  const height = 250;
  const pad = 26;
  const xStep = (width - pad * 2) / Math.max(1, points.length - 1);
  const toX = (_, index) => pad + index * xStep;
  const riskY = (item) => height - pad - (item.risk / 100) * (height - pad * 2);
  const flowY = (item) => height - pad - clamp(item.waterFlow / 220) * (height - pad * 2);
  const riskPoints = points.map((item, index) => `${toX(item, index)},${riskY(item).toFixed(1)}`);
  const flowPoints = points.map((item, index) => `${toX(item, index)},${flowY(item).toFixed(1)}`);
  const area =
    `M${riskPoints[0]} L${riskPoints.slice(1).join(" L")} ` +
    `L${pad + (points.length - 1) * xStep},${height - pad} L${pad},${height - pad} Z`;
  const grid = [0, 25, 50, 75, 100]
    .map((value) => {
      const y = height - pad - (value / 100) * (height - pad * 2);
      return `<line x1="${pad}" y1="${y}" x2="${width - pad}" y2="${y}" stroke="#edf0f6"/>`;
    })
    .join("");
  const monthLabels = points
    .filter((_, index) => index % 7 === 0)
    .map((item, index) => {
      const x = pad + index * 7 * xStep;
      return `<text x="${x}" y="${height - 4}" fill="#a1a8b4" font-size="12">${formatDate(item.timestamp)}</text>`;
    })
    .join("");

  return `
    <svg class="line-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="riskArea" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stop-color="#ec3f8c" stop-opacity="0.28"/>
          <stop offset="1" stop-color="#ec3f8c" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${grid}
      <path d="${area}" fill="url(#riskArea)"/>
      <polyline points="${flowPoints.join(" ")}" fill="none" stroke="#ff9f32" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>
      <polyline points="${riskPoints.join(" ")}" fill="none" stroke="#ec3f8c" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      ${riskPoints
        .filter((_, index) => index % 8 === 0)
        .map((point) => {
          const [x, y] = point.split(",");
          return `<circle cx="${x}" cy="${y}" r="7" fill="#ec3f8c" stroke="#fff" stroke-width="3"/>`;
        })
        .join("")}
      ${monthLabels}
    </svg>
  `;
}

function sparkline(color = "#fff") {
  return `
    <svg class="sparkline" viewBox="0 0 120 50" fill="none">
      <path d="M4 38 C16 8, 26 8, 38 31 S59 46, 71 20 S91 8, 116 28" stroke="${color}" stroke-width="4" stroke-linecap="round"/>
    </svg>
  `;
}

function overviewCard(current, records) {
  const monthlyRisk = records.slice(-30).reduce((sum, item) => sum + item.risk, 0) / 30;
  const highCount = records.slice(-30).filter((item) => item.risk >= 55).length;
  return `
    <section class="card overview-card">
      <div class="overview-side">
        <h2>Панель мониторинга</h2>
        <p>Сводка за последний месяц</p>
        <span class="main-number">${monthlyRisk.toFixed(1)}%</span>
        <span class="label">Средний риск за месяц</span>
        <span class="main-number">${highCount}</span>
        <span class="label">Опасных наблюдений</span>
        <button class="primary-button" data-page-target="input" type="button">Новый прогноз</button>
      </div>
      <div>
        <div class="chart-zone">
          <div class="legend">
            <span><i style="background:#ec3f8c"></i>Риск</span>
            <span><i style="background:#ff9f32"></i>Расход</span>
          </div>
          ${lineChart(records)}
        </div>
        <div class="chart-footer">
          <div class="mini"><span class="mini-icon" style="background:#ec3f8c">R</span><div><span>Река</span><strong>${state.river}</strong></div></div>
          <div class="mini"><span class="mini-icon" style="background:#7b54d8">Q</span><div><span>Расход</span><strong>${current.waterFlow.toFixed(1)} м3/с</strong></div></div>
          <div class="mini"><span class="mini-icon" style="background:#38bee6">P</span><div><span>Осадки</span><strong>${current.precipitation.toFixed(1)} мм/ч</strong></div></div>
          <div class="mini"><span class="mini-icon" style="background:#ffc642">L</span><div><span>Уровень</span><strong>${current.level}</strong></div></div>
        </div>
      </div>
    </section>
  `;
}

function donutCard(latest) {
  const counts = latest.reduce(
    (acc, item) => {
      if (item.risk >= 75) acc.critical += 1;
      else if (item.risk >= 55) acc.high += 1;
      else acc.normal += 1;
      return acc;
    },
    { critical: 0, high: 0, normal: 0 },
  );
  const total = Math.max(1, latest.length);
  return `
    <section class="card donut-card">
      <div class="card-title">
        <div>
          <h3>Структура риска</h3>
          <p>Состояние четырех бассейнов</p>
        </div>
      </div>
      <div class="donut"></div>
      <div class="donut-stats">
        <div><strong>${Math.round((counts.normal / total) * 100)}%</strong><span>Норма</span></div>
        <div><strong>${Math.round((counts.high / total) * 100)}%</strong><span>Высокий</span></div>
        <div><strong>${Math.round((counts.critical / total) * 100)}%</strong><span>Критический</span></div>
      </div>
    </section>
  `;
}

function gradientCards(current) {
  return `
    <section class="grid cards-grid">
      <article class="gradient-card" style="background:linear-gradient(135deg,#ec3f8c,#b648bd)">
        <small>Влажность</small>
        <strong>${current.humidity.toFixed(0)}%</strong>
        <span>готовность бассейна к формированию стока</span>
        ${sparkline()}
      </article>
      <article class="gradient-card" style="background:linear-gradient(135deg,#7b54d8,#4d63d9)">
        <small>Снежный запас</small>
        <strong>${current.snowWater.toFixed(0)} мм</strong>
        <span>запас воды в снежном покрове</span>
        ${sparkline()}
      </article>
      <article class="gradient-card" style="background:linear-gradient(135deg,#38bee6,#5d7edc)">
        <small>Сейсмический сигнал</small>
        <strong>${current.seismicActivity.toFixed(1)}</strong>
        <span>условная интенсивность геофизического сигнала</span>
        ${sparkline()}
      </article>
      <article class="gradient-card" style="background:linear-gradient(135deg,#ffb22e,#ff7149)">
        <small>Температура</small>
        <strong>${current.temperature.toFixed(1)}°C</strong>
        <span>фактор ускоренного снеготаяния</span>
        ${sparkline()}
      </article>
    </section>
  `;
}

function activityList(records) {
  const rows = records
    .slice(-5)
    .reverse()
    .map((item, index) => {
      const colors = ["#ec3f8c", "#7b54d8", "#38bee6", "#ffc642", "#28dd62"];
      return `
        <div class="activity">
          <div class="activity-time">${formatDateTime(item.timestamp)}</div>
          <div class="activity-dot" style="background:${colors[index]}">${index + 1}</div>
          <div>
            <strong>${item.level}: ${item.risk.toFixed(1)}%</strong>
            <span>${item.river}: осадки ${item.precipitation.toFixed(1)} мм/ч, расход ${item.waterFlow.toFixed(1)} м3/с</span>
          </div>
        </div>
      `;
    })
    .join("");
  return `<section class="card timeline"><div class="card-title"><div><h3>Последние действия</h3><p>Журнал свежих наблюдений</p></div></div>${rows}</section>`;
}

function predictionTable(records) {
  const rows = records
    .slice(-7)
    .reverse()
    .map(
      (item, index) => `
        <tr>
          <td>${String(12000 + index)}</td>
          <td>${item.river}</td>
          <td>${formatDateTime(item.timestamp)}</td>
          <td>${item.risk.toFixed(1)}%</td>
          <td><span class="status" style="background:${levelColors[item.level]}">${item.level}</span></td>
        </tr>
      `,
    )
    .join("");
  return `
    <section class="card table-card">
      <div class="card-title">
        <div><h3>Журнал прогнозов</h3><p>Последние сохраненные расчеты</p></div>
      </div>
      <div class="toolbar">
        <button class="add-button" data-page-target="input" type="button">+ Добавить</button>
        <input class="search" value="Поиск" readonly />
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>№</th><th>Река</th><th>Дата</th><th>Риск</th><th>Статус</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function dashboardPage() {
  const records = currentHistory();
  const current = records[records.length - 1];
  const latest = latestByRiver();
  return `
    <div class="grid dashboard-grid">
      ${overviewCard(current, records)}
      ${donutCard(latest)}
    </div>
    ${gradientCards(current)}
    <div class="grid bottom-grid">
      ${activityList(state.history.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)))}
      ${predictionTable(state.history.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)))}
    </div>
  `;
}

function inputPage() {
  const river = currentRiver();
  const current = currentHistory().at(-1);
  return `
    <section class="card form-card">
      <div class="card-title">
        <div>
          <h2>Ввод параметров наблюдения</h2>
          <p>Расчет риска селевого потока по текущим гидрометеорологическим параметрам.</p>
        </div>
      </div>
      <form id="predictForm" class="form-grid">
        <div class="field">
          <label>Река</label>
          <select name="river">${state.rivers.map((item) => `<option ${item.name === state.river ? "selected" : ""}>${item.name}</option>`).join("")}</select>
        </div>
        ${[
          ["precipitation", "Осадки, мм/ч", current.precipitation],
          ["temperature", "Температура, °C", current.temperature],
          ["humidity", "Влажность, %", current.humidity],
          ["waterFlow", "Расход воды, м3/с", current.waterFlow],
          ["snowWater", "Снег, мм", current.snowWater],
          ["seismicActivity", "Сейсмика, усл. ед.", current.seismicActivity],
        ]
          .map(
            ([name, label, value]) => `
              <div class="field">
                <label>${label}</label>
                <input name="${name}" type="number" step="0.1" value="${Number(value).toFixed(1)}" />
              </div>
            `,
          )
          .join("")}
      </form>
      <button class="primary-button" form="predictForm" type="submit">Рассчитать и сохранить</button>
      <div class="prediction-result" id="predictionResult">
        <div class="risk-result">
          <span class="label">Текущий прогноз</span>
          <strong style="color:${levelColors[current.level]}">${current.risk.toFixed(1)}%</strong>
          <span class="status" style="background:${levelColors[current.level]}">${current.level}</span>
        </div>
        <div class="card pad">
          <h3>${river.name}</h3>
          <p class="label">${river.description}</p>
        </div>
      </div>
    </section>
  `;
}

function surfaceCanvas() {
  const config = periodConfig[state.surfacePeriod] || periodConfig.month;
  const records = periodRecords();
  const average = averageRecord(records);
  return `
    <div class="grid analytics-grid">
      <section class="card surface-card">
        <div class="card-title">
          <div><h2>3D-поверхность риска</h2><p>${config.caption}: осадки, расход воды и расчетный риск</p></div>
          <div class="tabs" role="tablist" aria-label="Период аналитики">
            ${Object.entries(periodConfig)
              .map(
                ([id, item]) => `
                  <button class="${state.surfacePeriod === id ? "active" : ""}" data-period="${id}" type="button">${item.label}</button>
                `,
              )
              .join("")}
          </div>
        </div>
        <div class="surface-summary">
          <div><span>Период</span><strong>${config.label}</strong></div>
          <div><span>Средний риск</span><strong>${average.risk.toFixed(1)}%</strong></div>
          <div><span>Осадки</span><strong>${average.precipitation.toFixed(1)} мм/ч</strong></div>
          <div><span>Расход</span><strong>${average.waterFlow.toFixed(1)} м3/с</strong></div>
          <button class="surface-reset" data-surface-action="reset" type="button">Сбросить вид</button>
        </div>
        <div class="surface-wrap">
          <canvas id="surfaceCanvas" class="surface"></canvas>
          <div class="surface-help">Мышью можно повернуть модель. Розовая точка - текущий сценарий.</div>
        </div>
        <div class="surface-legend">
          <span><i style="background:#38bee6"></i>низкий риск</span>
          <span><i style="background:#ffc642"></i>повышенный</span>
          <span><i style="background:#ff9f32"></i>высокий</span>
          <span><i style="background:#ec3f8c"></i>критический</span>
        </div>
      </section>
      <section class="card pad">
        <div class="card-title"><div><h3>Вклад факторов</h3><p>Упрощенная экспертная интерпретация</p></div></div>
        ${factorBars()}
      </section>
    </div>
    <section class="card table-card">
      <div class="card-title"><div><h3>Текущий риск по рекам</h3><p>Сравнение четырех бассейнов</p></div></div>
      ${riskBars()}
    </section>
  `;
}

function factorBars() {
  const current = currentHistory().at(-1);
  const factors = [
    ["Осадки", normalize(current.precipitation, 0, 80) * 25, "#ec3f8c"],
    ["Расход", normalize(current.waterFlow, 5, 220) * 22, "#7b54d8"],
    ["Влажность", normalize(current.humidity, 35, 100) * 15, "#38bee6"],
    ["Снег", normalize(current.snowWater, 0, 800) * 15, "#ff9f32"],
    ["Сейсмика", normalize(current.seismicActivity, 0, 8) * 15, "#28dd62"],
  ];
  return factors
    .map(
      ([name, value, color]) => `
        <div style="margin:18px 0">
          <div style="display:flex;justify-content:space-between;font-size:13px;font-weight:700"><span>${name}</span><span>${value.toFixed(1)}</span></div>
          <div style="height:10px;border-radius:999px;background:#f1f3f8;margin-top:8px;overflow:hidden">
            <div style="width:${Math.min(100, value * 4)}%;height:100%;background:${color};border-radius:999px"></div>
          </div>
        </div>
      `,
    )
    .join("");
}

function riskBars() {
  return `
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:18px">
      ${latestByRiver()
        .map(
          (item) => `
            <div style="padding:18px;border:1px solid var(--line);border-radius:10px">
              <div style="display:flex;justify-content:space-between;font-weight:800"><span>${item.river}</span><span>${item.risk.toFixed(1)}%</span></div>
              <div style="height:12px;border-radius:999px;background:#f1f3f8;margin-top:16px;overflow:hidden">
                <div style="width:${item.risk}%;height:100%;background:${levelColors[item.level]};border-radius:999px"></div>
              </div>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function analyticsPage() {
  return surfaceCanvas();
}

function databasePage() {
  const counts = [
    ["Реки", state.rivers.length, "справочник бассейнов", "#ec3f8c,#7b54d8"],
    ["Измерения", state.history.length, "временные ряды параметров", "#7b54d8,#4d63d9"],
    ["Прогнозы", state.history.length, "рассчитанные уровни риска", "#38bee6,#5d7edc"],
    ["События", state.events.length, "исторические селевые случаи", "#ffb22e,#ff7149"],
  ];
  const latestRows = state.history
    .slice()
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 8)
    .map(
      (item, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>${formatDateTime(item.timestamp)}</td>
          <td>${item.river}</td>
          <td>${item.precipitation.toFixed(1)}</td>
          <td>${item.waterFlow.toFixed(1)}</td>
          <td>${item.snowWater.toFixed(0)}</td>
          <td>${item.seismicActivity.toFixed(1)}</td>
          <td>${item.risk.toFixed(1)}%</td>
          <td><span class="status" style="background:${levelColors[item.level]}">${item.level}</span></td>
        </tr>
      `,
    )
    .join("");
  return `
    <section class="grid db-hero">
      <article class="card db-schema">
        <div class="card-title"><div><h3>Связь данных</h3><p>Как формируется прогноз</p></div></div>
        <div class="schema-flow">
          <div class="schema-node"><i style="background:#ec3f8c">1</i><div><strong>Справочник рек</strong><span>Баксан, Малка, Черек, Чегем</span></div><em>rivers</em></div>
          <div class="schema-node"><i style="background:#7b54d8">2</i><div><strong>Измерения</strong><span>осадки, температура, влажность, расход, снег, сейсмика</span></div><em>measurements</em></div>
          <div class="schema-node"><i style="background:#38bee6">3</i><div><strong>Прогноз</strong><span>процент риска и уровень опасности</span></div><em>predictions</em></div>
          <div class="schema-node"><i style="background:#ff9f32">4</i><div><strong>История событий</strong><span>материал для проверки и демонстрации</span></div><em>events</em></div>
        </div>
      </article>
    </section>
    <section class="grid database-grid">
      ${counts
        .map(
          ([name, count, caption, gradient]) => `
            <article class="db-tile" style="background:linear-gradient(135deg, ${gradient})">
              <span>${name}</span>
              <strong>${count}</strong>
              <p>${caption}</p>
            </article>
          `,
        )
        .join("")}
    </section>
    <section class="card table-card">
      <div class="card-title">
        <div><h3>Последние записи базы</h3><p>Новые измерения сразу попадают в расчет риска и журнал прогнозов</p></div>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr><th>№</th><th>Дата</th><th>Река</th><th>Осадки</th><th>Расход</th><th>Снег</th><th>Сейсмика</th><th>Риск</th><th>Уровень</th></tr>
          </thead>
          <tbody>${latestRows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function eventsPage() {
  const rows = state.events
    .map(
      (event, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>${event.date}</td>
          <td>${event.time}</td>
          <td>${event.river}</td>
          <td>${event.duration}</td>
          <td>${event.volume}</td>
          <td><span class="status" style="background:${event.power.includes("мощ") ? "#ec3f8c" : "#7b54d8"}">${event.power}</span></td>
          <td>${event.trigger}</td>
        </tr>
      `,
    )
    .join("");
  return `
    <section class="card table-card">
      <div class="card-title"><div><h2>Исторические селевые события</h2><p>Журнал известных случаев по выбранным рекам</p></div></div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>№</th><th>Дата</th><th>Время</th><th>Река</th><th>Мин.</th><th>Тыс. м3</th><th>Мощность</th><th>Триггер</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function profilePage() {
  const user = state.user || { fullName: "Оператор мониторинга", login: "operator", role: "Оператор" };
  const latest = state.history
    .slice()
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 4);
  return `
    <section class="profile-grid">
      <article class="card pad profile-settings-card">
        <div class="card-title"><div><h3>Настройки</h3><p>Параметры профиля и отображения</p></div></div>
        <div class="profile-list">
          <div><span>ФИО</span><strong>${user.fullName}</strong></div>
          <div><span>Логин</span><strong>${user.login}</strong></div>
          <div><span>Роль</span><strong>${user.role || "Оператор"}</strong></div>
          <div><span>Статус</span><strong class="good">Авторизован</strong></div>
        </div>
        <div class="settings-list">
          <label>
            <span>Река по умолчанию</span>
            <select>
              ${state.rivers.map((river) => `<option ${river.name === state.river ? "selected" : ""}>${river.name}</option>`).join("")}
            </select>
          </label>
          <label>
            <span>Период аналитики</span>
            <select>
              ${Object.entries(periodConfig)
                .map(([id, item]) => `<option ${state.surfacePeriod === id ? "selected" : ""}>${item.label}</option>`)
                .join("")}
            </select>
          </label>
          <label class="setting-toggle">
            <input type="checkbox" checked />
            <span>Показывать критические уведомления</span>
          </label>
          <label class="setting-toggle">
            <input type="checkbox" checked />
            <span>Сохранять расчеты в журнал прогнозов</span>
          </label>
        </div>
      </article>

      <article class="card table-card profile-recent">
        <div class="card-title"><div><h3>Последние расчеты</h3><p>Свежие записи, доступные оператору</p></div></div>
        <div class="table-scroll">
          <table>
            <thead><tr><th>Дата</th><th>Река</th><th>Риск</th><th>Уровень</th></tr></thead>
            <tbody>
              ${latest
                .map(
                  (item) => `
                    <tr>
                      <td>${formatDateTime(item.timestamp)}</td>
                      <td>${item.river}</td>
                      <td>${item.risk.toFixed(1)}%</td>
                      <td><span class="status" style="background:${levelColors[item.level]}">${item.level}</span></td>
                    </tr>
                  `,
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  `;
}

function renderRiverSelect() {
  return `
    <select id="riverSelect" class="search" style="width:190px">
      ${state.rivers.map((river) => `<option ${river.name === state.river ? "selected" : ""}>${river.name}</option>`).join("")}
    </select>
  `;
}

function render() {
  if (!state.authenticated) {
    authScreen.classList.remove("is-hidden");
    appShell.classList.add("is-hidden");
    profilePanel.classList.add("is-hidden");
    return;
  }

  authScreen.classList.add("is-hidden");
  appShell.classList.remove("is-hidden");
  updateAccountView();

  if (!state.rivers.length || !state.history.length) {
    app.innerHTML = `<section class="card pad"><h2>Загрузка данных</h2><p class="label">Проверяем авторизацию и получаем данные мониторинга.</p></section>`;
    return;
  }

  renderNav();
  document.querySelector(".topbar-title").innerHTML = `
    <strong>Мониторинг селевых потоков</strong>
  `;

  const pageHtml = {
    dashboard: dashboardPage,
    input: inputPage,
    analytics: analyticsPage,
    database: databasePage,
    events: eventsPage,
    profile: profilePage,
  }[state.page]();

  app.innerHTML = `
    <div class="page-heading">
      <div>
        <h1 style="margin:0;font-size:24px">${state.page === "profile" ? "Личный кабинет" : "SelFlow Monitor"}</h1>
        ${
          state.page === "profile"
            ? ""
            : '<p style="margin:6px 0 0;color:var(--muted);font-size:13px">Рабочая панель прогнозирования селевых рисков</p>'
        }
      </div>
      ${state.page === "profile" ? "" : renderRiverSelect()}
    </div>
    <div class="grid">${pageHtml}</div>
  `;

  document.querySelector("#riverSelect")?.addEventListener("change", (event) => {
    state.river = event.target.value;
    render();
  });

  document.querySelectorAll("[data-page-target]").forEach((button) => {
    button.addEventListener("click", () => {
      state.page = button.dataset.pageTarget;
      render();
    });
  });

  document.querySelectorAll("[data-period]").forEach((button) => {
    button.addEventListener("click", () => {
      state.surfacePeriod = button.dataset.period;
      render();
    });
  });

  document.querySelectorAll("[data-surface-action='reset']").forEach((button) => {
    button.addEventListener("click", () => {
      surfaceState.yaw = -0.65;
      surfaceState.pitch = 0.72;
      drawSurface();
    });
  });

  document.querySelectorAll("[data-action='logout']").forEach((button) => {
    button.addEventListener("click", performLogout);
  });

  const form = document.querySelector("#predictForm");
  if (form) form.addEventListener("submit", submitPrediction);

  if (document.querySelector("#surfaceCanvas")) drawSurface();
}

async function submitPrediction(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  const payload = {
    river: data.river,
    precipitation: Number(data.precipitation),
    temperature: Number(data.temperature),
    humidity: Number(data.humidity),
    waterFlow: Number(data.waterFlow),
    snowWater: Number(data.snowWater),
    seismicActivity: Number(data.seismicActivity),
  };
  try {
    const response = await apiRequest("/api/observations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Не удалось сохранить прогноз");
    const record = await response.json();
    state.river = record.river;
    state.history.push(record);
    render();
  } catch (error) {
    if (state.authenticated) alert(error.message);
  }
}

function drawSurface() {
  const canvas = document.querySelector("#surfaceCanvas");
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, rect.width, rect.height);

  if (!canvas.dataset.bound) {
    canvas.dataset.bound = "true";
    canvas.addEventListener("pointerdown", (event) => {
      surfaceState.dragging = true;
      surfaceState.lastX = event.clientX;
      surfaceState.lastY = event.clientY;
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!surfaceState.dragging) return;
      const dx = event.clientX - surfaceState.lastX;
      const dy = event.clientY - surfaceState.lastY;
      surfaceState.lastX = event.clientX;
      surfaceState.lastY = event.clientY;
      surfaceState.yaw += dx * 0.01;
      surfaceState.pitch = clamp(surfaceState.pitch + dy * 0.008, 0.25, 1.18);
      drawSurface();
    });
    canvas.addEventListener("pointerup", () => {
      surfaceState.dragging = false;
    });
    canvas.addEventListener("pointercancel", () => {
      surfaceState.dragging = false;
    });
  }

  const river = currentRiver();
  const config = periodConfig[state.surfacePeriod] || periodConfig.month;
  const average = averageRecord(periodRecords());
  const centerX = rect.width * 0.52;
  const centerY = rect.height * 0.62;
  const scale = Math.min(rect.width, rect.height) * 0.34;
  const yaw = surfaceState.yaw;
  const pitch = surfaceState.pitch;
  const pMin = 0;
  const pMax = config.precipitationMax;
  const qMin = 5;
  const qMax = config.flowMax;

  const project = (x, y, z) => {
    const cosYaw = Math.cos(yaw);
    const sinYaw = Math.sin(yaw);
    const cosPitch = Math.cos(pitch);
    const sinPitch = Math.sin(pitch);
    const x1 = x * cosYaw - y * sinYaw;
    const y1 = x * sinYaw + y * cosYaw;
    const y2 = y1 * cosPitch - z * sinPitch;
    const depth = y1 * sinPitch + z * cosPitch;
    return {
      x: centerX + x1 * scale,
      y: centerY + y2 * scale,
      depth,
    };
  };

  const riskColor = (risk) => {
    if (risk >= 75) return "#ec3f8c";
    if (risk >= 55) return "#ff9f32";
    if (risk >= 30) return "#ffc642";
    return "#38bee6";
  };

  const point = (precipitation, waterFlow) => {
    const values = {
      precipitation,
      temperature: average.temperature || 16,
      humidity: average.humidity || 76,
      waterFlow,
      snowWater: average.snowWater || 310,
      seismicActivity: average.seismicActivity || 3.7,
    };
    const risk = calculateRisk(values, river);
    return {
      precipitation,
      waterFlow,
      risk,
      x: ((waterFlow - qMin) / (qMax - qMin)) * 2 - 1,
      y: ((precipitation - pMin) / (pMax - pMin)) * 2 - 1,
      z: (risk / 100) * 1.18,
    };
  };

  const cells = [];
  const pSteps = Array.from({ length: 15 }, (_, index) => pMin + (index * (pMax - pMin)) / 14);
  const qSteps = Array.from({ length: 15 }, (_, index) => qMin + (index * (qMax - qMin)) / 14);
  for (let pi = 0; pi < pSteps.length - 1; pi += 1) {
    for (let qi = 0; qi < qSteps.length - 1; qi += 1) {
      const corners = [
        point(pSteps[pi], qSteps[qi]),
        point(pSteps[pi], qSteps[qi + 1]),
        point(pSteps[pi + 1], qSteps[qi + 1]),
        point(pSteps[pi + 1], qSteps[qi]),
      ];
      const projected = corners.map((item) => ({ ...item, ...project(item.x, item.y, item.z) }));
      const avgRisk = corners.reduce((sum, item) => sum + item.risk, 0) / corners.length;
      const avgDepth = projected.reduce((sum, item) => sum + item.depth, 0) / projected.length;
      cells.push({ projected, avgRisk, avgDepth });
    }
  }

  ctx.fillStyle = "#f9fafc";
  ctx.fillRect(0, 0, rect.width, rect.height);

  ctx.strokeStyle = "#e6ebf3";
  ctx.lineWidth = 1;
  for (let index = 0; index < pSteps.length; index += 2) {
    const y = ((pSteps[index] - pMin) / (pMax - pMin)) * 2 - 1;
    const a = project(-1, y, 0);
    const b = project(1, y, 0);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  for (let index = 0; index < qSteps.length; index += 2) {
    const x = ((qSteps[index] - qMin) / (qMax - qMin)) * 2 - 1;
    const a = project(x, -1, 0);
    const b = project(x, 1, 0);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  cells
    .sort((a, b) => a.avgDepth - b.avgDepth)
    .forEach((cell) => {
      ctx.beginPath();
      cell.projected.forEach((item, index) => {
        if (index === 0) ctx.moveTo(item.x, item.y);
        else ctx.lineTo(item.x, item.y);
      });
      ctx.closePath();
      ctx.fillStyle = riskColor(cell.avgRisk);
      ctx.globalAlpha = 0.84;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "rgba(255,255,255,0.74)";
      ctx.lineWidth = 1;
      ctx.stroke();
    });

  const axes = [
    { from: [-1, -1, 0], to: [1.15, -1, 0], label: "Расход воды, м3/с", color: "#7b54d8" },
    { from: [-1, -1, 0], to: [-1, 1.15, 0], label: "Осадки, мм/ч", color: "#38bee6" },
    { from: [-1, -1, 0], to: [-1, -1, 1.25], label: "Риск, %", color: "#ec3f8c" },
  ];

  ctx.lineWidth = 2;
  axes.forEach((axis) => {
    const a = project(...axis.from);
    const b = project(...axis.to);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.strokeStyle = axis.color;
    ctx.stroke();
    ctx.fillStyle = axis.color;
    ctx.font = "700 12px Inter, sans-serif";
    ctx.fillText(axis.label, b.x + 8, b.y - 8);
  });

  const marker = point(clamp(average.precipitation, pMin, pMax), clamp(average.waterFlow, qMin, qMax));
  const markerBase = project(marker.x, marker.y, 0);
  const markerTop = project(marker.x, marker.y, marker.z);
  ctx.beginPath();
  ctx.moveTo(markerBase.x, markerBase.y);
  ctx.lineTo(markerTop.x, markerTop.y);
  ctx.strokeStyle = "rgba(236,63,140,0.8)";
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(markerTop.x, markerTop.y, 7, 0, Math.PI * 2);
  ctx.fillStyle = "#ec3f8c";
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = "#fff";
  ctx.stroke();
  ctx.fillStyle = "#172033";
  ctx.font = "800 12px Inter, sans-serif";
  ctx.fillText("Средняя точка периода", markerTop.x + 12, markerTop.y - 10);

  ctx.fillStyle = "#172033";
  ctx.font = "800 13px Inter, sans-serif";
  ctx.fillText(`Река: ${river.name} | Период: ${config.label}`, 18, 28);
  ctx.fillStyle = "#7d8798";
  ctx.font = "12px Inter, sans-serif";
  ctx.fillText("Высота показывает риск, цвет показывает уровень опасности.", 18, 48);
  ctx.fillText(`Диапазон: осадки 0-${pMax} мм/ч, расход ${qMin}-${qMax} м3/с.`, 18, 66);
}

function setupAuth() {
  const authForm = document.querySelector("#authForm");
  const authTitle = document.querySelector("#authTitle");
  const authText = document.querySelector("#authText");
  const authSubmit = document.querySelector("#authSubmit");
  const authMessage = document.querySelector("#authMessage");
  const registerFields = document.querySelectorAll(".register-only");
  const modeButtons = document.querySelectorAll("[data-auth-mode]");

  const showAuthError = (message = "") => {
    authMessage.textContent = message;
    authMessage.classList.toggle("is-hidden", !message);
  };

  const syncAuthMode = (resetMessage = true) => {
    const isRegister = state.authMode === "register";
    if (resetMessage) showAuthError("");
    authTitle.textContent = isRegister ? "Регистрация" : "Авторизация";
    authText.textContent = isRegister
      ? "Создайте учетную запись оператора для доступа к рабочей программе."
      : "Войдите в рабочую панель оператора или зарегистрируйте нового пользователя.";
    authSubmit.textContent = isRegister ? "Зарегистрироваться и войти" : "Войти в систему";
    registerFields.forEach((field) => field.classList.toggle("is-hidden", !isRegister));
    modeButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.authMode === state.authMode);
    });
  };

  modeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.authMode = button.dataset.authMode;
      syncAuthMode();
    });
  });

  authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showAuthError("");
    const data = Object.fromEntries(new FormData(authForm));
    if (!String(data.login || "").trim() || !String(data.password || "").trim()) {
      showAuthError("Введите логин и пароль");
      return;
    }
    if (state.authMode === "register" && !String(data.fullName || "").trim()) {
      showAuthError("Введите ФИО пользователя");
      return;
    }

    authSubmit.disabled = true;
    authSubmit.textContent = state.authMode === "register" ? "Создаем аккаунт..." : "Проверяем вход...";
    try {
      const endpoint = state.authMode === "register" ? "/api/auth/register" : "/api/auth/login";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(data),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Не удалось выполнить вход");
      setSession(payload.token, payload.user);
      await loadBootstrap();
      render();
    } catch (error) {
      clearSession();
      showAuthError(error.message);
    } finally {
      authSubmit.disabled = false;
      syncAuthMode(false);
    }
  });
  syncAuthMode();
}

async function performLogout() {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: authHeaders(),
    });
  } catch {
    // Local session cleanup is enough for the prototype if the server is unavailable.
  }
  clearSession();
  state.rivers = [];
  state.history = [];
  state.events = [];
  profilePanel.classList.add("is-hidden");
  render();
}

function setupAccountMenu() {
  accountButton.addEventListener("click", () => {
    profilePanel.classList.add("is-hidden");
    accountButton.setAttribute("aria-expanded", "false");
    state.page = "profile";
    render();
  });

  logoutButton.addEventListener("click", performLogout);
}

async function loadBootstrap() {
  const response = await apiRequest("/api/bootstrap");
  const payload = await response.json();
  Object.assign(state, payload);
}

async function restoreSession() {
  if (!state.token) return;
  try {
    const response = await fetch("/api/auth/me", {
      headers: authHeaders(),
    });
    if (!response.ok) throw new Error("Сессия недействительна");
    const payload = await response.json();
    state.authenticated = true;
    state.user = payload.user;
    await loadBootstrap();
  } catch {
    clearSession();
  }
}

async function init() {
  setupAuth();
  setupAccountMenu();
  await restoreSession();
  render();
}

init();
