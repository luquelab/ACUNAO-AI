import os
import streamlit as st
from loader import DocumentProcessor
from llm import ChatPDFAssistant, PrintRetrievalHandler
import subprocess
import platform
import threading
import time
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from langchain_community.embeddings import SentenceTransformerEmbeddings
# import ollama


st.set_page_config(page_title="💬 ACUNAO Chatbot", layout="wide")

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
    st.title("💬 ACUNAO Chatbot")
    st.subheader("Chat with your documents")
    st.markdown(
        """
        An AI assistant programmed to answer questions and provide information based on the documents you provide. If the AI assistant's answer is not based on the context, please let our lab know.  

        Press control + c  in the terminal or command line to stop the assistant.
        """
        )

    # Specify the desktop path and folder name for files storage
    desktop_path = os.path.join(os.path.expanduser("~/Documents"))
    folder_name = "ACUNAO-Data"
    folder_path = os.path.join(desktop_path, folder_name)

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Fetch initial list of folders
    if "folders" not in st.session_state:
        st.session_state.folders = get_folders(folder_path)
    
    # Display files in sidebar with options to delete
    st.subheader("Available Databases")
    st.success("Only update database list when document finished processing!")

    selected_db = st.selectbox(
        'Choose a database:',
        options=st.session_state.folders
    )

    # Button to update the database list
    if st.button("Update database list"):
        st.session_state.folders = get_folders(folder_path)

    if st.button("Open ACUNAO-Data Folder"):
        open_folder(folder_path)

    st.divider()

    st.subheader("Manage Chat History")
    st.warning("Warning: your chat history will be cleared from memory!", icon="⚠️")
    st.button('Clear Chat History', on_click=clear_chat_history, type="secondary")

@st.cache_resource
def init_embedding():
    embeddings = SentenceTransformerEmbeddings(model_name="nomic-ai/nomic-embed-text-v1.5", model_kwargs={"trust_remote_code":True})
    return embeddings

# @st.cache_resource
# def init_llm():
#     try:
#         model_list = ollama.list()
#         if "phi3:medium-128k" not in model_list:
#             ollama.pull("phi3:medium-128k")
#     except Exception as e:
#         print(f"An error occurred: {e}")

st.title("💬 ACUNAO Chatbot")

st.info(
    """
    **Welcome! How may I assist you today?**  
    Start by adding supported documents into the ACUNAO-Data folder in your computer's Documents folder or click the 'Open ACUNAO-Data Folder' button in the sidebar. ACUNAO currently supports PDF documents:  

    1. Open ACUNAO-Data folder in your computer's Documents folder.  
    2. Create a new folder with your project name to create a new project.  
    3. Add documents into the folder and your AI assistant is ready to answer your questions!   
    4. Navigate to the terminal or command line and press control + c to stop the assistant.   

    **Pro tip:** Organize your project by creating separate folders for different topics inside your project to create separate databases!""")

if "messages" not in st.session_state.keys():
    # Set the initial AI message
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

for message in st.session_state.messages:
    # Display queries and responses
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Initiate the embeddings for llm
embeddings = init_embedding()

# Initiate the llm
# init_llm()

# Initiate llm based on database selected
if selected_db != None:
    st.warning("Initating selected database...")
    assistant = ChatPDFAssistant(selected_db, embeddings)
    st.success("Database initiated! Assistant is ready.", icon="✅")
else: 
    st.warning("Initating selected database...")
    assistant = ChatPDFAssistant(embeddings=embeddings)
    st.success("Database initiated! Assistant is ready.", icon="✅")

# Respond to user query
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        retrieval_handler = PrintRetrievalHandler(st.container()) # Callback for retriever
        st_cb = StreamlitCallbackHandler(
                        st.container(),
                        collapse_completed_thoughts=True,
                        expand_new_thoughts=True,
                        ) # Callback for RAG chain
        response = assistant.chat(prompt, st_cb=[st_cb, retrieval_handler])
        st.markdown(response)
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)

@st.cache_resource
def init_processor():
    processor = DocumentProcessor()
    return processor

# Initiate document processor and thread if not already done
if 'processor' not in st.session_state:
    st.session_state.processor = init_processor()
    st.session_state.processor_thread = threading.Thread(target=st.session_state.processor.run, daemon=True)
    st.session_state.processor_thread.start()

# Messages while document is processing 
while st.session_state.processor_thread.is_alive():
    # Display status of document processing 
    time.sleep(2)
    if st.session_state.processor.event_handler is not None:
        try:
            placeholder = st.empty()
            if st.session_state.processor.event_handler.process_start:
                placeholder.warning("New document detected!")
                time.sleep(3)
                placeholder.warning("Processing document...")
                st.session_state.processor.event_handler.process_start = False
            elif st.session_state.processor.event_handler.process_end:
                placeholder.success("Done! Finished processing document.", icon="✅")
                st.session_state.processor.event_handler.process_end = False
            elif st.session_state.processor.event_handler.del_process_start:
                placeholder.warning("Deleting document...")
                st.session_state.processor.event_handler.del_process_start = False
            elif st.session_state.processor.event_handler.del_process_end:
                placeholder.success("Done! Document deleted.", icon="✅")
                st.session_state.processor.event_handler.del_process_end = False
        except KeyboardInterrupt:
            break