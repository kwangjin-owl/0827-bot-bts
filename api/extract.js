// 버셀 서버리스 함수. 브라우저 대신 여기서 Gemini 를 부릅니다.
//
// 왜 서버를 거치나
//   브라우저에서 직접 부르면 GEMINI_API_KEY 가 페이지 소스에 그대로 보입니다.
//   배포된 사이트를 연 누구나 꺼내 쓸 수 있고, 요금은 내가 냅니다.
//   그래서 키는 서버에만 두고 브라우저는 이 함수만 부릅니다.
//
// 뽑는 방식은 app.py 의 _extract_once 와 같습니다.
// 같은 모델, 같은 프롬프트, 같은 파싱. 그래야 두 봇을 비교할 수 있습니다.
//
// history 를 받습니다
//   앞서는 방금 친 말 한 줄만 받았습니다. 그래서 HISTORY_TURNS 를 무엇으로 두든
//   모델이 보는 창은 늘 1턴이었고, 1과 2를 비교해도 모델 쪽 차이가 없었습니다.
//   이제 브라우저가 최근 HISTORY_TURNS 개의 주고받기를 같이 보냅니다.
//   넘긴 것 = HISTORY_TURNS x 2 + 1     (마지막 +1 이 방금 친 말)
//   창 밖으로 나간 턴은 여기 안 실립니다. 그것이 "범위 밖으로 밀림" 입니다.
//
// 버셀 설정
//   Settings -> Environment Variables
//     GEMINI_API_KEY   필수
//     GEMINI_MODEL     선택. 비우면 gemini-3.5-flash-lite

const DEFAULT_MODEL = "gemini-3.5-flash-lite";

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "POST 만 받습니다" });
    return;
  }

  const key = process.env.GEMINI_API_KEY;
  if (!key) {
    res.status(500).json({ error: "GEMINI_API_KEY 가 설정되지 않았습니다" });
    return;
  }

  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  const text = (body && body.text ? String(body.text) : "").slice(0, 500);
  const names = (body && Array.isArray(body.names)) ? body.names.slice(0, 30) : [];
  if (!text || !names.length) {
    res.status(400).json({ error: "text 와 names 가 필요합니다" });
    return;
  }

  // 창. 브라우저가 잘라서 보낸 것을 그대로 씁니다. 여기서 더 자르지 않습니다.
  // 몇 턴을 넘길지는 settings.py 의 HISTORY_TURNS 가 정합니다.
  const history = (body && Array.isArray(body.history)) ? body.history.slice(-8) : [];

  // 항목별로 고를 수 있는 값. 브라우저가 장소 사전과 settings.py 에서 뽑아 보냅니다.
  // 없으면 예전처럼 이름만 보냅니다.
  const choices = (body && body.choices && typeof body.choices === "object") ? body.choices : {};
  const lines = [];
  history.forEach(function (t) {
    if (!t) return;
    const u = t.user ? String(t.user).replace(/\s+/g, " ").slice(0, 300) : "";
    const b = t.bot ? String(t.bot).replace(/\s+/g, " ").slice(0, 300) : "";
    if (u) lines.push("user: " + u);
    if (b) lines.push("assistant: " + b);
  });

  // app.py 의 프롬프트에 앞 대화 자리를 더했습니다.
  // 창이 비어 있으면 그 자리를 통째로 빼서, 예전과 같은 문장이 나갑니다.
  // 고를 값을 알려 줍니다. 이게 없으면 모델이 "장소 갈래" 를 비우고
  // "장소 종류" 에 관광지를 넣거나, 지역을 "서울 남쪽" 대신 "서울" 로 뽑습니다.
  const guide = [];
  names.forEach(function (n) {
    const c = choices[n];
    if (Array.isArray(c) && c.length) guide.push("- " + n + " : " + c.join(" / "));
    else if (typeof c === "string" && c.trim()) guide.push("- " + n + " : " + c.trim());
  });

  const prompt =
    "다음 문장에서 아래 항목을 찾아 JSON 으로만 답하세요.\n" +
    "찾지 못한 항목은 빈 문자열로 두세요. 설명은 쓰지 마세요.\n" +
    (guide.length
      ? "항목별로 쓸 수 있는 값입니다. 목록이 있는 항목은 그 안의 값을 그대로 적으세요.\n" +
        "비슷한 말을 들으면 목록의 표현으로 바꿔 적고, 해당하는 것이 없으면 비워 두세요.\n" +
        guide.join("\n") + "\n"
      : "") +
    (lines.length
      ? "앞 대화는 참고만 하세요. 값은 마지막 문장을 기준으로 채웁니다.\n" +
        "'거기' 같은 말이 가리키는 곳은 앞 대화에서 찾으세요.\n" +
        "앞 대화:\n" + lines.join("\n") + "\n"
      : "") +
    "항목: " + names.join(", ") + "\n" +
    "문장: " + text;

  const model = process.env.GEMINI_MODEL || DEFAULT_MODEL;
  const url = "https://generativelanguage.googleapis.com/v1beta/models/" +
    encodeURIComponent(model) + ":generateContent";

  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0, maxOutputTokens: 512 }
      })
    });

    if (!r.ok) {
      const detail = (await r.text()).slice(0, 300);
      res.status(502).json({ error: "Gemini 응답 오류 " + r.status, detail: detail, model: model });
      return;
    }

    const data = await r.json();
    const parts = ((((data.candidates || [])[0] || {}).content || {}).parts) || [];
    let raw = parts.map(function (p) { return p.text || ""; }).join("");

    // app.py 와 같은 방식으로 벗겨냅니다.
    raw = raw.replace(/```json/g, "").replace(/```/g, "");
    const m = raw.match(/\{[\s\S]*\}/);
    let got = {};
    if (m) { try { got = JSON.parse(m[0]); } catch (e) { got = {}; } }

    // 물어본 항목만 돌려줍니다. 모델이 없는 칸을 지어내도 걸러집니다.
    const out = {};
    names.forEach(function (n) {
      const v = got[n];
      out[n] = (v === undefined || v === null) ? "" : String(v).trim();
    });

    // window 는 계측 화면에서 "모델이 실제로 본 것" 으로 띄웁니다.
    res.status(200).json({
      got: out,
      raw: raw.trim().slice(0, 400),
      model: model,
      window: lines,
      turns: history.length
    });
  } catch (e) {
    res.status(500).json({ error: String(e && e.message ? e.message : e).slice(0, 200) });
  }
};