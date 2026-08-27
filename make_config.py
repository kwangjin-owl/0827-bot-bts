#!/usr/bin/env python3
"""
.env 를 읽어 config.js 를 만듭니다.

    python make_config.py

왜 이 단계가 필요한가
--------------------
브라우저는 .env 를 읽지 못합니다. .env 는 서버나 빌드 도구가 읽는 규칙이고,
index.html 은 서버 없이 그냥 열리는 파일이기 때문입니다.
그래서 값의 출처는 .env 하나로 두고, 이 스크립트가 브라우저가 읽을 수 있는
config.js 로 옮겨 적습니다.

    .env        진짜 값.        git 에 안 올라감
    config.js   자동 생성 파일.  git 에 안 올라감
    index.html  config.js 를 읽음. git 에 올라감 - 값이 없으므로 안전

값을 바꿨으면 이 스크립트를 다시 돌리세요.
설치할 것은 없습니다. 표준 파이썬만 씁니다.
"""

import json
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
OUT_PATH = os.path.join(HERE, "config.js")

# 브라우저로 내보낼 이름. 여기 없는 값은 config.js 에 들어가지 않습니다.
# GEMINI_API_KEY 는 일부러 뺐습니다. 그것은 봇이 서버 쪽에서 쓰는 키이고,
# 브라우저에 내보내면 페이지를 여는 누구나 볼 수 있습니다.
EXPORT = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]


def read_env(path):
    """.env 를 한 줄씩 읽습니다. python-dotenv 없이 동작합니다."""
    values = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            values[key] = val
    return values


def main():
    if not os.path.exists(ENV_PATH):
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

    body = ",\n".join(
        "  {}: {}".format(k, json.dumps(env[k], ensure_ascii=False)) for k in EXPORT
    )
    out = (
        "// 자동 생성 파일입니다. 직접 고치지 마세요.\n"
        "// 값을 바꾸려면 .env 를 고치고  python make_config.py  를 다시 돌리세요.\n"
        "// 이 파일은 .gitignore 에 들어 있습니다.\n"
        "window.APP_CONFIG = {\n" + body + "\n};\n"
    )
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)

    key = env["SUPABASE_ANON_KEY"]
    print("config.js 를 만들었습니다.")
    print("  SUPABASE_URL       " + env["SUPABASE_URL"])
    print("  SUPABASE_ANON_KEY  {}... (길이 {})".format(key[:12], len(key)))

    # .gitignore 가 실제로 막고 있는지 확인합니다. 안 막고 있으면 커밋 사고가 납니다.
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
