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

  // app.py 의 프롬프트를 글자 그대로 옮겼습니다.
  const prompt =
    "다음 문장에서 아래 항목을 찾아 JSON 으로만 답하세요.\n" +
    "찾지 못한 항목은 빈 문자열로 두세요. 설명은 쓰지 마세요.\n" +
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

    res.status(200).json({ got: out, raw: raw.trim().slice(0, 400), model: model });
  } catch (e) {
    res.status(500).json({ error: String(e && e.message ? e.message : e).slice(0, 200) });
  }
};
