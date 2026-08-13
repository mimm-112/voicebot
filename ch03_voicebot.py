##### 패키지 추가 #####
import streamlit as st
# audiorecorder 패키지 추가
from audiorecorder import audiorecorder
# OpenAI 패키지 추가
import openai
# 파일 삭제를 위한 패키지 추가
import os
# 시간 정보를 위한 패키지 추가
from datetime import datetime
# TTS 패키지 추가
from gtts import gTTS
# 음원 파일을 재생하기 위한 패키지 추가
import base64

# GPT 모델 선택지
# 교재는 gpt-4 / gpt-3.5-turbo 를 사용하지만 두 모델 모두 2026-10-23 자로
# OpenAI에서 서비스가 종료되므로 현행 모델로 교체했다.
GPT_MODELS = ["gpt-4o", "gpt-4o-mini"]

# 시스템 프롬프트 (교재와 동일)
SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a thoughtful assistant. Respond to all input in 25 words and answer in korea",
}


##### 기능 구현 함수 #####
def get_api_key():
    """사용할 OpenAI API 키를 결정한다.

    사이드바에 직접 입력한 키를 우선 사용하고, 비어 있으면 Streamlit Secrets에
    저장해 둔 키를 사용한다. Secrets 값을 text_input의 value로 넣으면 마스킹이
    되더라도 실제 키가 브라우저까지 전달되므로, 호출 시점에만 읽어서 쓴다.
    """
    if st.session_state["OPENAI_API"]:
        return st.session_state["OPENAI_API"]
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        # secrets.toml 이 없는 로컬 환경에서는 st.secrets 접근 자체가 예외를 낸다.
        return ""


def STT(audio, apikey):
    # 파일 저장
    filename = "input.mp3"
    audio.export(filename, format="mp3")

    # 음원 파일 열기
    audio_file = open(filename, "rb")
    # Whisper 모델을 활용해 텍스트 얻기
    client = openai.OpenAI(api_key=apikey)
    respons = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    audio_file.close()
    # 파일 삭제
    os.remove(filename)
    return respons.text


def ask_gpt(prompt, model, apikey):
    client = openai.OpenAI(api_key=apikey)
    response = client.chat.completions.create(model=model, messages=prompt)
    gptResponse = response.choices[0].message.content
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
            - STT(Speech-To-Text)는 OpenAI의 Whisper AI를 활용하였습니다.
            - 답변은 OpenAI의 GPT 모델을 활용하였습니다.
            - TTS(Text-To-Speech)는 구글의 Google Translate TTS를 활용하였습니다.
            """
        )
        st.markdown("")

    # session state 초기화
    if "chat" not in st.session_state:
        st.session_state["chat"] = []

    if "OPENAI_API" not in st.session_state:
        st.session_state["OPENAI_API"] = ""

    if "messages" not in st.session_state:
        st.session_state["messages"] = [SYSTEM_PROMPT]

    if "check_reset" not in st.session_state:
        st.session_state["check_reset"] = False

    # 사이드바 생성
    with st.sidebar:
        # Open AI API 키 입력받기
        st.session_state["OPENAI_API"] = st.text_input(
            label="OPENAI API 키",
            placeholder="Enter Your API Key",
            value="",
            type="password",
        )

        st.markdown("---")

        # GPT 모델을 선택하기 위한 라디오 버튼 생성
        model = st.radio(label="GPT 모델", options=GPT_MODELS)

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
        # 음성 녹음 아이콘 추가
        audio = audiorecorder("클릭하여 녹음하기", "녹음 중...")
        if (audio.duration_seconds > 0) and (st.session_state["check_reset"] == False):
            # 음성 재생
            st.audio(audio.export().read())

            apikey = get_api_key()
            if not apikey:
                st.error("사이드바에 OPENAI API 키를 입력해 주세요.")
                st.stop()

            # 음원 파일에서 텍스트 추출
            question = STT(audio, apikey)

            # 채팅을 시각화하기 위해 질문 내용 저장
            now = datetime.now().strftime("%H:%M")
            st.session_state["chat"] = st.session_state["chat"] + [
                ("user", now, question)
            ]
            # GPT 모델에 넣기 위해 질문 내용 저장
            st.session_state["messages"] = st.session_state["messages"] + [
                {"role": "user", "content": question}
            ]

    with col2:
        # 오른쪽 영역 작성
        st.subheader("질문/답변")
        if (audio.duration_seconds > 0) and (st.session_state["check_reset"] == False):
            # ChatGPT에게 답변 얻기
            response = ask_gpt(st.session_state["messages"], model, get_api_key())

            # GPT 모델에 넣을 프롬프트를 위해 답변 내용 저장
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
