// 버셀이 배포할 때 config.js 를 만들어 냅니다.
//
//   settings.py 를 직접 읽습니다. make_config.py 를 안 돌려도 배포는 최신입니다.
//   예전에는 slots.json 을 읽었는데, 그 파일은 make_config.py 가 만드는 중간 산물이라
//   돌리는 걸 잊으면 배포에 옛 칸 목록이 그대로 올라갔습니다.
//   이제 settings.py 가 정본이고 그 한 파일만 고치면 됩니다.
//
//   settings.py 를 못 읽으면 slots.json 으로 물러섭니다. 배포는 멈추지 않습니다.
//
// 버셀 설정
//   Settings -> Environment Variables 에 SUPABASE_URL, SUPABASE_ANON_KEY
//   Settings -> Build and Deployment
//     Framework Preset  Other
//     Build Command     node build.js      (Override 켜기)
//     Output Directory  .                  (Override 켜기)

const fs = require("fs");

// ----------------------------------------------------------------
//  settings.py 읽기
//
//  파이썬을 다 해석하지 않습니다. 이 파일이 쓰는 모양만 봅니다.
//    NAME = 숫자 / "문자열" / [ ... ] / { ... }
//  값 안에 함수 호출이나 f-string 을 쓰면 여기서 못 읽고 slots.json 으로 물러섭니다.
// ----------------------------------------------------------------

// 주석을 걷어냅니다. 따옴표 안의 # 는 건드리지 않습니다.
function stripComments(src) {
  let out = "";
  let quote = null;
  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    if (quote) {
      if (c === "\\") { out += c + (src[i + 1] || ""); i++; continue; }
      if (c === quote) quote = null;
      out += c;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; out += c; continue; }
    if (c === "#") { while (i < src.length && src[i] !== "\n") i++; out += "\n"; continue; }
    out += c;
  }
  return out;
}

// NAME = 다음에 오는 값을 통째로 떼어 옵니다. 괄호 짝을 세어 끝을 찾습니다.
function readValue(src, name) {
  const m = new RegExp("^[ \\t]*" + name + "[ \\t]*=[ \\t]*", "m").exec(src);
  if (!m) return null;

  let i = m.index + m[0].length;
  const OPEN = { "[": 1, "{": 1, "(": 1 };
  const CLOSE = { "]": 1, "}": 1, ")": 1 };

  if (!OPEN[src[i]]) {                       // 숫자나 문자열 한 줄
    let j = i;
    while (j < src.length && src[j] !== "\n") j++;
    return src.slice(i, j).trim();
  }

  let depth = 0, quote = null, j = i;
  for (; j < src.length; j++) {
    const c = src[j];
    if (quote) {
      if (c === "\\") { j++; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; continue; }
    if (OPEN[c]) depth++;
    else if (CLOSE[c]) { depth--; if (depth === 0) { j++; break; } }
  }
  return src.slice(i, j);
}

// 파이썬 리터럴을 JSON 으로 옮깁니다. 튜플은 배열로, 홑따옴표는 쌍따옴표로.
function pyToJson(text) {
  let out = "";
  let quote = null;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quote) {
      if (c === "\\") { out += c + (text[i + 1] || ""); i++; continue; }
      if (c === quote) { quote = null; out += '"'; continue; }
      if (c === '"') { out += '\\"'; continue; }   // 홑따옴표 안의 쌍따옴표
      out += c;
      continue;
    }
    if (c === "'" || c === '"') { quote = c; out += '"'; continue; }
    if (c === "(") { out += "["; continue; }
    if (c === ")") { out += "]"; continue; }
    out += c;
  }
  return out.replace(/,(\s*[\]}])/g, "$1");        // 파이썬이 허용하는 끝쉼표 제거
}

function pyLiteral(src, name) {
  const raw = readValue(src, name);
  if (raw === null) throw new Error(name + " 을 찾지 못했습니다");
  return JSON.parse(pyToJson(raw));
}

function slotsFromSettings(path) {
  const src = stripComments(fs.readFileSync(path, "utf8"));
  const ask = pyLiteral(src, "ASK_SLOTS");
  if (!Array.isArray(ask) || !ask.length) throw new Error("ASK_SLOTS 가 비어 있습니다");
  return {
    ask: ask,
    domains: pyLiteral(src, "DOMAIN_SLOTS"),
    filters: pyLiteral(src, "FILTERS"),
    ask_style: pyLiteral(src, "ASK_STYLE"),
    history_turns: pyLiteral(src, "HISTORY_TURNS")
  };
}

// ----------------------------------------------------------------
//  열쇠
// ----------------------------------------------------------------
const KEYS = ["SUPABASE_URL", "SUPABASE_ANON_KEY"];
const cfg = {};
const missing = [];

for (const k of KEYS) {
  const v = process.env[k];
  if (v && v.trim()) cfg[k] = v.trim();
  else missing.push(k);
}

if (missing.length) {
  console.error("환경 변수가 비어 있습니다: " + missing.join(", "));
  console.error("버셀 Settings -> Environment Variables 에서 넣고 다시 배포하세요.");
  console.error("빈 config.js 를 만들고 계속합니다. 사이트는 예약 내역을 못 불러옵니다.");
}

// ----------------------------------------------------------------
//  칸 목록 - settings.py 가 먼저, 안 되면 slots.json
// ----------------------------------------------------------------
let source = "";
let slotNote = "칸 목록 없음 - 웹 기본값을 씁니다";

try {
  cfg.SLOTS = slotsFromSettings("settings.py");
  source = "settings.py";
} catch (e) {
  console.error("settings.py 를 읽지 못했습니다: " + e.message);
  console.error("slots.json 으로 물러섭니다. 그 파일이 오래됐으면 배포도 오래된 채로 나갑니다.");
  try {
    const slots = JSON.parse(fs.readFileSync("slots.json", "utf8"));
    if (slots && Array.isArray(slots.ask) && slots.ask.length) {
      cfg.SLOTS = slots;
      source = "slots.json (대체)";
    }
  } catch (e2) {
    // 둘 다 없으면 칸 목록 없이 갑니다. 배포는 계속됩니다.
  }
}

if (cfg.SLOTS) {
  slotNote = "묻는 칸 " + cfg.SLOTS.ask.length + "개 · " +
    cfg.SLOTS.ask.map(function (p) { return p[0]; }).join(" / ");
}

const out =
  "// 배포할 때 build.js 가 만든 파일입니다. 직접 고치지 마세요.\n" +
  "window.APP_CONFIG = " + JSON.stringify(cfg, null, 2) + ";\n";

fs.writeFileSync("config.js", out);

const key = cfg.SUPABASE_ANON_KEY || "";
console.log("config.js 를 만들었습니다.");
console.log("  SUPABASE_URL       " + (cfg.SUPABASE_URL || "(없음)"));
console.log("  SUPABASE_ANON_KEY  " + (key ? key.slice(0, 12) + "... (길이 " + key.length + ")" : "(없음)"));
console.log("  칸 목록 출처       " + (source || "(없음)"));
console.log("  칸 목록            " + slotNote);
if (cfg.SLOTS) {
  console.log("  ASK_STYLE          " + cfg.SLOTS.ask_style);
  console.log("  HISTORY_TURNS      " + cfg.SLOTS.history_turns);
}