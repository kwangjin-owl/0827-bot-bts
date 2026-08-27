# 이 파일은 열지 않습니다. settings.py 만 바꿉니다.
import warnings
# 켤 때마다 뜨는 deprecated 경고를 감춘다. 학생이 그것을 에러로 읽는다(260827 실측).
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="gradio")
import sys
# Windows 터미널은 한글을 cp949 로 그려서 안내문이 깨진다(260827 실측).
# 이 두 줄이 있어야 학생이 메시지를 읽을 수 있다.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os, json, re
import gradio as gr
import google.generativeai as genai
from dotenv import load_dotenv
import settings

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.5-flash-lite")

NAMES = [n for n, _ in settings.ASK_SLOTS]

# 같은 말을 두 번 뽑지 않는다. 뽑은 결과를 기억해 둔다.
_seen = {}
LAST_ERROR = [""]


def extract(text):
    key = (text, tuple(NAMES))
    if key in _seen:
        return dict(_seen[key])
    got = _extract_once(text)
    _seen[key] = dict(got)
    return got


def _extract_once(text):
    """유저가 친 말 한 개에서 칸을 뽑아낸다. 못 뽑으면 빈 문자열."""
    prompt = (
        "다음 문장에서 아래 항목을 찾아 JSON 으로만 답하세요.\n"
        "찾지 못한 항목은 빈 문자열로 두세요. 설명은 쓰지 마세요.\n"
        f"항목: {', '.join(NAMES)}\n"
        f"문장: {text}"
    )
    try:
        raw = model.generate_content(prompt).text
        raw = raw.replace("```json", "").replace("```", "")
        m = re.search(r"\{.*\}", raw, re.S)
        got = json.loads(m.group(0)) if m else {}
    except Exception as e:
        LAST_ERROR[0] = f"{type(e).__name__}: {str(e)[:120]}"
        got = {}
    return {n: str(got.get(n, "")).strip() for n in NAMES}


def _user_said(history):
    """유저 발화만 시간순으로 뽑는다.
    gradio 는 버전에 따라 history 를 (내 말, 봇 답) 튜플로도,
    {"role": ..., "content": ...} 목록으로도 준다(260827 실측 - dict 를
    튜플처럼 풀면 발화 대신 "role" 글자가 들어가 앞 턴이 전부 증발한다)."""
    out = []
    for h in history:
        if isinstance(h, dict):
            if h.get("role") == "user":
                out.append(str(h.get("content", "")))
        else:
            out.append(str(h[0]))
    return out


def merge(history):
    """건네받은 범위 안에서만 칸을 모은다. 범위 밖은 없는 것과 같다."""
    box = {n: "" for n in NAMES}
    said = _user_said(history)
    recent = said[-settings.HISTORY_TURNS:] if settings.HISTORY_TURNS > 0 else []
    for u in recent:
        for k, v in extract(u).items():
            if v:
                box[k] = v
    return box


def all_seen(history):
    """건네는 범위와 무관하게, 유저가 지금까지 말한 것 전부."""
    seen = {n: "" for n in NAMES}
    for u in _user_said(history):
        for k, v in extract(u).items():
            if v:
                seen[k] = v
    return seen


def chat(message, history):
    box = merge(history)
    ever = all_seen(history)
    for k, v in extract(message).items():
        if v:
            box[k] = v
            ever[k] = v

    missing = [n for n in NAMES if not box[n]]
    filled = len(NAMES) - len(missing)
    head = (
        f"채운 칸: {filled}/{len(NAMES)}  "
        f"(ASK_STYLE={settings.ASK_STYLE}, HISTORY_TURNS={settings.HISTORY_TURNS})\n"
        + " | ".join(
            f"{n}: {box[n]}" if box[n]
            else (f"{n}: - (범위 밖으로 밀림)" if ever[n] else f"{n}: -")
            for n in NAMES)
        + "\n" + "-" * 46 + "\n"
    )

    if missing:
        ask = dict(settings.ASK_SLOTS)
        if settings.ASK_STYLE == "all_at_once":
            body = "배차하려면 아래를 한 번에 알려 주세요.\n" + "\n".join(
                f"- {n}: {ask[n]}" for n in missing)
        else:
            body = ask[missing[0]]
        return head + body

    auto = "\n".join(f"- {k}: {v}" for k, v in settings.AUTO_SLOTS.items())
    return head + "배차했습니다.\n" + "\n".join(
        f"- {n}: {box[n]}" for n in NAMES) + "\n" + auto


demo = gr.ChatInterface(chat)
demo.launch()
