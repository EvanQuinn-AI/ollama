Llama: Streamlit Chat Application with AI Assistant
Overview
This code is designed to create an interactive chat interface using the Streamlit library and the ollama library for generating responses from an AI model. The application allows users to communicate with a text-based AI assistant, which can be customized through various settings such as selecting different models or providing system instructions. It supports file uploads that are processed to extract text content, which is then included in conversations between the user and the AI.

Installation
To use this code:

Install Dependencies: Ensure you have Streamlit installed by running pip install streamlit if it's not already set up on your environment.
Install necessary libraries with:
pip install PyPDF2 docx2txt

Make sure the ollama library is available or compatible with this code.
Usage
Constants and Configuration
HISTORY_DIR: Specifies the directory for storing chat histories.
SYSTEM_PROMPT_KEY and USER_ID_KEY: Used for managing session states related to system prompts and user IDs respectively.
Functions Overview:
get_user_history_file(): Generates a unique file path for each user's chat history.
load_history(): Loads chat history from the disk if available, else returns an empty list.
save_history(): Saves the current state of history to disk.
get_ollama_models(): Lists available models that can be used by ollama.
render_markdown_with_code(): Formats code blocks in Markdown for better readability.
extract_text_from_file(): Processes uploaded files like PDFs, DOCXs, and TXTs.
Session State Initialization
Initializes session state variables including chat history, messages, current index of conversation, streaming state, etc., to ensure the application can track user interactions across sessions.

Chat Interface Components:
Sidebar Controls: Allows users to select models, set system prompts, manage file uploads, and switch or clear chat histories.
Main Chat Window: Displays previous conversations with formatted text blocks for messages. Includes options to load past chats, view file context during a conversation.
Input and Streaming Section: Features an input field where users can type messages. Includes mechanisms to stream AI-generated responses in real-time.
File Context Display
Automatically includes the content of uploaded files as part of each message sent by the user when interacting with the AI assistant.

Interaction Logic:
Users can engage in conversations with the AI, which processes system prompts and responses dynamically based on selected models. The application manages file uploads to enhance context-aware interactions.

Customization Tips
Model Selection: Users can choose from a list of available models, potentially expanding functionality by integrating different AI agents.
System Instructions: Customize instructions provided to the AI assistant for tailored behavior specific to your use case.
User Interface Enhancements: The code includes scripts to maintain UI consistency and smoothness during interactions. Tailor these as needed.
Future Development
Improved Error Handling: Implement more robust error handling mechanisms to provide better user feedback when encountering technical issues or API timeouts.
UI/UX Improvements: Optimize the interface for mobile devices and improve loading times by optimizing dependencies or using asynchronous calls where appropriate.
Security Enhancements: Ensure that uploaded files are securely handled, especially if sensitive data might be involved.
This application offers a dynamic chat experience with an AI assistant capable of processing various types of file inputs, enhancing user engagement through context-aware conversations.
