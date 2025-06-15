import streamlit as st
from ollama import chat
import subprocess, json, os, time, uuid
from datetime import datetime
from pathlib import Path

# Dependencies: pip install PyPDF2 docx2txt

# ─── Constants & Helpers ──────────────────────────────────────────────────────
HISTORY_DIR = "chat_histories"
SYSTEM_PROMPT_KEY = "system_prompt"
USER_ID_KEY = "user_id"

# Create history directory
Path(HISTORY_DIR).mkdir(exist_ok=True)

def get_user_history_file():
    """Get history file path for current user"""
    if USER_ID_KEY not in st.session_state:
        st.session_state[USER_ID_KEY] = str(uuid.uuid4())
    return os.path.join(HISTORY_DIR, f"{st.session_state[USER_ID_KEY]}.json")

def load_history():
    history_file = get_user_history_file()
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_history(h):
    with open(get_user_history_file(), "w", encoding="utf-8") as f:
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

def extract_text_from_file(uploaded_file):
    """Extract text from various file types"""
    try:
        # Text-based files
        if uploaded_file.type.startswith('text/') or \
           uploaded_file.type in ['application/json', 'application/xml']:
            return uploaded_file.getvalue().decode('utf-8')
            
        # PDF files
        elif uploaded_file.type == 'application/pdf':
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(uploaded_file)
                return "\n".join([page.extract_text() for page in reader.pages])
            except ImportError:
                st.error("PyPDF2 required for PDF processing. Install with `pip install PyPDF2`")
                return None
                
        # Word documents
        elif uploaded_file.type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                                   'application/msword']:
            try:
                import docx2txt
                return docx2txt.process(uploaded_file)
            except ImportError:
                st.error("docx2txt required for DOCX processing. Install with `pip install docx2txt`")
                return None
                
        else:
            st.error(f"Unsupported file type: {uploaded_file.type}")
            return None
            
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

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
if SYSTEM_PROMPT_KEY not in st.session_state:
    st.session_state[SYSTEM_PROMPT_KEY] = "You are a helpful AI assistant."
if "file_text" not in st.session_state:
    st.session_state.file_text = None

st.set_page_config(
    page_title="Ollama Chat",
    layout="centered",  # Changed to centered for better button layout
    page_icon="🤖"
)

# Custom CSS for better scrolling and button layout
st.markdown("""
    <style>
        /* Better scrolling behavior */
        .stApp {
            overflow: auto !important;
        }
        
        /* Better button layout */
        .stButton button {
            width: 100% !important;
        }
        
        /* Chat message container */
        .chat-container {
            max-height: 70vh;
            overflow-y: auto;
            padding-bottom: 20px;
        }
        
        /* Stop button styling */
        .stop-button {
            margin-bottom: 10px !important;
        }
    </style>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Settings")

# User info
st.sidebar.subheader(f"👤 User: {st.session_state[USER_ID_KEY][:8]}")

# File uploader
st.sidebar.subheader("📁 File Upload")
uploaded_file = st.sidebar.file_uploader(
    "Upload text-based file", 
    type=['txt', 'pdf', 'docx', 'doc', 'json', 'xml', 'csv'],
    label_visibility="collapsed"
)

if uploaded_file:
    with st.spinner("Extracting text from file..."):
        extracted_text = extract_text_from_file(uploaded_file)
        if extracted_text:
            st.session_state.file_text = extracted_text
            st.sidebar.success(f"Extracted {len(extracted_text)} characters")
            st.sidebar.expander("View extracted text").code(extracted_text[:2000] + ("..." if len(extracted_text) > 2000 else ""))
        else:
            st.session_state.file_text = None

if st.session_state.file_text:
    if st.sidebar.button("❌ Clear File Content"):
        st.session_state.file_text = None

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
    st.session_state.file_text = None

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

# Create a container for messages with better scrolling
chat_container = st.container()

with chat_container:
    # Display messages with nicer formatting
    for msg in st.session_state.messages:
        avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg["role"] == "assistant" and msg.get("formatted", False):
                st.markdown(msg["content"], unsafe_allow_html=True)
            else:
                st.markdown(msg["content"])

# ─── File Context Display ────────────────────────────────────────────────────
if st.session_state.file_text:
    with st.expander("📄 Current File Context"):
        st.caption("This text will be included with your next message")
        st.code(st.session_state.file_text[:3000] + ("..." if len(st.session_state.file_text) > 3000 else ""))

# ... (keep all your existing imports and code until the streaming section)

# ... (keep all your existing imports and code until the streaming section)

# ─── Input and Streaming ─────────────────────────────────────────────────────
if st.session_state.to_stream is None:
    user_input = st.chat_input("Type your message here...")
    if user_input:
        # Add file context if available
        if st.session_state.file_text:
            user_input = f"File context:\n{st.session_state.file_text}\n\n---\n\n{user_input}"
            st.session_state.file_text = None  # Clear after use
        
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
    # Better stop button layout
    stop_col, _ = st.columns([1, 5])
    with stop_col:
        if st.button("⏹️ Stop Generating", key="stop_button", use_container_width=True):
            st.session_state.stop_requested = True
            st.rerun()
    
    # Create a container specifically for the streaming message
    streaming_container = st.container()
    
    with streaming_container:
        full_response = ""
        message_placeholder = st.empty()
        
        with message_placeholder.container():
            with st.chat_message("assistant", avatar="🤖"):
                response_placeholder = st.empty()
                
                # Initial scroll to bottom
                st.markdown(
                    """
                    <script>
                    function scrollToBottom() {
                        // Try to find the specific chat container first
                        const chatContainer = window.parent.document.querySelector('.chat-container');
                        if (chatContainer) {
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        } else {
                            // Fallback to document scrolling
                            window.parent.document.body.scrollTop = window.parent.document.body.scrollHeight;
                            window.parent.document.documentElement.scrollTop = window.parent.document.documentElement.scrollHeight;
                        }
                    }
                    // Scroll immediately and then every 100ms during streaming
                    scrollToBottom();
                    const scrollInterval = setInterval(scrollToBottom, 100);
                    </script>
                    """,
                    unsafe_allow_html=True
                )
                
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
                finally:
                    # Clear the interval when done
                    st.markdown(
                        """
                        <script>
                        if (typeof scrollInterval !== 'undefined') {
                            clearInterval(scrollInterval);
                        }
                        scrollToBottom(); // One final scroll
                        </script>
                        """,
                        unsafe_allow_html=True
                    )
            
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

# Final auto-scroll to ensure we're at bottom
st.markdown(
    """
    <script>
    // Simple immediate scroll to bottom
    function scrollNow() {
        const chatContainer = window.parent.document.querySelector('.chat-container');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        } else {
            window.scrollTo(0, document.body.scrollHeight);
        }
    }
    // Try scrolling immediately and again after a short delay
    scrollNow();
    setTimeout(scrollNow, 300);
    </script>
    """, 
    unsafe_allow_html=True
)