# -*- coding: utf-8 -*-
"""
index.html 패치 - 창(history)을 모델에 실어 보내고, 계측 화면에서 창 폭을 바꿔 봅니다.

    python patch_index.py

무엇을 고치나
  1. HIST 를 상수에서 변수로. settings.py 값은 HIST_CFG 로 따로 보관합니다.
  2. extractLLM 이 최근 HIST 턴을 같이 보냅니다.  (api/extract.js 도 같이 바꿔야 합니다)
  3. 봇이 한 말을 턴에 적어 둡니다. 창에는 유저 말과 봇 답이 같이 들어갑니다.
  4. 계측 화면 말머리에 "모델이 실제로 본 줄" 을 찍습니다.
  5. 챗봇 탭에 창 폭 조절기를 답니다. 계측 화면에서만 보입니다.

안전장치
  각 자리가 원문에 정확히 한 번 있는지 먼저 다 확인합니다.
  하나라도 어긋나면 아무것도 안 고치고 멈춥니다.
  고치기 전에 index.html.bak 을 남깁니다.
"""

import shutil
import sys
from pathlib import Path

SRC = Path("index.html")
BAK = Path("index.html.bak")

# ----------------------------------------------------------------
#  (찾을 것, 바꿀 것, 설명)
# ----------------------------------------------------------------
EDITS = []


# 1. HIST 를 변수로. settings.py 가 준 값은 HIST_CFG 에 따로 둡니다.
EDITS.append((
    r'const HIST = (SLOTS && SLOTS.history_turns) || 2;',
    r'''// settings.py 가 준 값이 정본입니다. HIST 는 계측 화면에서 잠깐 얹어 보는 값입니다.
// 조절기로 바꿔도 settings.py 는 그대로입니다. 제출은 settings.py 기준입니다.
const HIST_CFG = (SLOTS && SLOTS.history_turns) || 2;
let   HIST     = HIST_CFG;''',
    "HIST 를 변수로 (HIST_CFG 추가)",
))


# 2. 모델이 본 줄을 담아 둘 자리
EDITS.append((
    r'let LAST_RAW = "";',
    r'''let LAST_RAW = "";
let LAST_WINDOW = [];   // 모델이 실제로 본 줄들. 창 밖은 여기 없습니다.''',
    "LAST_WINDOW 변수 추가",
))


# 3. extractLLM 이 창을 받습니다
EDITS.append((
    r'async function extractLLM(text){',
    r'async function extractLLM(text, history){',
    "extractLLM 에 history 인자",
))

EDITS.append((
    r'body: JSON.stringify({ text: text, names: LLM_NAMES })',
    r'body: JSON.stringify({ text: text, names: LLM_NAMES, history: history || [] })',
    "요청 본문에 history 싣기",
))

EDITS.append((
    r'LAST_RAW = data.raw || "";',
    r'''LAST_RAW = data.raw || "";
  LAST_WINDOW = data.window || [];''',
    "응답에서 창 받아오기",
))


# 4. 부르는 자리 - 창을 만들어 넘기고, 원문 그대로 보냅니다
EDITS.append((
    r'''  let got = null;
  try {
    got = await extractLLM(src);
    if (got) ENGINE = "llm";''',
    r'''  // 모델에게 넘길 창. settings.py 의 HISTORY_TURNS 가 여기서 실제로 쓰입니다.
  //   넘긴 것 = HISTORY_TURNS x 2 + 1     (마지막 +1 이 방금 친 말)
  // HIST 가 0 이면 slice(-0) 이 전체를 돌려주므로 따로 막습니다.
  const win = (HIST > 0 ? turns.slice(-HIST) : []).map(function(t){
    return { user: t.me, bot: t.bot || "" };
  });
  let got = null;
  try {
    // 원문을 그대로 넘깁니다. 대명사를 손으로 치환해 주면 창이 일을 안 하게 됩니다.
    // "거기" 를 창으로 푸는지 못 푸는지가 이 실습에서 볼 것입니다.
    // 예전처럼 돌리려면 text 를 src 로 되돌리세요.
    got = await extractLLM(text, win);
    if (got) ENGINE = "llm";''',
    "창을 만들어 넘기기 (src -> text)",
))


