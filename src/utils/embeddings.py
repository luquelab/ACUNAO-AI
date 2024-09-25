import os
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb.utils import embedding_functions
import shutil


def initialize_embeddings_and_db(folder_name):
    # Set the chunk size and overlap for text splitting
    chunk_size = 4500
    chunk_overlap = 1000

    # Specify the desktop path and folder name for vector database storage
    desktop_path = os.path.join(os.path.expanduser("~/Documents"), "ACUNAO-Data")
    vdb_name = "vectordb"
    folder_path = os.path.join(desktop_path, folder_name, vdb_name)

    # Create the folder if it doesn't exist
    if folder_name != "llm":
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    # Copy llm to the ACUNAO-Data folder
    dest_folder_path = os.path.join(desktop_path, "llm")
    dest_file_path = os.path.join(dest_folder_path, "Phi-3-medium-128k-instruct-Q4_K_M.gguf")
    if not os.path.exists(dest_folder_path):
         os.makedirs(dest_folder_path)
    llm_path = "./data/2_test_data/Phi-3-medium-128k-instruct-Q4_K_M.gguf"
    if not os.path.isfile(dest_file_path):
        shutil.copy2(llm_path, dest_folder_path)
    llm = dest_file_path
    
    # Initialize embeddings
    embeddings = embedding_functions.SentenceTransformerEmbeddingFunction("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Initialize Chroma vector store or load existing if available
    if folder_name != "llm":
        client = chromadb.PersistentClient(folder_path)
        collection = client.get_or_create_collection(name="acunao-db", embedding_function=embeddings)

    return embeddings, client, collection, text_splitter, llm