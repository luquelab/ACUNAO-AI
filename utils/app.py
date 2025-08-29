import os
import streamlit as st
from utils.loader import DocumentProcessor
from utils.llm import ChatPDFAssistant 
from utils.embeddings import initialize_embeddings_and_db
import subprocess
import platform
import threading
import time
from langchain_community.chat_models import ChatLlamaCpp
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from streamlit.runtime.scriptrunner import add_script_run_ctx
import clipboard
import json
from datetime import datetime
from pytz import timezone
import os, signal
import torch


st.set_page_config(page_title="💬 ACUNAO AI Chatbot", layout="wide")

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stAppDeployButton {visibility: hidden;}
</style>

"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

def open_folder(path):
    """
    Opens the folder that houses the database and documents used in the RAG system.
    """
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":  # macOS
        subprocess.Popen(["open", path])
    else:  # Linux
        subprocess.Popen(["xdg-open", path])

# Function to get all folders and subfolders
def get_folders(base_path):
    folders = []
    for root, dirs, _ in os.walk(base_path):
        # Filter out "vectordb" and hidden folders
        dirs[:] = [d for d in dirs if d.lower() != "vectordb" and d.lower() != "llm" and not d.startswith('.')]
        for dir in dirs:
            # Store relative path of the folder
            folders.append(os.path.relpath(os.path.join(root, dir), base_path))
    return folders

def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

with st.sidebar:
    st.title("💬 ACUNAO AI Chatbot")
    st.subheader("Chat with your documents")
    st.markdown(
        """
        An AI assistant programmed to answer questions and provide information based on the documents you provide. If the AI assistant's answer is not based on the context, please let our lab know.  
        """
        )

    st.subheader("Quit app")
    st.markdown("Click button then close browser.")
    if st.button("Quit app"):
        os.kill(os.getpid(), signal.SIGKILL)

    # Specify the desktop path and folder name for files storage
    desktop_path = os.path.join(os.path.expanduser("~/Documents"))
    folder_name = "ACUNAO-AI-Data"
    folder_path = os.path.join(desktop_path, folder_name)

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Fetch initial list of folders
    if "folders" not in st.session_state:
        st.session_state.folders = get_folders(folder_path)
    
    # Display files in sidebar with options to delete
    st.subheader("Available Databases")

    selected_db = st.selectbox(
        'Choose a database:',
        options=st.session_state.folders
    )

    # Button to update the database list
    if st.button("Update database list"):
        st.session_state.folders = get_folders(folder_path)

    if st.button("Open ACUNAO-AI-Data Folder"):
        open_folder(folder_path)

    st.divider()

    st.subheader("Manage Chat History")
    st.warning("Warning: your chat history will be cleared from memory!", icon="⚠️")
    st.button('Clear Chat History', on_click=clear_chat_history, type="secondary")

@st.cache_resource
def init_embedding():
    embeddings = HuggingFaceEmbeddings(model_name="nomic-ai/nomic-embed-text-v1.5", model_kwargs={"trust_remote_code":True})
    return embeddings

@st.cache_resource
def init_llm():
    if torch.cuda.is_available():
        _, _, _, _, llm_model = initialize_embeddings_and_db("project_example")
        llm = ChatLlamaCpp(
            model_path = llm_model,
            n_gpu_layers = -1, 
            temperature = 0.0,
            n_ctx = 5028,
            streaming=True,
        )
    else:
        _, _, _, _, llm_model = initialize_embeddings_and_db("project_example")
        llm = ChatLlamaCpp(
            model_path = llm_model,
            temperature = 0.0,
            n_ctx = 5028,
            streaming=True,
        )
    return llm

st.title("💬 ACUNAO AI Chatbot")

st.info(
    """
    **Welcome! How may I assist you today?**  
    Start by adding supported documents into the ACUNAO-AI-Data folder in your computer's Documents folder or click the 'Open ACUNAO-AI-Data Folder' button in the sidebar. ACUNAO AI currently supports PDF documents:  

    1. Open ACUNAO-AI-Data folder in your computer's Documents folder.  
    2. Create a new folder with your project name to create a new project.  
    3. Add documents into the folder.
    4. Wait for your document to process. You will be notified when it is done processing. View the metadata.txt in the folder to see if the document loaded successfully.
    5. ACUNAO AI is ready to answer your questions!   

    **Read the README.txt file if you haven't!**

    When asking for summarization, you would have to specify the title of the document you would like to be summarized, not the name of the pdf.
    
    **Pro tip:** Organize your project by creating separate folders for different topics inside your project to create separate databases!""")

