from langchain_openai import ChatOpenAI
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import RedisChatMessageHistory
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import secrets
import time

with st.spinner(_cache=True):
    @st.cache_resource(experimental_allow_widgets=True)
    def get_manager():
        return stx.CookieManager()

    cookie_manager = get_manager()
    time.sleep(1)


def get_session_history(session_id) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(
        session_id, url=st.secrets["REDIS_URL"]
    )


def generate_response(input):
    response = chain_with_history.stream({"input": input}, config=config)
    for chunk in response:
        yield chunk


def set_seesion_id():
    current_date = datetime.now().strftime('%Y%m%d')
    random_token = secrets.token_hex(16)
    # 以日期和隨機亂碼作為 session_id
    token_with_date = f"{current_date}_{random_token}"
    cookie_manager.set("session_id", token_with_date,
                       expires_at=datetime.now() + timedelta(days=365))


# 使用此 APP 需輸入開發者設定的 KEY
joanne_app_key = st.sidebar.text_input('密碼(請聯絡開發者)', type='password')

if (joanne_app_key != st.secrets["JOANNE_APP_KEY"]):
    st.warning('輸入錯誤! 請聯絡開發者~')
    st.stop()

else:
    st.success('成功! 可以開始聊天~')
    if not cookie_manager.get("session_id"):
        set_seesion_id()

    selected_llm_model = st.sidebar.selectbox(
        "選擇模型", ["gpt-3.5-turbo", "gpt-4-turbo"])

    # === 設定Langchain 架構 ===
    llm = ChatOpenAI(model=selected_llm_model,
                     api_key=st.secrets["OPENAI_API_KEY"])
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You're an assistant。"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )
    chain = prompt | llm
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
    config = {"configurable": {"session_id": cookie_manager.get("session_id")}}

    # === 頁面顯示設定 ===
    st.title("Joanne-GPT")
    st.subheader("盡情地聊天吧!")

    if clear_chat_button := st.button("清除聊天以建立新聊天"):
        cookie_manager.delete(cookie="session_id")
        # 刪除該 session_id 的聊天紀錄
        get_session_history(cookie_manager.get("session_id")).clear()
        # 建立新session_id
        set_seesion_id()

    # 呈現聊天紀錄
    for message in get_session_history(cookie_manager.get("session_id")).messages:
        message = dict(message)
        if "AI" in message["type"]:
            with st.chat_message("assistant"):
                st.markdown(message["content"])
        else:
            with st.chat_message("user"):
                st.markdown(message["content"])

    if prompt := st.chat_input("輸入問題..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            st.write_stream(generate_response(prompt))
