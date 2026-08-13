# 음성 비서 프로그램 (Voice Assistant)

음성으로 질문하면 AI가 답하고, 그 답변을 다시 음성으로 읽어 주는 웹 애플리케이션입니다.
《음성비서 만들기 — 진짜 챗GPT API 활용법》 PART 03의 실습을 구현했습니다.

## 동작 흐름

```
[사용자 음성 녹음]                 st.audio_input (스트림릿 내장)
        │
        ▼
[STT: 음성 → 텍스트]              Google Gemini (오디오 입력)
        │
        ▼
[답변 생성: 텍스트 → 텍스트]       Google Gemini (gemini-3.6-flash / gemini-3.5-flash-lite)
        │
        ▼
[TTS: 텍스트 → 음성]              Google Translate TTS (gTTS)
        │
        ▼
[웹 UI 출력 및 자동 재생]          Streamlit
```

이전 대화가 `st.session_state["messages"]` 에 누적되므로 후속 질문에서 앞선 대화 내용을
기억합니다. (예: "대한민국의 수도는?" → "서울입니다" → "**그 도시의** 인구는?" → 서울 인구로 답변)

## 파일 구성

| 파일 | 설명 |
|---|---|
| `ch03_voicebot.py` | 메인 애플리케이션 |
| `requirements.txt` | 파이썬 패키지 목록 (`streamlit`, `google-genai`, `gTTS` 3개뿐) |

## 로컬 실행 방법

```bash
python3 -m venv ch03_env
source ch03_env/bin/activate        # Windows: ch03_env\Scripts\activate.bat
pip install -r requirements.txt
streamlit run ch03_voicebot.py
```

