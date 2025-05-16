import json
import os
import re
from typing import Optional, Dict, Text, Any, List
from urllib.parse import urlparse

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
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=config.get('api_key') or "",
            base_url=config.get('server'),
            headers=config.get('headers')
        ) if config else OpenAIEmbeddings()
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
               sources: Optional[List] = None,
               **kwargs
               ):
        if kwargs.get("server") and kwargs.get("headers"):
            if config is None:
                config = {}
            config["server"] = kwargs.get("server")
            config["headers"] = kwargs.get("headers")
        file, web = cls._classify(sources, file, web)
        knowledge_base = {
            'faq': faq,
            'file': file,
            'web': web,
        }
        return cls(name, description, config, knowledge_base)

    def prepare(
            self,
            faq_data: Optional[Any] = None,
            files_dir: Optional[List[Text]] = None,
            web_urls: Optional[List[Text]] = None
    ) -> None:
        """
        Prepare the RAG system by loading and indexing knowledge sources.

        Args:
            faq_data: FAQ dict
            files_dir: Directory containing documents (PDF, TXT, CSV)
            web_urls: List of web URLs to scrape
        """
        documents = []

        # Load FAQ if provided
        if faq_data:
            for faq in faq_data:
                # Combine Q&A into a single document
                question = faq.get('q')
                answer = faq.get('a')
                content = f"Question: {question}\nAnswer: {answer}"
                documents.append(Document(
                    page_content=content,
                    metadata={"source": "faq", "type": "qa"}
                ))

        # Load documents if directory provided
        if files_dir:
            for files in files_dir:
                if not os.path.exists(files):
                    logger.error(f"The path: {files} is not a valid one.")
                    continue
                for root, _, filenames in os.walk(files):  # 递归遍历所有子目录
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

    @staticmethod
    def _classify(scources, file=None, web=None):
        if web is None:
            web = []
        if file is None:
            file = []

        def is_url(s):
            try:
                result = urlparse(s)
                return result.scheme in ('http', 'https', 'ftp') and bool(result.netloc)
            except Exception as e:
                return False

        def is_path(s):
            return os.path.isabs(s) or os.path.exists(s) or bool(re.match(r'^(\./|\.\./|/)?[\w\-/\\\.]+$', s))

        if scources is None:
            return file, web

        for source in scources:
            if is_url(source):
                web.append(source)
            if is_path(source):
                file.append(source)
        return file, web