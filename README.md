# 가는길 — 장소 예약과 택시 배차

두 도메인(관광 · 택시)을 한 건으로 처리하는 서비스입니다.
같은 일을 **폼**과 **챗봇** 두 방식으로 해 보고 무엇이 편한지 비교하려고 만들었습니다.

```
https://0827-bot-bts.vercel.app/        예약 화면 — 폼 UI, Supabase 연결
https://0827-bot-bts.vercel.app/test    실습 화면 — 슬롯 현황 · 변경 이력 · 비교용 챗봇
```

**웹에 탭이 둘 있습니다.** 폼으로 예약, 챗봇으로 예약. 둘 다 같은 7칸을 채우고
같은 Supabase 테이블에 들어갑니다. 한 화면에서 바로 비교할 수 있습니다.

**Gradio 봇은 터미널에서 따로 돕니다.** `app.py` 를 켜면 `127.0.0.1:7860` 에 뜹니다.
웹 안 챗봇은 그 봇과 같은 칸·같은 기억 제약으로 도는 쌍둥이입니다.

---

## 무엇이 들어 있나

| 파일 | 하는 일 |
|---|---|
| `index.html` | 웹사이트. 폼 탭과 챗봇 탭. `/test` 에서는 슬롯 현황이 함께 나옵니다 |
| `app.py` | **Agent Bot.** 터미널에서 로컬로 돕니다. 킷 원본이며 고치지 않습니다 |
| `bot-requirements.txt` | 봇을 돌릴 때 설치할 것 |
| `check.py` | 열쇠와 모델이 살아 있는지 확인 |
| `settings.py` | **묻는 칸 목록.** 봇과 웹이 같이 읽습니다 |
| `schema.sql` | Supabase 테이블 3개 |
| `make_config.py` | 내 컴퓨터에서 `config.js` 와 `slots.json` 을 만듭니다 |
| `build.js` | 버셀이 배포할 때 `config.js` 를 만듭니다 |
| `vercel.json` | `/test` 를 실습 화면으로 연결합니다 |
| `scenarios.md` | 수정 시나리오 9개와 채점표 |
| `.env.example` | 열쇠 양식 |

저장소에 **올라가지 않는** 파일 둘: `.env`, `config.js`. 둘 다 `.gitignore` 가 막습니다.

---

## 칸 구조

묻는 칸 7개, 자동 칸 4개입니다.

| 도메인 | 묻는 칸 | 자동 칸 |
|---|---|---|
| 관광 | 종류 · 지역 · 이름 | 주소 · 연락처 · 평점 |
| 택시 | 출발지 · 도착지 · 출발 시간 · 종류 | 기사 연락처 |

두 도메인은 **장소 이름**에서 이어집니다. 폼에서는 장소 이름이 택시의 출발지나
도착지 한쪽에 자동으로 들어갑니다. 어느 쪽인지는 화면에서 고릅니다.

WoS 관광+택시 대화 1,297건을 세어 보면 이렇습니다.

| 장소와 택시가 이어지는 방식 | 비율 |
|---|---|
| 장소가 **출발지** (거기서 타고 나옴) | 47.2% |
| 둘 다 아님 (택시는 딴 데로) | 29.0% |
| 장소가 **도착지** (거기로 감) | 23.9% |

장소를 도착지로 고정하면 24%만 맞습니다. 그래서 방향을 고르게 두었습니다.

---

## 처음 한 번만 하는 것

**1. 테이블 만들기**
Supabase → SQL Editor → `schema.sql` 붙여넣고 Run.
맨 아래 `장소_건수 24` 가 나오면 성공입니다.

**2. 열쇠 넣기**

```
copy .env.example .env
```

`.env` 를 열어 채웁니다. 값은 Supabase → Settings → API Keys 에 있습니다.

```
SUPABASE_URL=https://내프로젝트.supabase.co
SUPABASE_ANON_KEY=여기에_키
GEMINI_API_KEY=여기에_키
```

`SUPABASE_ANON_KEY` 는 "API Keys" 탭의 Publishable key 나
"Legacy API Keys" 탭의 anon key 중 아무거나 됩니다.

**3. 설정 파일 만들기**

```
python make_config.py
```

`config.js` 와 `slots.json` 이 생깁니다. `index.html` 을 열면 바로 붙습니다.

---

## 두 방식 돌려보기

### 폼과 챗봇 (웹)

`index.html` 을 열고 위쪽 탭을 누릅니다. 둘 다 같은 7칸을 채우고,
다 차면 같은 Supabase 테이블에 예약이 들어갑니다.

챗봇은 페이지 안에서 돕니다. 슬롯 값이 닫힌 집합(장소 24곳, 지역 5, 종류 8, 택시 4)
이라 규칙으로 뽑아내며, 그래서 API 키를 브라우저에 내보내지 않습니다.

### Gradio 봇 (터미널)

```
.\.venv\Scripts\python.exe app.py
```

`127.0.0.1:7860` 에 뜹니다. 웹 안 챗봇과 같은 칸, 같은 기억 제약으로 돕니다.

---

## settings.py 가 유일한 출처입니다

```
settings.py  →  slots.json  →  config.js  →  index.html
   봇이 읽음      make_config.py                웹이 읽음
```

`ASK_SLOTS` 에서 줄을 지우면 **봇도 안 묻고 웹에서도 그 입력칸이 사라집니다.**
고친 뒤에는 `python make_config.py` 를 한 번 돌리세요.

---

## 오늘의 제약

`HISTORY_TURNS = 2` 로 고정입니다. 봇은 바로 앞 두 번의 주고받기만 봅니다.
묻는 칸이 7개인데 한 칸씩 물으면 7턴이 들고, 앞 5칸은 봇 시야에서 사라집니다.
`/test` 로 들어가면 밀려난 칸이 주황색으로 표시됩니다.

폼은 이 문제가 없습니다. 상태가 화면에 다 있고 DB 에 남기 때문입니다.
그 차이를 재는 것이 `scenarios.md` 의 시나리오 9개입니다.

---

## 배포

버셀 Settings 에서 이렇게 둡니다.

| 항목 | 값 |
|---|---|
| Framework Preset | Other |
| Build Command | `node build.js` (Override 켜기) |
| Output Directory | `.` (Override 켜기) |
| Environment Variables | `SUPABASE_URL`, `SUPABASE_ANON_KEY` |

환경 변수를 나중에 추가했으면 Deployments 에서 Redeploy 를 해야 반영됩니다.
빌드 로그에 `config.js 를 만들었습니다` 가 찍히면 성공입니다.

---

## 주의

`schema.sql` 의 정책은 로그인 없는 실습용입니다. 누구나 예약을 읽고 쓸 수 있습니다.
삭제와 장소 사전 수정은 막아 두었습니다. 발표가 끝나면 프로젝트를 지우거나
로그인을 붙이세요.

`anon key` 는 비밀이 아닙니다. 브라우저에 내려가는 값이라 사이트를 열면 보입니다.
`.env` 로 감추는 것은 저장소 이력에 남기지 않으려는 것이지, 배포된 사이트를
지켜 주지는 않습니다. 데이터를 지키는 것은 RLS 정책입니다.

`GEMINI_API_KEY` 는 진짜 비밀입니다. 봇만 쓰고 브라우저로는 나가지 않습니다.