if "copied" not in st.session_state.keys(): 
    st.session_state.copied = []

if "messages" not in st.session_state.keys():
    # Set the initial AI message
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

if "message_history" not in st.session_state:
    st.session_state.message_history = StreamlitChatMessageHistory(key="chat_history")

for message in st.session_state.messages:
    # Display queries and responses
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.message_history.add_message({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Initiate the embeddings for llm
embeddings = init_embedding()

# Initiate the llm
llm = init_llm()

# Initiate llm based on database selected
if selected_db != None:
    st.warning("Initiating selected database...")
    assistant = ChatPDFAssistant(db=selected_db, embeddings=embeddings, llm=llm)
    st.success("Database initiated! Assistant is ready.", icon="✅")
else: 
    st.warning("Initiating selected database...")
    assistant = ChatPDFAssistant(embeddings=embeddings, llm=llm)
    st.success("Database initiated! Assistant is ready.", icon="✅")

# Respond to user query
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):

        with st.status("Retrieving documents", expanded=True) as status:
            response_log = os.path.join(folder_path, ".response_log.json")

            if os.path.exists(response_log):
                with open(response_log, 'r') as f:
                    log = json.load(f)
            else:
                log = {}

            start_time = time.time()

            output = assistant.chat(prompt)

            end_time = time.time()
            clock_time = "{:.2f}".format(end_time - start_time)
            datetime_now = datetime.now(timezone('America/New_York')).isoformat()

            log[datetime_now] = {
                "response_time": f"{clock_time}s",
                "response": output["answer"]
            }

            with open(response_log, 'w') as f:
                json.dump(log, f, indent=4)

            # Context Retrieval status container
            with st.container():
                st.write(f"**Question:** {output['input']}")
                sources = []

                for i, doc in enumerate(output['context']):
                    source = doc.metadata.get("source", "File directory not available.")
                    page_number = doc.metadata.get("page", "Page number not available.")
                    
                    st.write(f"**Document {i+1}**")
                    st.markdown(f"**Source**: {source} **Page**: {page_number}")
                    st.markdown(doc.page_content)
                    sources.append(f"**Source**: {source} **Page**: {page_number}")

            status.update(label="Click here to view the sources!", state="complete", expanded=False)

        response = output["answer"]
        def stream_ans():
            for word in response.split(" "):
                yield word + " "
                time.sleep(0.02)

        source_response = "\n\n".join(["\n\n".join(sources), "\n\n".join(["**Answer:**", response])])

        st.markdown(f"**Answer:**")
        st.write_stream(stream_ans)
        st.button("📋", on_click=on_copy_click, args=(response,))

    message = {"role": "assistant", "content": source_response}
    st.session_state.messages.append(message)
    st.session_state.message_history.add_message(message)

@st.cache_resource
def init_processor():
    processor = DocumentProcessor()
    return processor

# Initiate document processor and thread if not already done
if 'processor' not in st.session_state:
    st.session_state.processor = init_processor()
    st.session_state.processor_thread = threading.Thread(target=st.session_state.processor.run, daemon=True)
    add_script_run_ctx(st.session_state.processor_thread)
    st.session_state.processor_thread.start()

placeholder = st.container()

# Messages while document is processing 
while st.session_state.processor_thread.is_alive():
    add_script_run_ctx(st.session_state.processor_thread)
    # Display status of document processing 
    time.sleep(2)
    if st.session_state.processor.event_handler is not None:
        try:
            if st.session_state.processor.event_handler.process_start:
                placeholder.warning("New document detected!")
                time.sleep(2)
                placeholder.empty()
                placeholder.warning("Processing document...")
                st.session_state.processor.event_handler.process_start = False
            elif st.session_state.processor.event_handler.process_end:
                placeholder = st.container()
                placeholder.success("Done! Finished processing document.", icon="✅")
                st.session_state.processor.event_handler.process_end = False
            elif st.session_state.processor.event_handler.del_process_start:
                placeholder.warning("Deleting document...")
                st.session_state.processor.event_handler.del_process_start = False
            elif st.session_state.processor.event_handler.del_process_end:
                placeholder = st.container()
                placeholder.success("Done! Document deleted.", icon="✅")
                st.session_state.processor.event_handler.del_process_end = False
        except KeyboardInterrupt:
            break