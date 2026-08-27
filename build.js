// 버셀이 배포할 때 config.js 를 만들어 냅니다.
//
//   로컬에서는  python make_config.py   -> .env + settings.py 를 읽습니다
//   버셀에서는  node build.js           -> 환경 변수 + slots.json 을 읽습니다
//
// slots.json 은 settings.py 에서 나온 칸 목록입니다. 비밀이 없어서 저장소에 올라갑니다.
// config.js 는 열쇠가 들어 있어 올라가지 않으므로, 배포할 때마다 새로 만듭니다.
//
// 버셀 설정
//   Settings -> Environment Variables 에 SUPABASE_URL, SUPABASE_ANON_KEY
//   Settings -> Build and Deployment
//     Framework Preset  Other
//     Build Command     node build.js      (Override 켜기)
//     Output Directory  .                  (Override 켜기)

const fs = require("fs");

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

let slotNote = "slots.json 없음 - 웹 기본 7칸을 씁니다";
try {
  const slots = JSON.parse(fs.readFileSync("slots.json", "utf8"));
  if (slots && Array.isArray(slots.ask) && slots.ask.length) {
    cfg.SLOTS = slots;
    slotNote = "묻는 칸 " + slots.ask.length + "개 · " +
      slots.ask.map(function (p) { return p[0]; }).join(" / ");
  }
} catch (e) {
  // 파일이 없거나 깨졌으면 칸 목록 없이 갑니다. 배포는 계속됩니다.
}

const out =
  "// 배포할 때 build.js 가 만든 파일입니다. 직접 고치지 마세요.\n" +
  "window.APP_CONFIG = " + JSON.stringify(cfg, null, 2) + ";\n";

fs.writeFileSync("config.js", out);

const key = cfg.SUPABASE_ANON_KEY || "";
console.log("config.js 를 만들었습니다.");
console.log("  SUPABASE_URL       " + (cfg.SUPABASE_URL || "(없음)"));
console.log("  SUPABASE_ANON_KEY  " + (key ? key.slice(0, 12) + "... (길이 " + key.length + ")" : "(없음)"));
console.log("  칸 목록            " + slotNote);
