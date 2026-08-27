// 버셀이 배포할 때 config.js 를 만들어 냅니다.
//
//   로컬에서는  python make_config.py   -> .env 를 읽습니다
//   버셀에서는  node build.js           -> 환경 변수를 읽습니다
//
// 둘 다 결과물은 같은 config.js 입니다.
// config.js 는 .gitignore 에 있어 저장소에 없습니다. 그래서 배포할 때 새로 만듭니다.
//
// 버셀 설정
//   Settings -> Environment Variables 에 SUPABASE_URL, SUPABASE_ANON_KEY 를 넣습니다
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
  console.error("빈 config.js 를 만들고 계속합니다. 사이트는 로컬 모드로 뜹니다.");
}

const out =
  "// 배포할 때 build.js 가 만든 파일입니다. 직접 고치지 마세요.\n" +
  "window.APP_CONFIG = " + JSON.stringify(cfg, null, 2) + ";\n";

fs.writeFileSync("config.js", out);

const key = cfg.SUPABASE_ANON_KEY || "";
console.log("config.js 를 만들었습니다.");
console.log("  SUPABASE_URL       " + (cfg.SUPABASE_URL || "(없음)"));
console.log("  SUPABASE_ANON_KEY  " + (key ? key.slice(0, 12) + "... (길이 " + key.length + ")" : "(없음)"));
