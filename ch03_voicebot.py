##### 패키지 추가 #####
import streamlit as st
# Gemini 패키지 추가
from google import genai
from google.genai import types
# 파일 삭제를 위한 패키지 추가
import os
# 시간 정보를 위한 패키지 추가
from datetime import datetime
# TTS 패키지 추가
from gtts import gTTS
# 음원 파일을 재생하기 위한 패키지 추가
import base64

# 답변에 사용할 Gemini 모델 선택지.
# 교재가 gpt-4(고성능) / gpt-3.5-turbo(경량) 중에서 고르게 한 것과 같은 구성이다.
# 둘 다 무료 티어에서 사용할 수 있다. (pro 계열은 무료 티어 대상이 아니다)
GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]

# 음성을 텍스트로 바꿀 때 사용할 모델
STT_MODEL = "gemini-3.6-flash"

# 시스템 프롬프트. 교재의 프롬프트에 자비스 컨셉의 말투 지시를 덧붙였다.
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are JARVIS, the AI butler from Iron Man. "
        "Respond to all input in 25 words and answer in korea. "
        "사용자를 '보스'라고 부르고, 정중하지만 위트 있는 집사 말투를 사용하세요."
    ),
}


##### 화면 꾸미기 #####
# 아이언맨 자비스 컨셉의 스타일. 스트림릿 내부 클래스명은 버전에 따라 바뀔 수 있어서
# 직접 만든 요소(jv-*)를 중심으로 스타일을 지정했다.
JARVIS_CSS = """
<style>
/* 밝은 바탕에 맞춘 색. 어두운 화면은 분위기는 좋지만 오래 보기 피로하고
   회색 글씨의 대비가 낮아진다. 배경을 밝히고 글자색을 진하게 잡아
   본문 대비를 충분히 확보했다. */
.stApp {
    background:
        radial-gradient(ellipse 80% 45% at 50% 0%, rgba(0,150,200,0.10), transparent 70%),
        radial-gradient(ellipse 55% 40% at 95% 100%, rgba(230,150,0,0.07), transparent 70%),
        #F5F9FC;
}
/* 아크 리액터는 스스로 빛나는 물체이므로 밝은 바탕에서도 그대로 살린다. */
@keyframes jvPulse {
    0%, 100% { box-shadow: 0 0 10px rgba(0,180,220,.75), 0 0 24px rgba(0,180,220,.35); }
    50%      { box-shadow: 0 0 18px rgba(0,180,220,.95), 0 0 42px rgba(0,180,220,.5); }
}

.jv-head { display:flex; align-items:center; gap:20px; padding:10px 0 4px 0; }
.jv-reactor {
    width:52px; height:52px; border-radius:50%; flex:none;
    background: radial-gradient(circle, #FFFFFF 0%, #9BEEFF 30%, #00A6CC 62%, #016C88 100%);
    animation: jvPulse 2.4s ease-in-out infinite;
}
/* 스트림릿이 마크다운 안의 글자 크기를 자체 규칙으로 덮어쓰기 때문에
   제목처럼 크기가 중요한 요소에는 !important 를 붙였다. */
.jv-title {
    font-size:3rem !important; font-weight:800 !important; letter-spacing:.04em;
    line-height:1.15 !important; margin:0 !important;
    color:#0C3D52; text-shadow: 0 2px 10px rgba(0,150,190,.35), 0 0 2px rgba(0,150,190,.4);
}
.jv-title .jv-oh { color:#D98A00; text-shadow: 0 2px 10px rgba(217,138,0,.35), 0 0 2px rgba(217,138,0,.45); }
.jv-sub { margin:6px 0 0 0 !important; font-size:.74rem !important; letter-spacing:.28em;
    color:#3E7A92; text-transform:uppercase; }

.jv-status { display:flex; gap:14px; flex-wrap:wrap; margin:10px 0 2px 0; font-size:.82rem; letter-spacing:.06em; }
.jv-status span { border:1px solid rgba(0,150,190,.35); border-radius:999px; padding:4px 14px;
    background:#FFFFFF; color:#0F5A73; box-shadow:0 1px 3px rgba(10,60,80,.07); }

.jv-rule { height:2px; border:0; margin:14px 0 18px 0;
    background:linear-gradient(90deg, transparent, rgba(0,150,190,.5), rgba(217,138,0,.35), transparent); }

.jv-panel { border:1px solid rgba(0,150,190,.25); border-left:4px solid #00A6CC; border-radius:8px;
    background:#FFFFFF; padding:16px 20px; margin-bottom:6px; box-shadow:0 1px 4px rgba(10,60,80,.06); }
.jv-panel ul { margin:0; padding-left:18px; color:#22485C; font-size:.96rem; line-height:1.9; }
.jv-panel b { color:#B06E00; font-weight:700; }

/* 대화 말풍선 */
.jv-row { display:flex; align-items:flex-end; gap:8px; margin-bottom:12px; }
.jv-row.me { justify-content:flex-end; }
.jv-row.ai { justify-content:flex-start; }
/* 말풍선 묶음이 남는 가로 공간을 다 차지하지 않도록 내용 크기에 맞춘다.
   이렇게 해야 시각 표시가 말풍선 바로 옆에 붙는다. */
.jv-msg { max-width:78%; min-width:0; flex:0 1 auto; }
.jv-bubble { padding:11px 16px; border-radius:14px; font-size:1rem; line-height:1.65;
    word-break:break-word; box-shadow:0 1px 4px rgba(10,60,80,.08); }
.jv-row.me .jv-bubble {
    background:#DFF4FB; border:1px solid #7FCBE3; color:#0B3D51; border-bottom-right-radius:4px; }
.jv-row.ai .jv-bubble {
    background:#FFF6E3; border:1px solid #E8C173; color:#4A3208; border-bottom-left-radius:4px; }
.jv-time { font-size:.74rem; color:#5D7C8A; flex:none; padding-bottom:3px; }
.jv-who { font-size:.72rem; letter-spacing:.12em; margin-bottom:3px; font-weight:600; }
.jv-row.me .jv-who { color:#0F6E8C; text-align:right; }
.jv-row.ai .jv-who { color:#A9700A; }

.jv-idle { border:2px dashed rgba(0,150,190,.3); border-radius:10px; padding:28px 18px;
    text-align:center; color:#3F6B7D; font-size:.95rem; letter-spacing:.04em; background:#FBFDFE; }
</style>
"""


