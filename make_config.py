#!/usr/bin/env python3
"""
.env 와 settings.py 를 읽어 config.js 와 slots.json 을 만듭니다.

    python make_config.py

무엇이 어디서 오는가
--------------------
    .env         Supabase 열쇠.          git 에 안 올라감
    settings.py  봇이 묻는 칸 목록.       git 에 올라감
        |
        v
    slots.json   칸 목록만 뽑은 것.       git 에 올라감 (비밀 없음)
    config.js    열쇠 + 칸 목록.          git 에 안 올라감
        |
        v
    index.html   config.js 를 읽어 폼을 그림

브라우저는 .env 도 settings.py 도 읽지 못합니다. 그래서 이 스크립트가 옮겨 적습니다.
settings.py 에서 칸을 지우면 봇과 웹에서 같이 사라집니다.
값을 바꿨으면 이 스크립트를 다시 돌리세요. 설치할 것은 없습니다.
"""

import ast
import json
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
SETTINGS_PATH = os.path.join(HERE, "settings.py")
CONFIG_PATH = os.path.join(HERE, "config.js")
SLOTS_PATH = os.path.join(HERE, "slots.json")

# 브라우저로 내보낼 열쇠. GEMINI_API_KEY 는 일부러 뺐습니다.
# 그것은 봇이 쓰는 키라 브라우저에 나가면 페이지를 여는 누구나 볼 수 있습니다.
EXPORT = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
# 비어 있어도 넘어가는 값. 챗봇 탭은 주소가 있을 때만 나타납니다.


def read_env(path):
    """.env 를 한 줄씩 읽습니다. python-dotenv 없이 동작합니다."""
    values = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            values[key] = val
    return values


def read_settings(path):
    """settings.py 에서 값만 꺼냅니다.

    import 하지 않고 ast 로 읽습니다. 그래야 settings.py 안의 코드가
    실행되지 않고, 파일에 실수가 있어도 이 스크립트가 같이 죽지 않습니다.
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                pass
    return out


def build_slots():
    """settings.py 가 있으면 칸 목록을 만들고, 없으면 None 을 돌려줍니다."""
    if not os.path.exists(SETTINGS_PATH):
        print("settings.py 가 없습니다. 칸 목록은 건너뜁니다.")
        print("  웹은 자기 안에 든 기본 7칸을 씁니다.")
        return None

    s = read_settings(SETTINGS_PATH)
    ask = s.get("ASK_SLOTS")
    if not ask:
        print("settings.py 에서 ASK_SLOTS 를 못 찾았습니다. 칸 목록은 건너뜁니다.")
        return None

    names = [pair[0] for pair in ask]
    dup = [n for n in names if names.count(n) > 1]
    if dup:
        print("경고 - 칸 이름이 겹칩니다: " + ", ".join(sorted(set(dup))))
        print("       겹치면 모델이 뽑은 JSON 에서 한쪽이 덮어써집니다. 이름을 갈라 주세요.")

    slots = {
        "ask": [[p[0], p[1]] for p in ask],
        "auto": s.get("AUTO_SLOTS", {}),
        "ask_style": s.get("ASK_STYLE", ""),
        "history_turns": s.get("HISTORY_TURNS", 0),
    }
    with open(SLOTS_PATH, "w", encoding="utf-8") as f:
        json.dump(slots, f, ensure_ascii=False, indent=2)
    print("slots.json 을 만들었습니다.  묻는 칸 {}개 · 자동 칸 {}개".format(
        len(slots["ask"]), len(slots["auto"])))
    print("  " + " / ".join(names))
    return slots


def main():
    slots = build_slots()

    if not os.path.exists(ENV_PATH):
        print()
        print(".env 가 없습니다.")
        print("  [ Windows ]  copy .env.example .env")
        print("  [ Mac ]      cp .env.example .env")
        print("그 다음 값을 채우고 다시 돌리세요.")
        return 1

    env = read_env(ENV_PATH)
    missing = [k for k in EXPORT if not env.get(k)]
    if missing:
        print("값이 비어 있습니다: " + ", ".join(missing))
        print(".env 를 열어 채운 뒤 다시 돌리세요.")
        return 1
    if "YOUR-PROJECT" in env["SUPABASE_URL"]:
        print("SUPABASE_URL 이 예시 그대로입니다. 자기 프로젝트 주소로 바꾸세요.")
        return 1

    cfg = {k: env[k] for k in EXPORT}
    if slots:
        cfg["SLOTS"] = slots

    out = (
        "// 자동 생성 파일입니다. 직접 고치지 마세요.\n"
        "// .env 와 settings.py 를 고치고  python make_config.py  를 다시 돌리세요.\n"
        "// 이 파일은 .gitignore 에 들어 있습니다.\n"
        "window.APP_CONFIG = " + json.dumps(cfg, ensure_ascii=False, indent=2) + ";\n"
    )
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(out)

    key = env["SUPABASE_ANON_KEY"]
    print()
    print("config.js 를 만들었습니다.")
    print("  SUPABASE_URL       " + env["SUPABASE_URL"])
    print("  SUPABASE_ANON_KEY  {}... (길이 {})".format(key[:12], len(key)))

    gi = os.path.join(HERE, ".gitignore")
    if os.path.exists(gi):
        text = open(gi, encoding="utf-8").read()
        for name in (".env", "config.js"):
            if name not in text:
                print("경고 - .gitignore 에 {} 가 없습니다. 추가하세요.".format(name))
    else:
        print("경고 - .gitignore 가 없습니다. .env 와 config.js 가 커밋될 수 있습니다.")

    print("이제 index.html 을 열면 바로 붙습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
