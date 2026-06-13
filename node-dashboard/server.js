import { createServer } from "node:http";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(__dirname, "public");
const dataDir = path.join(__dirname, "data");
const observationPath = path.join(dataDir, "observations.json");
const userPath = path.join(dataDir, "users.json");
const port = Number(process.env.PORT || 3000);

const sessions = new Map();
const demoUsers = [
  {
    id: "demo-operator",
    fullName: "Оператор мониторинга",
    login: "operator",
    password: "1234",
    role: "Оператор",
  },
];

const rivers = [
  {
    name: "Баксан",
    basinArea: 680,
    slopeIndex: 0.22,
    riskCoefficient: 1.15,
    color: "#7b54d8",
    description: "Высокогорный бассейн с выраженной селевой активностью и развитой инфраструктурой.",
  },
  {
    name: "Малка",
    basinArea: 850,
    slopeIndex: 0.18,
    riskCoefficient: 1.0,
    color: "#37bce4",
    description: "Крупный бассейн, где существенную роль играют снеготаяние и накопленная водность.",
  },
  {
    name: "Черек",
    basinArea: 560,
    slopeIndex: 0.21,
    riskCoefficient: 1.05,
    color: "#ec3f8c",
    description: "Горный бассейн с крутыми склонами, высокой расчлененностью рельефа и ливневыми триггерами.",
  },
  {
    name: "Чегем",
    basinArea: 420,
    slopeIndex: 0.23,
    riskCoefficient: 1.1,
    color: "#ff9f32",
    description: "Компактный бассейн с быстрым гидрологическим откликом на осадки и сейсмические сигналы.",
  },
];

