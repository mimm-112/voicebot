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

# 시스템 프롬프트 (교재와 동일)
SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a thoughtful assistant. Respond to all input in 25 words and answer in korea",
}


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


##### 메인 함수 #####
def main():
    # 기본 설정
    st.set_page_config(page_title="음성 비서 프로그램", layout="wide")

    # 제목
    st.header("음성 비서 프로그램")

    # 구분선
    st.markdown("---")

    # 기본 설명
    with st.expander("음성비서 프로그램에 관하여", expanded=True):
        st.write(
            """
            - 음성비서 프로그램의 UI는 스트림릿을 활용하여 만들었습니다.
            - STT(Speech-To-Text)는 구글의 Gemini를 활용하였습니다.
            - 답변은 구글의 Gemini 모델을 활용하였습니다.
            - TTS(Text-To-Speech)는 구글의 Google Translate TTS를 활용하였습니다.
            """
        )
        st.markdown("")

    # session state 초기화
    if "chat" not in st.session_state:
        st.session_state["chat"] = []

    if "GOOGLE_API" not in st.session_state:
        st.session_state["GOOGLE_API"] = ""

    if "messages" not in st.session_state:
        st.session_state["messages"] = [SYSTEM_PROMPT]

    if "check_reset" not in st.session_state:
        st.session_state["check_reset"] = False

    # 사이드바 생성
    with st.sidebar:
        # Gemini API 키 입력받기
        st.session_state["GOOGLE_API"] = st.text_input(
            label="GEMINI API 키",
            placeholder="Enter Your API Key",
            value="",
            type="password",
        )

        st.markdown("---")

        # Gemini 모델을 선택하기 위한 라디오 버튼 생성
        model = st.radio(label="GEMINI 모델", options=GEMINI_MODELS)

        st.markdown("---")

        # 리셋 버튼 생성
        if st.button(label="초기화"):
            # 리셋 코드
            st.session_state["chat"] = []
            st.session_state["messages"] = [SYSTEM_PROMPT]
            st.session_state["check_reset"] = True

    # 기능 구현 공간
    col1, col2 = st.columns(2)
    with col1:
        # 왼쪽 영역 작성
        st.subheader("질문하기")
        # 음성 녹음 (스트림릿 내장 위젯 — 녹음과 재생을 함께 제공한다)
        audio = st.audio_input("클릭하여 녹음하기")
        if (audio is not None) and (st.session_state["check_reset"] == False):
            apikey = get_api_key()
            if not apikey:
                st.error("사이드바에 GEMINI API 키를 입력해 주세요.")
                st.stop()

            # 음원 파일에서 텍스트 추출
            question = STT(audio, apikey)

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
        # 오른쪽 영역 작성
        st.subheader("질문/답변")
        if (audio is not None) and (st.session_state["check_reset"] == False):
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

            # 채팅 형식으로 시각화하기
            for sender, time, message in st.session_state["chat"]:
                if sender == "user":
                    st.write(
                        f'<div style="display:flex;align-items:center;">'
                        f'<div style="background-color:#007AFF;color:white;border-radius:12px;padding:8px 12px;margin-right:8px;">{message}</div>'
                        f'<div style="font-size:0.8rem;color:gray;">{time}</div></div>',
                        unsafe_allow_html=True,
                    )
                    st.write("")
                else:
                    st.write(
                        f'<div style="display:flex;align-items:center;justify-content:flex-end;">'
                        f'<div style="background-color:lightgray;border-radius:12px;padding:8px 12px;margin-left:8px;">{message}</div>'
                        f'<div style="font-size:0.8rem;color:gray;">{time}</div></div>',
                        unsafe_allow_html=True,
                    )
                    st.write("")

            # gTTS를 활용하여 음성 파일 생성 및 재생
            TTS(response)
        else:
            # 초기화 직후에는 위 블록을 건너뛰므로 여기서 플래그를 되돌린다.
            # 교재 코드에는 check_reset을 False로 되돌리는 지점이 없어서
            # 초기화를 한 번 누르면 이후 녹음이 영영 처리되지 않는다.
            st.session_state["check_reset"] = False


if __name__ == "__main__":
    main()