# 5. 봇이 한 말을 턴에 적어 둡니다
EDITS.append((
    r'''function bubble(cls, htmlStr){
  const d = document.createElement("div");
  d.className = "bub bub--" + cls;
  d.innerHTML = htmlStr;
  $("chat-log").appendChild(d);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
}''',
    r'''function bubble(cls, htmlStr){
  const d = document.createElement("div");
  d.className = "bub bub--" + cls;
  d.innerHTML = htmlStr;
  $("chat-log").appendChild(d);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
}

// 봇이 한 말을 지금 턴에 적어 둡니다. 다음 턴의 창에 이 줄이 같이 들어갑니다.
// 봇 발화가 창에 남아야 하는 이유 - 손님이 안 되풀이한 이름이 봇 답에는 남아 있습니다.
function sayBot(head, plain){
  bubble("bot", head + esc(plain));
  if (turns.length) turns[turns.length - 1].bot = plain;
}''',
    "sayBot 추가",
))

EDITS.append((
    r'''    bubble("bot", head + esc(
      "장소를 " + box.place_name + josa(box.place_name) + " 바꿨습니다.\n" +
      LABEL[stale] + eun(LABEL[stale]) + " 아직 " + prevName + "입니다. " +
      box.place_name + josa(box.place_name) + " 같이 바꿀까요? 그대로 두셔도 됩니다."));''',
    r'''    sayBot(head,
      "장소를 " + box.place_name + josa(box.place_name) + " 바꿨습니다.\n" +
      LABEL[stale] + eun(LABEL[stale]) + " 아직 " + prevName + "입니다. " +
      box.place_name + josa(box.place_name) + " 같이 바꿀까요? 그대로 두셔도 됩니다.");''',
    "잔존 확인 발화 기록",
))

EDITS.append((
    r'''    bubble("bot", head + esc(pre +
      nm + "에서 택시를 타세요, 아니면 " + nm + josa(nm) + " 가세요?"));''',
    r'''    sayBot(head, pre +
      nm + "에서 택시를 타세요, 아니면 " + nm + josa(nm) + " 가세요?");''',
    "이월 질문 발화 기록",
))

EDITS.append((
    r'    bubble("bot", head + esc(lead + bar + body));',
    r'    sayBot(head, lead + bar + body);',
    "되묻기 발화 기록",
))


# 6. 계측 말머리에 창을 찍습니다
EDITS.append((
    r'  if (ENGINE === "llm" && LAST_RAW) out += "\n모델 원문 " + esc(LAST_RAW) + "\n";',
    r'''  if (ENGINE === "llm"){
    // 모델이 실제로 본 줄입니다. 위의 "밀림" 표시가 창 밖에 있는 것이고요.
    out += "\n창 " + HIST + "턴 · " + LAST_WINDOW.length + "줄  " +
      (LAST_WINDOW.length ? esc(LAST_WINDOW.join("  |  ")) : "(빈 창 · 방금 친 말만)");
    if (LAST_RAW) out += "\n모델 원문 " + esc(LAST_RAW);
    out += "\n";
  }''',
    "계측 말머리에 창 표시",
))


# 7. 조절기 - 화면
EDITS.append((
    r'.chat__quick{display:flex;flex-wrap:wrap;gap:8px}',
    r'''.chat__quick{display:flex;flex-wrap:wrap;gap:8px}
.labbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12.5px;color:var(--muted)}
.labbar .chip{padding:5px 12px;font-size:13px}
.labbar__note{color:var(--muted-soft)}''',
    "조절기 CSS",
))

EDITS.append((
    r'<div class="chat__quick" id="chat-quick" hidden></div>',
    r'''<div class="labbar" id="lab-hist" hidden>
          <span>창 폭</span>
          <button type="button" class="chip" data-hist="0">0턴</button>
          <button type="button" class="chip" data-hist="1">1턴</button>
          <button type="button" class="chip" data-hist="2">2턴</button>
          <button type="button" class="chip" data-hist="3">3턴</button>
          <span class="labbar__note" id="lab-hist-note"></span>
        </div>
        <div class="chat__quick" id="chat-quick" hidden></div>''',
    "조절기 마크업",
))


