import sys
from langchain_core.prompts import PromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from utils.embeddings import initialize_embeddings_and_db
from langchain_chroma import Chroma
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.retrievers.document_compressors import FlashrankRerank
from langchain.retrievers import ContextualCompressionRetriever


class ChatPDFAssistant:
    """Handles PDF ingestion, query processing, and answering queries using a chat model."""

    def __init__(self, db="project_example", embeddings=None, llm=None):
        # Initialize embeddings and vector database
        _, self.client, self.vectordb, self.text_splitter, _ = initialize_embeddings_and_db(db)

        self.db = Chroma(client=self.client, collection_name="acunao-db",embedding_function=embeddings)

        self.DEFAULT_SYSTEM_PROMPT = """
        You are a good, honest project assistant. 

        If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you do not know the answer to a question, make it clear you do not know the answer instead of making up false information.
        """.strip()

        self.SYSTEM_PROMPT = "Use the following pieces of context to answer the question at the end. You must only answer within the provided context. If you do not know the answer, just say you don't know, don't try to make up an answer."

        self.template = self.generate_prompt(
            """
            {context}

            Question: {input}
            """,
            system_prompt=self.SYSTEM_PROMPT,
        )

        self.qa_prompt = PromptTemplate(template=self.template, input_variables=['context', 'input'])

        # Implement Multiquery retriever
        retriever = MultiQueryRetriever.from_llm(
                                                retriever=self.db.as_retriever(), llm=llm
                                            )
        compressor = FlashrankRerank()
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=retriever
        )

        # Create QA Chain
        combine_docs_chain = create_stuff_documents_chain(llm, self.qa_prompt)
        self.chain = create_retrieval_chain(compression_retriever, combine_docs_chain)


    def generate_prompt(self, prompt: str, system_prompt: str) -> str:
        return f"""
        <|system|>
        {system_prompt}<|end|>

        <|user|>
        {prompt}<|end|>
        """.strip()

    def chat(self, input_text):
        user_input = str(input_text)
        if user_input == 'exit':
            print('Exiting')
            sys.exit()
        if user_input == '':
            return None
        # result = self.chain.invoke({'input': user_input}, {"callbacks": st_cb})
        result = self.chain.invoke({"input":user_input})
        
        return result