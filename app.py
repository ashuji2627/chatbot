import streamlit as st 
from chat_engine import query_ollama
from db import init_db, insert_message, get_messages, delete_session, get_all_sessions
from prompt_generator import generate_contextual_prompt
import uuid
import time
from datetime import datetime

from logger import get_logger
logger = get_logger()

# ---- CONFIG ----
st.set_page_config(page_title="Chatbot", layout="centered")
init_db()

# ---- CUSTOM CSS ----
st.markdown("""
<style>
[data-baseweb="radio"] > div {
    border-bottom: 1px solid #ccc;
    padding: 8px 10px;
    transition: all 0.2s ease-in-out;
    cursor: pointer;
}
[data-baseweb="radio"] > div:hover {
    background-color: #f0f0f5;
}
[data-baseweb="radio"] > div[data-selected="true"] {
    background-color: #dceeff;
    border-left: 4px solid #0066cc;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ---- UTILITY ----
def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---- SESSION INIT ----
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    logger.info(f"New chat session started: {st.session_state.session_id}")

# ---- FETCH SESSION OPTIONS ----
def refresh_sidebar_sessions():
    session_options = get_all_sessions()
    session_ids = list(session_options.keys())
    session_display_names = ["New Chat"] + [session_options[sid] for sid in session_ids]
    session_ids = [None] + session_ids
    return session_display_names, session_ids

session_display_names, session_ids = refresh_sidebar_sessions()

# ---- SIDEBAR ----
st.sidebar.title("Chat History")
selected_index = st.sidebar.radio(
    "Choose a chat session",
    options=list(range(len(session_display_names))),
    format_func=lambda i: session_display_names[i],
    key="session_selector"
)

# ---- HANDLE SESSION SELECTION ----
if selected_index == 0:
    st.session_state.session_id = str(uuid.uuid4())
    logger.info(f"New session selected (New Chat): {st.session_state.session_id}")
else:
    st.session_state.session_id = session_ids[selected_index]
    logger.info(f"Existing session selected: {st.session_state.session_id}")

# ---- DELETE SESSION ----
if st.sidebar.button("Delete This Chat"):
    delete_session(st.session_state.session_id)
    logger.warning(f"Deleted session: {st.session_state.session_id}")
    st.success("Deleted successfully!")
    st.rerun()

# ---- FETCH MESSAGES ----
messages = get_messages(st.session_state.session_id)
logger.debug(f"Loaded messages for session: {st.session_state.session_id}, count: {len(messages)}")

# ---- TITLE ----
if messages:
    title_text = messages[0]["content"][:40] + "..." if len(messages[0]["content"]) > 40 else messages[0]["content"]
    st.title(title_text)
else:
    st.title("Chatbot")
    st.info("Start a conversation to begin a new chat.")

# ---- TYPING + SPINNER ANIMATION ----
def show_typing_then_spinner(total_seconds=20):
    typing = st.empty()
    phrases = [
        "🤖 Booting up AI circuits...",
        "🧠 Thinking really hard...",
        "📚 Recalling every word ever written...",
        "🔍 Searching the depths of data...",
        "💡 Brewing up a clever reply...",
        "⌛ Almost there, stay tuned...",
    ]
    start_time = time.time()
    index = 0
    while time.time() - start_time < 10:
        dots = "." * (index % 4)
        typing.markdown(f"💬 Assistant is typing{dots}")
        time.sleep(4)
        index += 1
    phrase_index = 0
    while time.time() - start_time < total_seconds - 10:
        typing.info(phrases[phrase_index % len(phrases)])
        time.sleep(2)
        phrase_index += 1
    typing.empty()

# ---- CHAT HISTORY DISPLAY ----
with st.container():
    st.markdown('<div class="chat-history">', unsafe_allow_html=True)
    for i, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if (
                msg["role"] == "assistant" and
                i == len(messages) - 1 and
                len(messages) >= 2 and
                messages[-2]["role"] == "user"
            ):
                if st.button("🔄 Regenerate", key="regenerate_btn"):
                    from db import delete_last_assistant_message
                    delete_last_assistant_message(st.session_state.session_id)
                    logger.info(f"Regenerating assistant message for session: {st.session_state.session_id}")

                    last_user_prompt = messages[-2]["content"]
                    contextual_prompt = generate_contextual_prompt(st.session_state.session_id, last_user_prompt)
                    history = get_messages(st.session_state.session_id)
                    history[-1]['content'] = contextual_prompt

                    with st.expander("Prompt Sent to Model"):
                        st.code(contextual_prompt, language="markdown")

                    with st.chat_message("assistant"):
                        placeholder = st.empty()
                        with placeholder.container():
                            with st.spinner("🤖 Regenerating response..."):
                                show_typing_then_spinner(total_seconds=10)
                                st.info(f"Query sent to Ollama model at {get_time()}")
                                response = query_ollama(history)
                                st.info(f"Response received at {get_time()}")
                        placeholder.empty()
                        st.markdown(response)
                        insert_message(st.session_state.session_id, "assistant", response)
                        logger.info(f"Regenerated response stored in session {st.session_state.session_id}")
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---- SCROLL TO BOTTOM ----
if st.button("⬇ Scroll to Bottom"):
    st.rerun()

# ---- CHAT INPUT ----
prompt = st.chat_input("Ask something...")

if prompt:
    insert_message(st.session_state.session_id, "user", prompt)
    logger.info(f"User prompt in session {st.session_state.session_id}: {prompt}")

    with st.chat_message("user"):
        st.markdown(prompt)

    # Acknowledgement with timestamps
    st.info(f"Code sent to server at {get_time()}")

    contextual_prompt = generate_contextual_prompt(st.session_state.session_id, prompt)
    st.info(f"Contextual prompt generated at {get_time()}")

    history = get_messages(st.session_state.session_id)
    history[-1]['content'] = contextual_prompt



    # Show prompt that will be sent to the model
    with st.expander("Prompt Sent to Model"):
        st.code(contextual_prompt, language="markdown")

    with st.chat_message("assistant"):
        placeholder = st.empty()
        with placeholder.container():
            with st.spinner("🤖 Generating response..."):
                show_typing_then_spinner(total_seconds=10)
                st.info(f"Query sent to Ollama model at {get_time()}")
                response = query_ollama(history)
                st.info(f"Response received at {get_time()}")
        placeholder.empty()
        st.markdown(response)

    insert_message(st.session_state.session_id, "assistant", response)
    logger.info(f"Assistant response in session {st.session_state.session_id}: {response[:100]}...")

    st.markdown("""
        <script>
        const chatBox = window.parent.document.querySelectorAll('.chat-history')[0];
        if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
        </script>
    """, unsafe_allow_html=True)