def render_header(model, turns):
    """자비스 컨셉의 제목과 상태 표시줄을 그린다.

    상태 표시줄에는 실제 세션 값(선택한 모델, 지금까지의 대화 횟수)을 보여준다.
    값을 인자로 받기 때문에 화면에 보이는 내용과 실제 상태가 어긋나지 않는다.
    """
    st.markdown(JARVIS_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="jv-head">
            <div class="jv-reactor"></div>
            <div>
                <div class="jv-title">🦾 자비스<span class="jv-oh">OHYEAH</span></div>
                <div class="jv-sub">Just A Rather Very Intelligent System</div>
            </div>
        </div>
        <div class="jv-status">
            <span>🧠 {model}</span>
            <span>💬 대화 {turns}턴</span>
        </div>
        <hr class="jv-rule">
        """,
        unsafe_allow_html=True,
    )


def render_bubble(sender, time, message):
    """대화 한 줄을 말풍선으로 그린다."""
    if sender == "user":
        st.markdown(
            f'<div class="jv-row me">'
            f'<div class="jv-time">{time}</div>'
            f'<div class="jv-msg"><div class="jv-who">보스</div>'
            f'<div class="jv-bubble">{message}</div></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="jv-row ai">'
            f'<div class="jv-msg"><div class="jv-who">🦾 자비스</div>'
            f'<div class="jv-bubble">{message}</div></div>'
            f'<div class="jv-time">{time}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


##### 기능 구현 함수 #####
def get_api_key():
    """사용할 Gemini API 키를 결정한다.

    사이드바에 직접 입력한 키를 우선 사용하고, 비어 있으면 Streamlit Secrets에
    저장해 둔 키를 사용한다. Secrets 값을 text_input의 value로 넣으면 마스킹이
    되더라도 실제 키가 브라우저까지 전달되므로, 호출 시점에만 읽어서 쓴다.
    """
    if st.session_state["GOOGLE_API"]:
        return st.session_state["GOOGLE_API"]
    try:
        return st.secrets.get("GOOGLE_API_KEY", "")
    except Exception:
        # secrets.toml 이 없는 로컬 환경에서는 st.secrets 접근 자체가 예외를 낸다.
        return ""


def to_gemini_contents(messages):
    """교재 형식의 대화 기록을 Gemini가 받는 형식으로 변환한다.

    교재는 대화를 [{"role": "user"/"assistant", "content": "..."}] 형태로
    쌓는다. 이 구조를 그대로 유지하고 API를 호출하기 직전에만 변환하기 때문에,
    화면 표시나 초기화 로직은 교재 코드와 똑같이 둘 수 있다.

    Gemini는 답변자의 역할을 "assistant"가 아니라 "model"이라고 부르고,
    시스템 프롬프트는 대화 기록이 아니라 별도 설정으로 전달한다.
    """
    contents = []
    for message in messages:
        if message["role"] == "system":
            continue
        role = "model" if message["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=message["content"])])
        )
    return contents


def STT(audio, apikey):
    # 녹음된 음원을 바이트 형식으로 읽기
    audio_bytes = audio.getvalue()

    # Gemini에 음원을 그대로 넘겨 텍스트 얻기
    client = genai.Client(api_key=apikey)
    respons = client.models.generate_content(
        model=STT_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            types.Part.from_text(
                text="이 음성을 받아쓰기 해주세요. 다른 설명 없이 말한 내용만 그대로 출력하세요."
            ),
        ],
    )
    return respons.text.strip()


def ask_gemini(prompt, model, apikey):
    client = genai.Client(api_key=apikey)
    response = client.models.generate_content(
        model=model,
        contents=to_gemini_contents(prompt),
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT["content"]),
    )
    gptResponse = response.text
    return gptResponse


def TTS(response):
    # gTTS를 활용하여 음성 파일 생성
    filename = "output.mp3"
    tts = gTTS(text=response, lang="ko")
    tts.save(filename)

    # 음원 파일 자동 재생
    with open(filename, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="True">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
    # 파일 삭제
    os.remove(filename)


def reset_chat():
    """대화 기록을 지우고 녹음 위젯도 비운다.

    교재는 check_reset 이라는 깃발 하나로 초기화를 처리하지만, 녹음 위젯에는
    직전 녹음이 그대로 남아 있기 때문에 다음 화면 갱신 때 같은 질문이 다시
    처리되는 문제가 있다. 위젯 key 에 붙는 번호를 올려서 녹음 위젯 자체를
    새로 만드는 방식으로 바꿨다.
    """
    st.session_state["chat"] = []
    st.session_state["messages"] = [SYSTEM_PROMPT]
    st.session_state["last_audio"] = None
    st.session_state["rec_key"] += 1


##### 메인 함수 #####
def main():
    # 기본 설정
    st.set_page_config(page_title="자비스OHYEAH", page_icon="🦾", layout="wide")

    # session state 초기화
    if "chat" not in st.session_state:
        st.session_state["chat"] = []

    if "GOOGLE_API" not in st.session_state:
        st.session_state["GOOGLE_API"] = ""

    if "messages" not in st.session_state:
        st.session_state["messages"] = [SYSTEM_PROMPT]

    if "model" not in st.session_state:
        st.session_state["model"] = GEMINI_MODELS[0]

    # 이미 처리한 녹음인지 구분하기 위한 값
    if "last_audio" not in st.session_state:
        st.session_state["last_audio"] = None

    # 녹음 위젯을 새로 만들기 위한 번호
    if "rec_key" not in st.session_state:
        st.session_state["rec_key"] = 0

    # 제목과 상태 표시줄 (실제 세션 값을 그대로 표시한다)
    render_header(
        model=st.session_state["model"],
        turns=len([c for c in st.session_state["chat"] if c[0] == "user"]),
    )

    # 기본 설명
    with st.expander("📋 SYSTEM BRIEFING", expanded=True):
        st.markdown(
            """
            <div class="jv-panel">
                <ul>
                    <li>인터페이스는 <b>스트림릿</b>으로 구축하였습니다.</li>
                    <li>음성 인식(STT)은 구글의 <b>Gemini</b>를 활용하였습니다.</li>
                    <li>답변 생성은 구글의 <b>Gemini</b> 모델을 활용하였습니다.</li>
                    <li>음성 합성(TTS)은 구글의 <b>Google Translate TTS</b>를 활용하였습니다.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 사이드바 생성
    with st.sidebar:
        st.markdown(JARVIS_CSS, unsafe_allow_html=True)
        st.markdown("### ⚙️ 제어판")

        # Gemini API 키 입력받기.
        # key 를 지정하면 입력값이 곧바로 session_state 에 들어가므로,
        # 화면 위쪽의 상태 표시줄이 현재 입력 상태를 바로 반영할 수 있다.
        st.text_input(
            label="🔑 인증 키",
            placeholder="Enter Your API Key",
            type="password",
            key="GOOGLE_API",
        )

        st.markdown("---")

        # Gemini 모델을 선택하기 위한 라디오 버튼 생성
        model = st.radio(label="🧠 코어 모델", options=GEMINI_MODELS, key="model")

        st.markdown("---")

        # 리셋 버튼 생성
        st.button(
            label="🔄 기억 초기화",
            use_container_width=True,
            on_click=reset_chat,
        )

    # 기능 구현 공간
    col1, col2 = st.columns(2)
    with col1:
        # 왼쪽 영역 작성
        st.subheader("🎙️ 음성 명령")
        # 음성 녹음 (스트림릿 내장 위젯 — 녹음과 재생을 함께 제공한다)
        audio = st.audio_input(
            "마이크를 눌러 말씀하세요, 보스",
            key=f"rec_{st.session_state['rec_key']}",
        )

        # 방금 새로 녹음한 것일 때만 처리한다.
        # 이 확인이 없으면 모델을 바꾸는 등 다른 이유로 화면이 갱신될 때마다
        # 남아 있는 녹음이 다시 처리되어 같은 질문을 반복해서 보내게 된다.
        is_new = False
        if audio is not None:
            audio_id = hash(audio.getvalue())
            is_new = audio_id != st.session_state["last_audio"]

        if is_new:
            apikey = get_api_key()
            if not apikey:
                st.error("🔑 인증 키가 없습니다, 보스. 왼쪽 제어판에 키를 입력해 주세요.")
                is_new = False
            else:
                # 음원 파일에서 텍스트 추출
                question = STT(audio, apikey)
                st.session_state["last_audio"] = audio_id

                # 채팅을 시각화하기 위해 질문 내용 저장
                now = datetime.now().strftime("%H:%M")
                st.session_state["chat"] = st.session_state["chat"] + [
                    ("user", now, question)
                ]
                # Gemini 모델에 넣기 위해 질문 내용 저장
                st.session_state["messages"] = st.session_state["messages"] + [
                    {"role": "user", "content": question}
                ]

    with col2:
        # 오른쪽 영역 작성 — 제목 옆에 대화 초기화 버튼을 함께 둔다.
        head, btn = st.columns([2, 1])
        with head:
            st.subheader("💬 교신 기록")
        with btn:
            st.button(
                label="🗑️ 대화 초기화",
                use_container_width=True,
                on_click=reset_chat,
                disabled=not st.session_state["chat"],
            )

        response = None
        if is_new:
            # Gemini에게 답변 얻기
            response = ask_gemini(st.session_state["messages"], model, get_api_key())

            # 다음 질문에 이전 대화를 함께 넘기기 위해 답변 내용 저장
            # 교재는 role을 "system"으로 저장하지만, 그러면 대화가 이어질수록
            # 모델 지시문이 계속 쌓이는 꼴이 된다. 실제 역할대로 "assistant"로 저장한다.
            st.session_state["messages"] = st.session_state["messages"] + [
                {"role": "assistant", "content": response}
            ]

            # 채팅 시각화를 위한 답변 내용 저장
            now = datetime.now().strftime("%H:%M")
            st.session_state["chat"] = st.session_state["chat"] + [
                ("bot", now, response)
            ]

        # 채팅 형식으로 시각화하기.
        # 교재는 이 부분을 녹음 처리 블록 안에 두는데, 그러면 모델을 바꾸는 등
        # 다른 이유로 화면이 갱신될 때 대화 내용이 사라진다. 밖으로 꺼냈다.
        if st.session_state["chat"]:
            for sender, time, message in st.session_state["chat"]:
                render_bubble(sender, time, message)
        else:
            # 아직 대화가 없을 때 보여줄 안내
            st.markdown(
                '<div class="jv-idle">🦾 대기 중입니다, 보스.<br>'
                "왼쪽 마이크를 눌러 말을 걸어 주세요.</div>",
                unsafe_allow_html=True,
            )

        # gTTS를 활용하여 음성 파일 생성 및 재생
        if response is not None:
            TTS(response)


if __name__ == "__main__":
    main()