브라우저에서 `http://localhost:8501` 로 접속한 뒤, 왼쪽 사이드바에 Gemini API 키를
입력하고 마이크 버튼으로 질문하면 됩니다.
키는 [Google AI Studio](https://aistudio.google.com/apikey) 에서 무료로 발급받습니다.

> **답변 음성이 재생되지 않는 경우** — 크롬의 자동 재생 차단 때문입니다.
> `설정 → 개인정보 보호 및 보안 → 사이트 설정 → 추가 콘텐츠 설정 → 소리` 에서
> `소리 재생이 허용됨` 항목에 접속 주소를 추가한 뒤 다시 실행하세요.

## API 키 처리

키는 두 경로로 받으며, 사이드바 입력이 우선입니다.

1. 사이드바의 `GEMINI API 키` 입력란 (교재 방식)
2. Streamlit Secrets 의 `GOOGLE_API_KEY`

Secrets 값을 입력란의 기본값(`value=`)으로 채우지 않고 API 호출 시점에만 읽습니다.
`type="password"` 로 마스킹하더라도 `value=` 에 넣은 값은 브라우저까지 전달되기 때문에,
공개 URL에서 키가 노출되는 것을 막기 위한 처리입니다.

로컬에서 Secrets를 쓰려면 `.streamlit/secrets.toml` 을 만들고 아래처럼 적습니다
(이 파일은 `.gitignore` 에 등록되어 있어 커밋되지 않습니다).

```toml
GOOGLE_API_KEY = "..."
```

## 교재와 다른 부분

교재는 2023년에 쓰였기 때문에 그대로 실행하면 동작하지 않는 부분이 있어 다음과 같이
수정했습니다.

### 1. OpenAI → Gemini 로 교체

교재는 STT에 OpenAI Whisper를, 답변 생성에 OpenAI GPT를 사용합니다. 두 가지 이유로
Google Gemini 로 바꿨습니다.

- 교재가 지정한 `gpt-4` 와 `gpt-3.5-turbo` 는 **2026년 10월 23일 OpenAI API에서 서비스가
  종료**됩니다 ([OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)).
- OpenAI API는 유료 크레딧이 있어야 호출되지만, Gemini는 무료 티어로 호출할 수 있어
  누구나 접속해서 바로 사용해 볼 수 있습니다.

교재의 각 단계가 무엇으로 대체되었는지는 아래와 같습니다. 파이프라인의 구조와
`STT()` → `ask_*()` → `TTS()` 라는 함수 구성은 교재와 동일하게 유지했습니다.

| 단계 | 교재 | 이 프로젝트 |
|---|---|---|
| 녹음 | `streamlit-audiorecorder` | `st.audio_input` (스트림릿 내장) |
| STT | OpenAI Whisper (`whisper-1`) | Gemini 오디오 입력 (`gemini-3.6-flash`) |
| 답변 | `gpt-4` / `gpt-3.5-turbo` | `gemini-3.6-flash` / `gemini-3.5-flash-lite` |
| TTS | gTTS | gTTS (교재와 동일) |
| UI | Streamlit | Streamlit (교재와 동일) |

Gemini 모델 선택지는 교재가 고성능(`gpt-4`) / 경량(`gpt-3.5-turbo`) 중에서 고르게 한 것과
같은 구성입니다. `pro` 계열은 무료 티어 대상이 아니라 제외했습니다.

**대화 기록 형식 변환** — 교재의 `messages` 구조
(`[{"role": "user"/"assistant", "content": ...}]`)를 그대로 유지하고, API를 호출하기
직전에만 Gemini 형식으로 변환합니다(`to_gemini_contents()`). Gemini는 답변자의 역할을
`assistant` 가 아니라 `model` 이라고 부르고 시스템 프롬프트를 대화 기록이 아닌 별도
설정으로 받기 때문입니다. 이렇게 하면 화면 표시·초기화 같은 나머지 로직을 교재 코드와
똑같이 둘 수 있습니다.

### 2. 녹음 위젯을 스트림릿 내장 위젯으로 교체

교재가 쓰는 `streamlit-audiorecorder` 는 `pydub` 에 의존하고, `pydub` 은 표준 라이브러리
`audioop` 을 사용합니다. `audioop` 은 **파이썬 3.13에서 제거**되었기 때문에 최신 파이썬
환경에서는 `import` 단계에서 바로 실패하고, mp3 변환을 위해 시스템 패키지 `ffmpeg`
(`packages.txt`)까지 따로 설치해야 합니다.

교재 출간 이후 스트림릿에 녹음 위젯 `st.audio_input` 이 내장되었으므로 이것으로
바꿨습니다. 그 결과 외부 패키지 `streamlit-audiorecorder` / `pydub`, 시스템 패키지
`ffmpeg`, 그리고 파이썬 버전 제약이 모두 사라졌습니다. 의존성은 `streamlit`,
`google-genai`, `gTTS` 세 개뿐이고, 배포할 때 Python 버전을 따로 지정할 필요가 없습니다.

### 3. 초기화 버튼을 누르면 이후 녹음이 처리되지 않는 문제

교재 코드는 `초기화` 버튼을 누를 때 `st.session_state["check_reset"] = True` 로 바꾸지만,
이 값을 다시 `False` 로 되돌리는 지점이 없습니다. 녹음 처리 조건이
`check_reset == False` 이므로, 초기화를 한 번 누르면 그 뒤로는 녹음을 해도 아무 반응이
없습니다. 처리 블록의 `else` 분기에서 플래그를 `False` 로 되돌리도록 했습니다.

### 4. 답변을 `role: "system"` 으로 저장하던 문제

교재는 AI의 답변을 `{"role": "system", "content": response}` 로 대화 기록에 넣습니다.
`system` 은 모델에게 내리는 지시문의 역할이므로, 대화가 길어질수록 답변 하나하나가
새로운 지시문으로 쌓여 모델의 동작이 흐트러집니다. 실제 역할에 맞게 `assistant` 로
저장하도록 고쳤습니다.

### 그 밖에

- 교재는 `pip freeze > requirements.txt` 를 안내하지만, 그러면 개발 환경에만 필요한
  패키지와 OS 종속적인 버전까지 모두 포함되어 배포 서버에서 설치가 실패하기 쉽습니다.
  실제로 필요한 패키지만 버전을 고정해 직접 작성했습니다.
- API 키가 비어 있는 상태로 녹음하면 호출에서 예외가 발생하며 화면에 스택 트레이스가
  그대로 노출되므로, 안내 메시지를 띄우고 멈추도록 했습니다.

## 배포

GitHub 리포지토리를 Streamlit Community Cloud 에 연결해 배포했습니다.

- 리포지토리: https://github.com/mimm-112/voicebot
- 배포 주소: *(배포 후 기재)*
