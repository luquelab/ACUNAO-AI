import os
from utils.embeddings import initialize_embeddings_and_db
from utils.pdfparser import PDFLoader
from langchain_community.vectorstores.utils import filter_complex_metadata
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uuid
from pathlib import Path    
import logging
import time
import json
from datetime import datetime
from pytz import timezone
from docx2pdf import convert
import shutil


class DocumentEventHandler(FileSystemEventHandler):
    """
    A custom event handler for monitoring and processing document-related events in a file system. This handler processes files with specific extensions and triggers actions on create, modify, and delete events.
    
    Attributes:
        processor: An instance responsible for processing and updating the vector database.
        supported_extensions: A set of file extensions that the handler will process.
        process_start: A flag indicating the processing state.
    """
    def __init__(self, processor):
        self.processor = processor
        self.process_start = False
        self.process_end = False
        self.del_process_start = False
        self.del_process_end = False

    def on_any_event(self, event):
        normalized_path = os.path.normpath(event.src_path)
        path_parts = normalized_path.split(os.sep)
        
        if event.is_directory or not event.src_path.endswith(tuple(self.processor.supported_extensions)) or self.should_ignore(event.src_path):
            return None

        database_index = path_parts.index("ACUNAOn-Data")
        subpath_parts = path_parts[database_index + 1:]
        if subpath_parts and os.path.splitext(subpath_parts[-1])[1]:
            subpath_parts = subpath_parts[:-1]
        self.processor.folder_name = os.sep.join(subpath_parts)

        if len(self.processor.folder_name) != 0: 
            if event.event_type in ['created', 'modified']:
                if not self.process_start:  # Only process if not already processing
                    self.processor.embeddings, self.processor.client, self.processor.vectordb, self.processor.text_splitter = initialize_embeddings_and_db(self.processor.folder_name)
                    self.processor.update_vector_db(event.src_path)

            elif event.event_type == 'deleted':
                self.del_process_start = True
                self.processor.embeddings, self.processor.client, self.processor.vectordb, self.processor.text_splitter = initialize_embeddings_and_db(self.processor.folder_name)
                self.processor.delete_from_vector_db(event.src_path)
                self.del_process_end = True

    def should_ignore(self, path):
        # Ignore files ending with '.tmp' or starting with '~'
        filename = os.path.basename(path)
        if filename.endswith('.tmp') or filename.startswith('~'):
            return True
        return False

