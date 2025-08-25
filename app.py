import streamlit as st
import requests
import json
import os
from pathlib import Path
import time

# Configure the page
st.set_page_config(
    page_title="ChatWithPDF",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Global text color improvements */
    .stMarkdown, .stText, .stButton > button {
        color: #2c3e50 !important;
    }
    
    /* Header styling with better contrast */
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .sub-header {
        font-size: 1.5rem;
        color: #34495e;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    /* Section styling with better backgrounds */
    .upload-section {
        background-color: #ecf0f1;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 2px solid #bdc3c7;
    }
    
    .chat-section {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 10px;
        border: 2px solid #e8e8e8;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Message styling with high contrast */
    .message {
        padding: 1.5rem;
        margin: 0.8rem 0;
        border-radius: 12px;
        font-size: 1.1rem;
        line-height: 1.6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .user-message {
        background-color: #3498db;
        color: white;
        border-left: 5px solid #2980b9;
        font-weight: 500;
    }
    
    .user-message strong {
        color: #ecf0f1;
    }
    
    .assistant-message {
        background-color: #2ecc71;
        color: white;
        border-left: 5px solid #27ae60;
        font-weight: 500;
    }
    
    .assistant-message strong {
        color: #ecf0f1;
    }
    
    /* Status boxes with better contrast */
    .status-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .success {
        background-color: #d5f4e6;
        border: 2px solid #27ae60;
        color: #1e8449;
    }
    
    .error {
        background-color: #fadbd8;
        border: 2px solid #e74c3c;
        color: #c0392b;
    }
    
    .info {
        background-color: #d6eaf8;
        border: 2px solid #3498db;
        color: #21618c;
    }
    
    /* Warning styling */
    .warning {
        background-color: #fef9e7;
        border: 2px solid #f39c12;
        color: #d68910;
    }
    
    /* Button improvements */
    .stButton > button {
        background-color: #3498db !important;
        color: white !important;
        border: 2px solid #2980b9 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #2980b9 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }
    
    /* Input field improvements */
    .stTextInput > div > div > input {
        border: 2px solid #bdc3c7 !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-size: 1rem !important;
        background-color: #ffffff !important;
        color: #2c3e50 !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3498db !important;
        box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1) !important;
    }
    
    /* File uploader improvements */
    .stFileUploader > div > div {
        border: 2px dashed #bdc3c7 !important;
        border-radius: 10px !important;
        background-color: #f8f9fa !important;
        padding: 2rem !important;
    }
    
    .stFileUploader > div > div:hover {
        border-color: #3498db !important;
        background-color: #ecf0f1 !important;
    }
    
    /* Metric improvements */
    .stMetric > div > div {
        background-color: #ecf0f1 !important;
        border: 2px solid #bdc3c7 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        color: #2c3e50 !important;
    }
    
    /* Sidebar improvements */
    .css-1d391kg {
        background-color: #f8f9fa !important;
        border-right: 2px solid #e8e8e8 !important;
    }
    
    /* General text improvements */
    p, div, span {
        color: #2c3e50 !important;
    }
    
    /* Links */
    a {
        color: #3498db !important;
        text-decoration: none !important;
    }
    
    a:hover {
        color: #2980b9 !important;
        text-decoration: underline !important;
    }
</style>
""", unsafe_allow_html=True)

# API configuration
API_BASE_URL = "http://localhost:8000"

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def upload_pdf(file):
    """Upload PDF to the API"""
    try:
        files = {'file': file}
        response = requests.post(f"{API_BASE_URL}/upload-pdf", files=files)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error: {response.text}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def ask_question(question):
    """Ask a question to the API"""
    try:
        data = {'question': question}
        response = requests.post(f"{API_BASE_URL}/ask", data=data)
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error: {response.text}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def main():
    # Header
    st.markdown('<h1 class="main-header">📚 ChatWithPDF</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload your PDF and ask questions about it using AI</p>', unsafe_allow_html=True)
    
    # Check API health
    if not check_api_health():
        st.error("⚠️ API server is not running. Please start the server first using `python main.py`")
        st.info("Make sure the API is running on http://localhost:8000")
        return
    
    # Sidebar for file management
    with st.sidebar:
        st.header("📁 File Management")
        
        # File upload section
        st.subheader("Upload PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a PDF file to start chatting"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            # Upload button
            if st.button("🚀 Process PDF"):
                with st.spinner("Processing PDF..."):
                    result, error = upload_pdf(uploaded_file)
                    
                    if result:
                        st.session_state['pdf_processed'] = True
                        st.session_state['file_info'] = result
                        st.success("PDF processed successfully!")
                        
                        # Display file info
                        st.json(result)
                    else:
                        st.error(error)
        
        # Display processed file info
        if 'file_info' in st.session_state:
            st.subheader("📊 File Information")
            info = st.session_state['file_info']
            st.metric("Chunks", info['chunks_count'])
            st.metric("Images", info['images_count'])
            st.metric("Tables", info['tables_count'])
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Chat interface
        st.header("💬 Chat with Your PDF")
        
        if 'pdf_processed' not in st.session_state:
            st.info("👆 Please upload and process a PDF file first to start chatting!")
        else:
            # Chat history
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = []
            
            # Display chat history
            for message in st.session_state['chat_history']:
                if message['role'] == 'user':
                    st.markdown(f'<div class="message user-message"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="message assistant-message"><strong>Assistant:</strong> {message["content"]}</div>', unsafe_allow_html=True)
            
            # Question input
            question = st.text_input(
                "Ask a question about your PDF:",
                placeholder="e.g., What are transformer models?",
                key="question_input"
            )
            
            if st.button("❓ Ask Question"):
                if question.strip():
                    # Add user question to chat
                    st.session_state['chat_history'].append({
                        'role': 'user',
                        'content': question,
                        'timestamp': time.time()
                    })
                    
                    # Get answer from API
                    with st.spinner("Thinking..."):
                        answer, error = ask_question(question)
                        
                        if answer:
                            # Add assistant answer to chat
                            st.session_state['chat_history'].append({
                                'role': 'assistant',
                                'content': answer['answer'],
                                'timestamp': time.time(),
                                'sources': answer.get('sources', [])
                            })
                            
                            st.success("✅ Answer received!")
                            st.rerun()  # Refresh to show new messages
                        else:
                            st.error(f"❌ {error}")
                else:
                    st.warning("Please enter a question!")
    
    with col2:
        # Quick actions and tips
        st.header("⚡ Quick Actions")
        
        if 'pdf_processed' in st.session_state:
            st.subheader("💡 Sample Questions")
            sample_questions = [
                "What is the main topic of this document?",
                "Can you summarize the key findings?",
                "What are the main conclusions?",
                "Explain the methodology used",
                "What are the limitations mentioned?"
            ]
            
            for q in sample_questions:
                if st.button(q, key=f"sample_{hash(q)}"):
                    st.session_state['question_input'] = q
                    st.experimental_rerun()
            
            st.subheader("🔄 Actions")
            if st.button("🗑️ Clear Chat History"):
                st.session_state['chat_history'] = []
                st.experimental_rerun()
            
            if st.button("📄 Process New PDF"):
                st.session_state['pdf_processed'] = False
                st.session_state['file_info'] = None
                st.session_state['chat_history'] = []
                st.experimental_rerun()
        else:
            st.info("Upload a PDF to see quick actions and sample questions!")
        
        # Help section
        st.header("❓ Help")
        st.markdown("""
        **How to use:**
        1. Upload a PDF file
        2. Click "Process PDF"
        3. Ask questions in the chat
        4. Get AI-powered answers!
        
        **Tips:**
        - Use specific questions for better answers
        - The AI understands context from your PDF
        - Images and tables are also analyzed
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #666;'>Built with Streamlit • Powered by LangChain & Groq</p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