const events = [
  ["2015-08-03", "19:15", 50, 95, "Средний", "Ливневые осадки", "Баксан"],
  ["2016-07-11", "14:40", 120, 380, "Очень мощный", "Ливень + снеготаяние", "Чегем"],
  ["2017-06-22", "21:05", 30, 48, "Малый", "Ливневые осадки", "Черек"],
  ["2018-08-15", "16:50", 60, 210, "Мощный", "Интенсивный ливень", "Баксан"],
  ["2019-05-19", "11:30", 90, 250, "Мощный", "Снеготаяние + дождь", "Малка"],
  ["2020-07-28", "19:05", 55, 95, "Средний", "Ливневые осадки", "Чегем"],
  ["2022-06-12", "15:40", 75, 160, "Мощный", "Прорыв ледникового озера", "Баксан"],
  ["2023-08-09", "17:25", 40, 70, "Средний", "Ливневые осадки", "Черек"],
].map(([date, time, duration, volume, power, trigger, river]) => ({
  date,
  time,
  duration,
  volume,
  power,
  trigger,
  river,
}));

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
  const snowmeltBoost = 0.45 + 0.55 * tempFactor;
  const scores = {
    precipitation: normalize(values.precipitation, 0, 80),
    waterFlow: normalize(values.waterFlow, 5, 220),
    humidity: normalize(values.humidity, 35, 100),
    snowWater: clamp(snowBase * snowmeltBoost),
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

function rng(seed) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function generateHistory() {
  const random = rng(42);
  const records = [];
  const now = Date.now();
  for (const river of rivers) {
    for (let day = 44; day >= 0; day -= 1) {
      const seasonal = Math.sin((45 - day) / 5);
      const eventPulse = day % 13 === 0 ? 1 : 0;
      const values = {
        precipitation: clamp(12 + seasonal * 10 + eventPulse * 34 + random() * 18, 0, 95),
        temperature: clamp(8 + seasonal * 7 + random() * 9, -10, 34),
        humidity: clamp(58 + eventPulse * 18 + random() * 28, 20, 100),
        waterFlow: clamp(42 + seasonal * 18 + eventPulse * 75 + random() * 42, 5, 250),
        snowWater: clamp(210 + Math.cos(day / 7) * 90 + random() * 140, 0, 850),
        seismicActivity: clamp(1.4 + eventPulse * 3.2 + random() * 3.4, 0, 9.5),
      };
      const risk = calculateRisk(values, river);
      records.push({
        id: `${river.name}-${day}`,
        river: river.name,
        timestamp: new Date(now - day * 24 * 60 * 60 * 1000).toISOString(),
        ...values,
        risk,
        level: classifyRisk(risk),
      });
    }
  }
  return records;
}

async function readObservations() {
  if (!existsSync(observationPath)) return [];
  try {
    return JSON.parse(await readFile(observationPath, "utf8"));
  } catch {
    return [];
  }
}

async function saveObservation(record) {
  await mkdir(dataDir, { recursive: true });
  const observations = await readObservations();
  observations.push(record);
  await writeFile(observationPath, JSON.stringify(observations.slice(-500), null, 2), "utf8");
}

async function readUsers() {
  if (!existsSync(userPath)) return demoUsers;
  try {
    const users = JSON.parse(await readFile(userPath, "utf8"));
    const merged = [...demoUsers];
    users.forEach((user) => {
      if (!merged.some((item) => item.login === user.login)) merged.push(user);
    });
    return merged;
  } catch {
    return demoUsers;
  }
}

async function saveUsers(users) {
  await mkdir(dataDir, { recursive: true });
  const customUsers = users.filter((user) => !demoUsers.some((item) => item.login === user.login));
  await writeFile(userPath, JSON.stringify(customUsers, null, 2), "utf8");
}

async function readBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

function publicUser(user) {
  if (!user) return null;
  return {
    id: user.id,
    fullName: user.fullName,
    login: user.login,
    role: user.role,
  };
}

function createSession(user) {
  const token = randomUUID();
  sessions.set(token, {
    user,
    createdAt: Date.now(),
  });
  return token;
}

function getToken(request) {
  const header = request.headers.authorization || "";
  if (header.startsWith("Bearer ")) return header.slice(7);
  return "";
}

function getUserFromRequest(request) {
  const token = getToken(request);
  if (!token || !sessions.has(token)) return null;
  return sessions.get(token).user;
}

function sendJson(response, payload, status = 200) {
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  response.end(JSON.stringify(payload));
}

async function serveStatic(request, response) {
  const url = new URL(request.url, `http://${request.headers.host}`);
  const safePath = path.normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, "");
  const filePath = path.join(publicDir, safePath === "/" ? "index.html" : safePath);
  const ext = path.extname(filePath).toLowerCase();
  const types = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
  };
  try {
    const file = await readFile(filePath);
    response.writeHead(200, { "content-type": types[ext] || "application/octet-stream" });
    response.end(file);
  } catch {
    const index = await readFile(path.join(publicDir, "index.html"));
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    response.end(index);
  }
}

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://${request.headers.host}`);
    if (request.method === "POST" && url.pathname === "/api/auth/login") {
      const payload = JSON.parse(await readBody(request));
      const login = String(payload.login || "").trim();
      const password = String(payload.password || "");
      const users = await readUsers();
      const user = users.find((item) => item.login === login && item.password === password);
      if (!user) {
        sendJson(response, { error: "Неверный логин или пароль" }, 401);
        return;
      }
      const token = createSession(user);
      sendJson(response, { token, user: publicUser(user) });
      return;
    }

    if (request.method === "POST" && url.pathname === "/api/auth/register") {
      const payload = JSON.parse(await readBody(request));
      const fullName = String(payload.fullName || "").trim();
      const login = String(payload.login || "").trim();
      const password = String(payload.password || "");
      if (!fullName || !login || !password) {
        sendJson(response, { error: "Заполните ФИО, логин и пароль" }, 400);
        return;
      }
      const users = await readUsers();
      if (users.some((item) => item.login === login)) {
        sendJson(response, { error: "Пользователь с таким логином уже существует" }, 409);
        return;
      }
      const user = {
        id: `user-${Date.now()}`,
        fullName,
        login,
        password,
        role: "Оператор",
      };
      users.push(user);
      await saveUsers(users);
      const token = createSession(user);
      sendJson(response, { token, user: publicUser(user) }, 201);
      return;
    }

    if (request.method === "GET" && url.pathname === "/api/auth/me") {
      const user = getUserFromRequest(request);
      if (!user) {
        sendJson(response, { authenticated: false }, 401);
        return;
      }
      sendJson(response, { authenticated: true, user: publicUser(user) });
      return;
    }

    if (request.method === "POST" && url.pathname === "/api/auth/logout") {
      const token = getToken(request);
      if (token) sessions.delete(token);
      sendJson(response, { ok: true });
      return;
    }

    if (request.method === "GET" && url.pathname === "/api/bootstrap") {
      const user = getUserFromRequest(request);
      if (!user) {
        sendJson(response, { error: "Требуется авторизация" }, 401);
        return;
      }
      const observations = await readObservations();
      sendJson(response, {
        rivers,
        events,
        history: [...generateHistory(), ...observations],
      });
      return;
    }

    if (request.method === "POST" && url.pathname === "/api/observations") {
      const user = getUserFromRequest(request);
      if (!user) {
        sendJson(response, { error: "Требуется авторизация" }, 401);
        return;
      }
      const payload = JSON.parse(await readBody(request));
      const river = rivers.find((item) => item.name === payload.river) || rivers[0];
      const values = {
        precipitation: Number(payload.precipitation),
        temperature: Number(payload.temperature),
        humidity: Number(payload.humidity),
        waterFlow: Number(payload.waterFlow),
        snowWater: Number(payload.snowWater),
        seismicActivity: Number(payload.seismicActivity),
      };
      const risk = calculateRisk(values, river);
      const record = {
        id: `manual-${Date.now()}`,
        river: river.name,
        timestamp: new Date().toISOString(),
        ...values,
        risk,
        level: classifyRisk(risk),
        operator: user.login,
      };
      await saveObservation(record);
      sendJson(response, record, 201);
      return;
    }

    await serveStatic(request, response);
  } catch (error) {
    sendJson(response, { error: error.message }, 500);
  }
});

server.listen(port, () => {
  console.log(`SelFlow Node dashboard: http://localhost:${port}`);
});
