import streamlit as st
from ollama import chat
import subprocess, json, os

# ─── Constants & Helpers ──────────────────────────────────────────────────────
HISTORY_FILE = "chat_history.json"
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []
def save_history(h):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, indent=2)
def get_ollama_models():
    try:
        out = subprocess.run(["ollama","list"], capture_output=True, text=True, check=True).stdout
        return [ln.split()[0] for ln in out.splitlines()[1:]]
    except:
        st.sidebar.error("Could not list Ollama models.")
        return []

# ─── Init session_state ──────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_idx" not in st.session_state:
    st.session_state.current_idx = None  # None=new chat, else index
if "to_stream" not in st.session_state:
    st.session_state.to_stream = None   # stores the prompt batch
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False

st.set_page_config(page_title="Ollama Chat", layout="wide")

# ─── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Settings")

models = get_ollama_models()
if not models:
    st.sidebar.stop()
selected_model = st.sidebar.selectbox("Model", models)

# New Chat
if st.sidebar.button("🆕 New Chat"):
    st.session_state.messages = []
    st.session_state.current_idx = None
    st.session_state.to_stream = None
    st.session_state.stop_requested = False
    st.rerun()

# Chat History
st.sidebar.markdown("### 📜 Chat History")
for rev_i, chat_obj in enumerate(st.session_state.chat_history[::-1]):
    orig_i = len(st.session_state.chat_history) - 1 - rev_i
    name = chat_obj.get("name", f"Chat {orig_i+1}")
    c1, c2 = st.sidebar.columns([4,1])
    with c1:
        if st.sidebar.button(name, key=f"load_{orig_i}"):
            st.session_state.messages = chat_obj["messages"].copy()
            st.session_state.current_idx = orig_i
            st.session_state.to_stream = None
            st.session_state.stop_requested = False
            st.rerun()
    with c2:
        if st.sidebar.button("🗑️", key=f"del_{orig_i}"):
            st.session_state.chat_history.pop(orig_i)
            save_history(st.session_state.chat_history)
            st.session_state.messages = []
            st.session_state.current_idx = None
            st.session_state.to_stream = None
            st.rerun()
if not st.session_state.chat_history:
    st.sidebar.info("No chats yet.")

# ─── Main Chat Window ─────────────────────────────────────────────────────────
st.title("💬 Chat with Ollama")

# Display past messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ─── Step 1: Capture input and queue for streaming ────────────────────────────
if st.session_state.to_stream is None:
    user_input = st.chat_input("Type your message here…")
    if user_input:
        # show user immediately
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role":"user","content":user_input})
        # queue up for streaming and rerun
        st.session_state.to_stream = {
            "model": selected_model,
            "messages": st.session_state.messages.copy()
        }
        st.session_state.stop_requested = False
        st.rerun()

# ─── Step 2: Stream response with Stop button ─────────────────────────────────
else:
    st.info("🧠 Generating…")

    full = ""
    container = st.chat_message("assistant")
    with container:
        placeholder = st.empty()
        for chunk in chat(
            model=st.session_state.to_stream["model"],
            messages=st.session_state.to_stream["messages"],
            stream=True
        ):
            if st.session_state.stop_requested:
                placeholder.markdown(full + "\n\n*⏹️ Generation stopped.*")
                break
            delta = chunk["message"]["content"]
            full += delta
            placeholder.markdown(full)

    # append assistant message
    st.session_state.messages.append({"role":"assistant","content":full})

    # save or update history
    first_user = next((m["content"] for m in st.session_state.messages if m["role"]=="user"), "Chat")
    title = first_user.split("\n")[0][:40]
    if st.session_state.current_idx is None:
        existing = [c["messages"] for c in st.session_state.chat_history]
        if st.session_state.messages not in existing:
            st.session_state.chat_history.append({
                "name": title,
                "messages": st.session_state.messages.copy()
            })
            st.session_state.current_idx = len(st.session_state.chat_history)-1
    else:
        st.session_state.chat_history[st.session_state.current_idx]["messages"] = st.session_state.messages.copy()

    save_history(st.session_state.chat_history)

    # clear queue
    st.session_state.to_stream = None
    st.session_state.stop_requested = False
