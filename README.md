# 음성 비서 프로그램 (Voice Assistant)

음성으로 질문하면 GPT가 답하고, 그 답변을 다시 음성으로 읽어 주는 웹 애플리케이션입니다.
《음성비서 만들기 — 진짜 챗GPT API 활용법》 PART 03의 실습을 구현했습니다.

## 동작 흐름

```
[사용자 음성 녹음]                 streamlit-audiorecorder
        │
        ▼
[STT: 음성 → 텍스트]              OpenAI Whisper (whisper-1)
        │
        ▼
[답변 생성: 텍스트 → 텍스트]       OpenAI GPT (gpt-4o / gpt-4o-mini)
        │
        ▼
[TTS: 텍스트 → 음성]              Google Translate TTS (gTTS)
        │
        ▼
[웹 UI 출력 및 자동 재생]          Streamlit
```

이전 대화가 `st.session_state["messages"]` 에 누적되므로 후속 질문에서 앞선 대화 내용을 기억합니다.

## 파일 구성

| 파일 | 설명 |
|---|---|
| `ch03_voicebot.py` | 메인 애플리케이션 |
| `requirements.txt` | 파이썬 패키지 목록 |
| `packages.txt` | 시스템 패키지 (ffmpeg — pydub의 mp3 변환에 필요) |

## 로컬 실행 방법

```bash
# 1. 가상 환경 생성 (파이썬 3.12 — 아래 '주의' 참고)
python3.12 -m venv ch03_env
source ch03_env/bin/activate        # Windows: ch03_env\Scripts\activate.bat

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 실행
streamlit run ch03_voicebot.py
```

브라우저에서 `http://localhost:8501` 로 접속한 뒤, 왼쪽 사이드바에 본인의 OpenAI API 키를
입력하고 `클릭하여 녹음하기` 버튼으로 질문하면 됩니다.

> **답변 음성이 재생되지 않는 경우** — 크롬의 자동 재생 차단 때문입니다.
> `설정 → 개인정보 보호 및 보안 → 사이트 설정 → 추가 콘텐츠 설정 → 소리` 에서
> `소리 재생이 허용됨` 항목에 접속 주소를 추가한 뒤 다시 실행하세요.

## API 키 처리

키는 두 경로로 받으며, 사이드바 입력이 우선입니다.

1. 사이드바의 `OPENAI API 키` 입력란 (교재 방식)
2. Streamlit Secrets 의 `OPENAI_API_KEY`

Secrets 값을 입력란의 기본값(`value=`)으로 채우지 않고 API 호출 시점에만 읽습니다.
`type="password"` 로 마스킹하더라도 `value=` 에 넣은 값은 브라우저까지 전달되기 때문에,
공개 URL에서 키가 노출되는 것을 막기 위한 처리입니다.

로컬에서 Secrets를 쓰려면 `.streamlit/secrets.toml` 을 만들고 아래처럼 적습니다
(이 파일은 `.gitignore` 에 등록되어 있어 커밋되지 않습니다).

```toml
OPENAI_API_KEY = "sk-..."
```

## 교재와 다른 부분

교재는 2023년에 쓰였기 때문에 그대로 실행하면 동작하지 않거나 곧 동작하지 않게 되는
부분이 있어 다음 세 가지를 수정했습니다.

### 1. GPT 모델 교체 — `gpt-4`, `gpt-3.5-turbo` → `gpt-4o`, `gpt-4o-mini`

교재가 사용하는 두 모델은 **2026년 10월 23일 OpenAI API에서 서비스가 종료**됩니다
([OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)).
호출 코드와 파라미터는 교재와 동일하고 모델 문자열만 바꿨습니다.
STT에 쓰는 `whisper-1` 은 종료 대상이 아니라 교재 그대로 두었습니다.

### 2. 초기화 버튼을 누르면 이후 녹음이 처리되지 않는 문제

교재 코드는 `초기화` 버튼을 누를 때 `st.session_state["check_reset"] = True` 로 바꾸지만,
이 값을 다시 `False` 로 되돌리는 지점이 없습니다. 녹음 처리 조건이
`check_reset == False` 이므로, 초기화를 한 번 누르면 그 뒤로는 녹음을 해도 아무 반응이
없습니다. 처리 블록의 `else` 분기에서 플래그를 `False` 로 되돌리도록 했습니다.

### 3. GPT 답변을 `role: "system"` 으로 저장하던 문제

교재는 GPT의 답변을 `{"role": "system", "content": response}` 로 대화 기록에 넣습니다.
`system` 은 모델에게 내리는 지시문의 역할이므로, 대화가 길어질수록 답변 하나하나가
새로운 지시문으로 쌓여 모델의 동작이 흐트러집니다. 실제 역할에 맞게 `assistant` 로
저장하도록 고쳤습니다.

### 그 밖에

- 교재는 `pip freeze > requirements.txt` 를 안내하지만, 그러면 개발 환경에만 필요한
  패키지와 OS 종속적인 버전까지 모두 포함되어 배포 서버에서 설치가 실패하기 쉽습니다.
  실제로 필요한 패키지만 버전을 고정해 직접 작성했습니다.
- API 키가 비어 있는 상태로 녹음하면 OpenAI 호출에서 예외가 발생하며 화면에
  스택 트레이스가 그대로 노출되므로, 안내 메시지를 띄우고 멈추도록 했습니다.

## 주의: 파이썬 버전

녹음 위젯(`streamlit-audiorecorder`)은 `pydub` 에 의존하고, `pydub` 은 표준 라이브러리
`audioop` 을 사용합니다. **`audioop` 은 파이썬 3.13에서 제거**되었기 때문에 3.13 환경에서는
`import` 단계에서 실패합니다. 로컬과 배포 모두 **파이썬 3.12** 를 사용해야 합니다.
(Streamlit Cloud 는 앱 배포 시 `Advanced settings` 에서 Python 버전을 지정합니다.)

## 배포

GitHub 리포지토리를 Streamlit Community Cloud 에 연결해 배포했습니다.

- 리포지토리: https://github.com/mimm-112/voicebot
- 배포 주소: *(배포 후 기재)*