# 8. 조절기 - 동작
EDITS.append((
    r'''  QUICK.forEach(function(pair){
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.textContent = pair[0];
    b.addEventListener("click", function(){ $("chat-input").value = pair[1]; chatSend(); });
    q.appendChild(b);
  });
}''',
    r'''  QUICK.forEach(function(pair){
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.textContent = pair[0];
    b.addEventListener("click", function(){ $("chat-input").value = pair[1]; chatSend(); });
    q.appendChild(b);
  });

  // 창 폭 조절기. settings.py 를 덮어쓰는 게 아니라 잠깐 얹어 보는 것입니다.
  // 대화 중간에 폭을 바꾸면 앞 턴이 어느 폭으로 쌓였는지 알 수 없어져 판을 새로 깝니다.
  const hb = $("lab-hist");
  hb.hidden = false;
  const paintHist = function(){
    Array.prototype.forEach.call(hb.querySelectorAll("[data-hist]"), function(b){
      b.setAttribute("aria-pressed",
        Number(b.getAttribute("data-hist")) === HIST ? "true" : "false");
    });
    $("lab-hist-note").textContent = (HIST === HIST_CFG)
      ? "settings.py 값 그대로 " + HIST_CFG + "턴"
      : "임시 " + HIST + "턴 · settings.py 는 " + HIST_CFG + "턴";
    $("bot-note").textContent =
      "터미널의 Gradio 봇과 같은 칸 " + ASK.length + "개. 지금 창은 " + HIST + "턴입니다.";
  };
  hb.addEventListener("click", function(ev){
    const b = ev.target.closest("[data-hist]");
    if (!b) return;
    HIST = Number(b.getAttribute("data-hist"));
    paintHist();
    chatReset();       // 폭이 바뀌면 처음부터. 섞이면 측정이 무의미해집니다
  });
  paintHist();
}''',
    "조절기 동작",
))


# 9. 창 폭이 바뀌므로 "2턴" 을 문구에서 뺍니다
EDITS.append((
    r'지운 글씨는 말씀하셨지만 봇이 2턴 창 밖으로 놓친 칸입니다.',
    r'지운 글씨는 말씀하셨지만 봇이 창 밖으로 놓친 칸입니다.',
    "요약판 문구에서 고정된 2턴 제거",
))


def main():
    if not SRC.exists():
        print("index.html 이 이 폴더에 없습니다. 프로젝트 폴더에서 실행하세요.")
        return 1

    text = SRC.read_text(encoding="utf-8")

    if "HIST_CFG" in text:
        print("이미 패치된 파일로 보입니다 (HIST_CFG 가 있습니다). 아무것도 안 했습니다.")
        return 0

    # 먼저 전부 확인합니다. 하나라도 어긋나면 손대지 않습니다.
    bad = []
    for old, _new, why in EDITS:
        n = text.count(old)
        if n != 1:
            bad.append((why, n))

    if bad:
        print("자리를 못 찾았습니다. 파일을 고치지 않았습니다.\n")
        for why, n in bad:
            print("  [{}회] {}".format(n, why))
        print("\nindex.html 이 제가 본 판과 다른 것 같습니다. 그 파일을 그대로 올려 주세요.")
        return 1

    shutil.copy2(SRC, BAK)

    for old, new, why in EDITS:
        text = text.replace(old, new, 1)
        print("  고침 - " + why)

    SRC.write_text(text, encoding="utf-8")

    print("\n끝났습니다. 원본은 index.html.bak 에 있습니다.")

    api = Path("api") / "extract.js"
    if api.exists():
        if "history" not in api.read_text(encoding="utf-8"):
            print("\n주의 - api/extract.js 가 아직 history 를 안 받습니다.")
            print("       그 파일도 같이 바꾸지 않으면 창이 모델까지 가지 않습니다.")
    else:
        print("\n주의 - api/extract.js 를 못 찾았습니다.")

    print("\n다음 - python make_config.py 를 돌려야 settings.py 값이 웹에 반영됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
