import streamlit as st
from ollama import chat
import subprocess, json, os, time
from datetime import datetime

# ─── Constants & Helpers ──────────────────────────────────────────────────────
HISTORY_FILE = "chat_history.json"
SYSTEM_PROMPT_KEY = "system_prompt"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_history(h):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, indent=2, ensure_ascii=False)

def get_ollama_models():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        return [line.split()[0] for line in result.stdout.splitlines()[1:] if line.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ["llama3", "mistral"]  # Fallback models

def render_markdown_with_code(text):
    """Render text with proper code block formatting"""
    in_code_block = False
    code_lines = []
    output = []
    
    for line in text.split('\n'):
        if line.startswith('```'):
            if in_code_block:
                # End of code block
                code = '\n'.join(code_lines)
                language = code_lines[0].strip() if code_lines and code_lines[0] else ''
                if language and ' ' not in language:
                    code = '\n'.join(code_lines[1:])
                else:
                    language = ''
                output.append(f'```{language}\n{code}\n```')
                code_lines = []
                in_code_block = False
            else:
                # Start of code block
                in_code_block = True
                language = line[3:].strip()
                if language:
                    code_lines.append(language)
        elif in_code_block:
            code_lines.append(line)
        else:
            output.append(line)
            
    return '\n'.join(output)

# ─── Init session_state ──────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_idx" not in st.session_state:
    st.session_state.current_idx = None
if "to_stream" not in st.session_state:
    st.session_state.to_stream = None
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "system_prompt" not in st.session_state:
    st.session_state[SYSTEM_PROMPT_KEY] = "You are a helpful AI assistant."

st.set_page_config(
    page_title="Ollama Chat",
    layout="wide",
    page_icon="🤖"
)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Settings")

# Model selection with refresh
st.sidebar.subheader("Model Configuration")
model_col1, model_col2 = st.sidebar.columns([4, 1])
with model_col1:
    models = get_ollama_models()
    selected_model = st.selectbox("Select Model", models, index=0 if models else 0)
with model_col2:
    st.sidebar.write("")  # Vertical spacing
    if st.sidebar.button("🔄", help="Refresh model list"):
        models = get_ollama_models()
        st.rerun()

# System prompt
st.sidebar.subheader("System Prompt")
system_prompt = st.sidebar.text_area(
    "Instructions for the AI:",
    value=st.session_state[SYSTEM_PROMPT_KEY],
    height=150,
    label_visibility="collapsed"
)
if system_prompt != st.session_state[SYSTEM_PROMPT_KEY]:
    st.session_state[SYSTEM_PROMPT_KEY] = system_prompt

# Chat management
st.sidebar.subheader("Chat Management")
if st.sidebar.button("🆕 New Chat", use_container_width=True):
    st.session_state.messages = []
    st.session_state.current_idx = None
    st.session_state.to_stream = None
    st.session_state.stop_requested = False

# History management
st.sidebar.subheader("📜 Chat History")
if st.session_state.chat_history:
    if st.sidebar.button("🗑️ Clear All History", use_container_width=True):
        st.session_state.chat_history = []
        save_history(st.session_state.chat_history)
        st.session_state.messages = []
        st.session_state.current_idx = None
        st.rerun()

for rev_i, chat_obj in enumerate(st.session_state.chat_history[::-1]):
    orig_i = len(st.session_state.chat_history) - 1 - rev_i
    name = chat_obj.get(
        "name",
        f"Chat {orig_i+1} ({len(chat_obj['messages']) // 2} messages)"
    )

    timestamp = chat_obj.get("timestamp", "")
    
    with st.sidebar.expander(f"{name} {timestamp}"):
        if st.button("💬 Load", key=f"load_{orig_i}"):
            st.session_state.messages = chat_obj["messages"].copy()
            st.session_state.current_idx = orig_i
            st.session_state.to_stream = None
            st.session_state.stop_requested = False
            st.rerun()
        
        if st.button("🗑️ Delete", key=f"del_{orig_i}"):
            st.session_state.chat_history.pop(orig_i)
            save_history(st.session_state.chat_history)
            if st.session_state.current_idx == orig_i:
                st.session_state.messages = []
                st.session_state.current_idx = None
            st.rerun()
else:
    st.sidebar.info("No chat history yet.")

# ─── Main Chat Window ─────────────────────────────────────────────────────────
st.title("💬 Chat with Ollama")
st.caption(f"Using model: **{selected_model}**")

# Display messages with nicer formatting
for msg in st.session_state.messages:
    avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "assistant" and msg.get("formatted", False):
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# Autoscroll to bottom
st.markdown("<div id='bottom'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            window.scrollTo(0, document.body.scrollHeight);
        });
    </script>
    """, 
    unsafe_allow_html=True
)

# ─── Input and Streaming ─────────────────────────────────────────────────────
if st.session_state.to_stream is None:
    user_input = st.chat_input("Type your message here...")
    if user_input:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Prepare messages with system prompt
        messages_for_api = [{"role": "system", "content": st.session_state[SYSTEM_PROMPT_KEY]}]
        messages_for_api.extend(st.session_state.messages.copy())
        
        # Queue for streaming
        st.session_state.to_stream = {
            "model": selected_model,
            "messages": messages_for_api
        }
        st.session_state.stop_requested = False
        st.rerun()
else:
    # Display stop button during generation
    stop_col, spacer = st.columns([1, 5])
    with stop_col:
        if st.button("⏹️ Stop Generating"):
            st.session_state.stop_requested = True
            st.rerun()
    
    # Streaming response
    full_response = ""
    message_placeholder = st.empty()
    with message_placeholder.chat_message("assistant", avatar="🤖"):
        response_placeholder = st.empty()
        
        try:
            for chunk in chat(
                model=st.session_state.to_stream["model"],
                messages=st.session_state.to_stream["messages"],
                stream=True
            ):
                if st.session_state.stop_requested:
                    break
                    
                delta = chunk.get("message", {}).get("content", "")
                full_response += delta
                
                # Update with basic formatting during streaming
                formatted = render_markdown_with_code(full_response)
                response_placeholder.markdown(formatted + "▌", unsafe_allow_html=True)
                
                # Small delay to prevent UI blocking
                time.sleep(0.01)
                
        except Exception as e:
            full_response = f"**Error:** {str(e)}"
            response_placeholder.markdown(full_response)
    
    # Final rendering with proper formatting
    formatted_response = render_markdown_with_code(full_response)
    response_placeholder.markdown(formatted_response, unsafe_allow_html=True)
    
    # Add assistant message to history with formatting flag
    st.session_state.messages.append({
        "role": "assistant",
        "content": formatted_response,
        "formatted": True
    })
    
    # Save to history
    if st.session_state.current_idx is None:
        # New chat
        first_user = next((m["content"] for m in st.session_state.messages if m["role"] == "user"), "Chat")
        title = first_user[:30] + "..." if len(first_user) > 30 else first_user
        st.session_state.chat_history.append({
            "name": title,
            "messages": st.session_state.messages.copy(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "model": selected_model
        })
        st.session_state.current_idx = len(st.session_state.chat_history) - 1
    else:
        # Update existing chat
        st.session_state.chat_history[st.session_state.current_idx] = {
            **st.session_state.chat_history[st.session_state.current_idx],
            "messages": st.session_state.messages.copy(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "model": selected_model
        }
    
    save_history(st.session_state.chat_history)
    
    # Reset streaming state
    st.session_state.to_stream = None
    st.session_state.stop_requested = False
    st.rerun()