class DocumentProcessor:
    """
    A class responsible for processing documents, managing embeddings, and interfacing with a vector database. This class initializes necessary components and sets up a file system observer for monitoring changes in the specified folder path.

    Attributes:
        desktop_path: Path to the ACUNAOn-Data folder.
        folder_name: Name of selected folder within ACUNAOn-Data.
        folder_path: Path to the folder containing documents to be processed.
        vectordb: Path to the vector database.
        embeddings: Placeholder for document embeddings.
        text_splitter: Placeholder for a text splitting utility.
        files: List to hold the names of the files to be processed.
        observer: Observer for monitoring file system changes.
        event_handler: Event handler for processing document-related events.
        observer_initialized: Flag indicating whether the observer has been initialized.
        observer_thread: Thread for running the observer.
        supported_extensions: List of file extensions that the processor will handle.
        timezone: Timezone to handle dates.
    """
    def __init__(self):
        self.desktop_path = os.path.join(os.path.expanduser("~"), "Documents", "ACUNAOn-Data")
        self.folder_name = "project_example" 
        self.folder_path = os.path.join(self.desktop_path, self.folder_name)
        self.vectordb = None
        self.embeddings = None
        self.text_splitter = None
        self.files = []
        self.observer = None
        self.event_handler = None
        self.observer_initialized = False
        self.observer_thread = None
        self.supported_extensions = [".pdf", ".docx"]
        self.timezone = timezone('America/New_York') # Datetime defaults to EST

    def save_file_metadata(self, metadata, metadata_file):
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)

    def add_file_metadata(self, metadata, filename, database, datenow, timenow, modified_at, clock_time, cpu_time, size, filetype):
        metadata[filename] = {
            "database": database,
            "date_added": datenow,
            "time_added": timenow,
            "modified_at": modified_at,
            "clock_time": f"{clock_time}s",
            "cpu_time": f"{cpu_time}s",
            "size": f"{size}kb",
            "filetype": filetype
        }   

    def initialize_observer(self):
        if not self.observer_initialized:
            self.observer = Observer()
            self.event_handler = DocumentEventHandler(self)
            self.observer.schedule(self.event_handler, self.desktop_path, recursive=True)
            self.observer.start()
            self.observer_initialized = True

    def update_vector_db(self, file_path):
        file_extension = os.path.splitext(file_path)[1]

        if file_extension == ".docx":
            filename = Path(file_path).name
            database = os.path.dirname(os.path.abspath(file_path))
            metadata_file = os.path.join(database, "metadata.json")
            size = os.path.getsize(file_path)/1000
            modified_at = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(os.path.getmtime(file_path)))

            # Load existing metadata if the file exists
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            # Skip files that have already been processed
            if filename in metadata and metadata[filename]["modified_at"] == modified_at:
                logging.info("Skipping already processed file: %s", file_path)
                return
            
            else: 
                start_time = time.time()
                t1_start = time.process_time() 

                convert(file_path)

                end_time = time.time()
                t1_stop = time.process_time()

                clock_time = "{:.2f}".format(end_time - start_time)
                cpu_time = "{:.2f}".format(t1_stop - t1_start)
                datenow, timenow = datetime.now(self.timezone).isoformat().split("T")

                self.add_file_metadata(metadata, filename, database, datenow, timenow, modified_at, clock_time, cpu_time, size, file_extension)
                self.save_file_metadata(metadata, metadata_file)
        
        elif file_extension == ".pdf":
            filename = Path(file_path).name
            database = os.path.dirname(os.path.abspath(file_path))
            metadata_file = os.path.join(database, "metadata.json")
            size = os.path.getsize(file_path)/1000
            modified_at = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(os.path.getmtime(file_path)))
        
            # Load existing metadata if the file exists
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            # Skip files that have already been processed
            if filename in metadata and metadata[filename]["modified_at"] == modified_at:
                logging.info("Skipping already processed file: %s", file_path)
                return

            else:
                print("Changes detected in folder. Updating vector database...")
                self.event_handler.process_start = True
                start_time = time.time()
                t1_start = time.process_time() 

                logging.info("Processing file: %s", file_path)

                loader = PDFLoader(file_path)

                documents = loader.load()
                text_chunks = filter_complex_metadata(self.text_splitter.split_documents(documents))

                self.vectordb.add(
                    documents=[doc.page_content for doc in text_chunks],
                    metadatas=[doc.metadata for doc in text_chunks],
                    ids=[str(uuid.uuid4()) for _ in range(len(text_chunks))]
                )

                logging.info("File processed: %s", file_path)
                end_time = time.time()
                t1_stop = time.process_time()

                clock_time = "{:.2f}".format(end_time - start_time)
                cpu_time = "{:.2f}".format(t1_stop - t1_start)
                datenow, timenow = datetime.now(self.timezone).isoformat().split("T")

                self.add_file_metadata(metadata, filename, database, datenow, timenow, modified_at, clock_time, cpu_time, size, file_extension)
                self.save_file_metadata(metadata, metadata_file)
                self.event_handler.process_end = True

    def delete_from_vector_db(self, file_path):
        filename = Path(file_path).name
        database = os.path.dirname(os.path.abspath(file_path))
        metadata_file = os.path.join(database, "metadata.json")

        # Load existing metadata if the file exists
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}

        if filename in metadata:
            print(f"File deleted: {file_path}. Removing from vector database...")
            self.vectordb.delete(where={"source": file_path})

            del metadata[filename]

            self.save_file_metadata(metadata, metadata_file)

    def run(self):
        if self.folder_name == "project_example":
            src_folder_path = "./data/2_test_data"
            dest_folder_path = os.path.join(self.desktop_path, self.folder_name)
            for item in os.listdir(src_folder_path):
                s = os.path.join(src_folder_path, item)
                d = os.path.join(dest_folder_path, item)
                # Skip .md files
                if os.path.isfile(s) and s.endswith('.md'):
                    continue
                # Copy the files to the directory
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

        self.embeddings, self.client, self.vectordb, self.text_splitter = initialize_embeddings_and_db(self.folder_name)
        if not self.observer_initialized:
            self.initialize_observer()

        try:
            print("Running document processor. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Interrupted by user. Stopping...")
        except Exception as error:
            print("Error processing documents: " + str(error))
        finally:
            self.stop_observer()

    def stop_observer(self):
        if self.observer_initialized:
            self.observer.stop()
            self.observer.join()
            print("Stopped the observer and saved state.")
            self.observer_initialized = False
