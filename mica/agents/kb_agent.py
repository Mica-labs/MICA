import json
import os
from typing import Optional, Dict, Text, Any, List

from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, WebBaseLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from mica.agents.agent import Agent
from mica.event import AgentComplete
from mica.llm.openai_model import OpenAIModel
from mica.tracker import Tracker
from mica.utils import logger


class KBAgent(Agent):
    def __init__(self,
                 name: Optional[Text] = None,
                 description: Optional[Text] = None,
                 config: Optional[Dict[Text, Any]] = None,
                 knowledge_base: Optional[Any] = None,
                 similarity_threshold: float = 0.0,
                 top_k: int = 3,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 **kwargs
                 ):
        self.llm_model = OpenAIModel.create(config)
        self.knowledge_base = knowledge_base
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.vector_store = None
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.prepare(knowledge_base['faq'], knowledge_base['file'], knowledge_base['web'])
        super().__init__(name, description)

    @classmethod
    def create(cls,
               name: Optional[Text] = None,
               description: Optional[Text] = None,
               config: Optional[Dict[Text, Any]] = None,
               faq: Optional[Dict] = None,
               file: Optional[Any] = None,
               web: Optional[List] = None,
               **kwargs
               ):
        if kwargs.get("server") and kwargs.get("headers"):
            if config is None:
                config = {}
            config["server"] = kwargs.get("server")
            config["headers"] = kwargs.get("headers")
        knowledge_base = {
            'faq': faq,
            'file': file,
            'web': web
        }
        return cls(name, description, config, knowledge_base)

    def prepare(
            self,
            faq_data: Optional[Any] = None,
            files_dir: Optional[Text] = None,
            web_urls: Optional[List[Text]] = None
    ) -> None:
        """
        Prepare the RAG system by loading and indexing knowledge sources.

        Args:
            faq_data: FAQ dict
            docs_dir: Directory containing documents (PDF, TXT)
            web_urls: List of web URLs to scrape
        """
        documents = []

        # Load FAQ if provided
        if faq_data:
            for question, answer in faq_data.items():
                # Combine Q&A into a single document
                content = f"Question: {question}\nAnswer: {answer}"
                documents.append(Document(
                    page_content=content,
                    metadata={"source": "faq", "type": "qa"}
                ))

        # Load documents if directory provided
        if files_dir and os.path.exists(files_dir):
            for root, _, filenames in os.walk(files_dir):  # 递归遍历所有子目录
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    if filename.endswith('.pdf'):
                        loader = PyPDFLoader(filepath)
                        documents.extend(loader.load())
                    elif filename.endswith('.txt'):
                        loader = TextLoader(filepath)
                        documents.extend(loader.load())
                    elif filename.endswith('.csv'):
                        loader = CSVLoader(filepath)
                        documents.extend(loader.load())

        # Load web content if URLs provided
        if web_urls:
            loader = WebBaseLoader(web_urls)
            documents.extend(loader.load())

        # Split documents into chunks
        if documents:
            texts = self.text_splitter.split_documents(documents)
            print(texts)
            # Create vector store
            self.vector_store = FAISS.from_documents(texts, self.embeddings)
            logger.debug(f"Indexed {len(texts)} text chunks from {len(documents)} documents")

    async def run(self, tracker: Tracker, **kwargs):
        """
        Process a user query against the knowledge base.
        Args:

        Returns:
            Dict containing matches and their scores if similarity threshold is met,
            None otherwise
        """
        if not self.vector_store:
            raise ValueError("Knowledge base not prepared. Call prepare() first.")

        user_input = tracker.latest_message.text
        # Search for similar documents
        docs_and_scores = self.vector_store.similarity_search_with_score(
            user_input,
            k=self.top_k
        )

        # Filter and format results
        matches = []
        for doc, score in docs_and_scores:
            if score >= self.similarity_threshold:
                matches.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score
                })

        if matches:
            metadata = {
                "matches": matches,
                "query": user_input,
                "total_matches": len(matches)
            }
            return True, [AgentComplete(provider=self.name, metadata=metadata)]
        return True, [AgentComplete(provider=self.name, metadata=None)]

