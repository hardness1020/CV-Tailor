"""
DocumentLoaderService - Pure I/O operations for loading and chunking documents.
Refactored from AdvancedDocumentProcessor for ft-005-multi-source-artifact-preprocessing.md

This service handles document loading WITHOUT LLM enhancement.
LLM operations moved to EvidenceContentExtractor.
"""

import logging
import hashlib
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# LangChain imports
try:
    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter,
        CharacterTextSplitter,
        MarkdownHeaderTextSplitter,
        HTMLHeaderTextSplitter
    )
    from langchain_community.document_loaders import (
        PyPDFLoader,
        UnstructuredPDFLoader,
        GitHubIssuesLoader,
        GithubFileLoader,
        UnstructuredHTMLLoader,
        TextLoader,
        UnstructuredMarkdownLoader
    )
    from langchain.schema import Document
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    # Create fallback Document class
    class Document:
        def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
            self.page_content = page_content
            self.metadata = metadata or {}

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.exceptions import SuspiciousFileOperation
from ..base.base_service import BaseLLMService

logger = logging.getLogger(__name__)


class DocumentLoaderService(BaseLLMService):
    """
    Pure I/O operations for loading and chunking documents.
    Extends BaseLLMService for access to circuit breaker and performance tracking.

    Key responsibilities:
    - Load documents from files/URLs/repositories
    - Parse formats (PDF, markdown, HTML, GitHub)
    - Split into chunks using LangChain
    - NO LLM calls, NO semantic analysis (moved to EvidenceContentExtractor)
    """

    def __init__(self):
        # Initialize config BEFORE calling super().__init__()
        self._service_config = getattr(settings, 'LANGCHAIN_SETTINGS', {})
        super().__init__()  # Initialize BaseLLMService dependencies
        self._init_text_splitters()

    def _get_service_config(self) -> Dict[str, Any]:
        """Get document loader specific configuration"""
        return self._service_config

    def _init_text_splitters(self):
        """Initialize various text splitting strategies"""
        chunk_size = self._service_config.get('chunk_size', 1000)
        chunk_overlap = self._service_config.get('chunk_overlap', 200)

        # Recursive character splitter (default)
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        ) if HAS_LANGCHAIN else None

        # Character splitter for simple cases
        self.character_splitter = CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        ) if HAS_LANGCHAIN else None

        # Markdown header splitter
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
                ("####", "Header 4"),
            ]
        ) if HAS_LANGCHAIN else None

        # HTML header splitter
        self.html_splitter = HTMLHeaderTextSplitter(
            headers_to_split_on=[
                ("h1", "Header 1"),
                ("h2", "Header 2"),
                ("h3", "Header 3"),
                ("h4", "Header 4"),
            ]
        ) if HAS_LANGCHAIN else None

    async def load_and_chunk_document(self,
                                     content: Union[str, bytes, Path],
                                     content_type: str,
                                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load document and split into chunks WITHOUT LLM enhancement.

        Args:
            content: File path, bytes, or content string
            content_type: Type of content ('pdf', 'github', 'html', 'markdown', 'text')
            metadata: Optional metadata to attach to chunks

        Returns:
            Dict with 'success', 'chunks', and 'processing_metadata'

        Note: LLM enhancement removed - moved to EvidenceContentExtractor
        """
        if not HAS_LANGCHAIN:
            return await self._fallback_processing(content, content_type, metadata)

        start_time = time.time()
        processing_metadata = {
            'content_type': content_type,
            'langchain_used': True,
            'processing_start_time': start_time
        }

        try:
            # Load document using appropriate loader
            documents = await self._load_document(content, content_type, metadata)

            # Apply intelligent text splitting
            chunks = self._apply_adaptive_splitting(documents, content_type)

            # Convert to simple dict format (NO LLM enhancement)
            simple_chunks = []
            for i, chunk in enumerate(chunks):
                simple_chunks.append({
                    'content': chunk.page_content,
                    'metadata': chunk.metadata,
                    'content_hash': hashlib.sha256(chunk.page_content.encode()).hexdigest()
                })

            processing_time = int((time.time() - start_time) * 1000)

            strategy_name = self._get_splitting_strategy_name(content_type)
            result = {
                'success': True,
                'total_chunks': len(simple_chunks),
                'chunks': simple_chunks,
                'processing_metadata': {
                    **processing_metadata,
                    'processing_time_ms': processing_time,
                    'strategy': strategy_name,  # Add strategy field for test compatibility
                    'splitting_strategy': strategy_name,
                    'original_document_count': len(documents),
                    'chunks_generated': len(chunks),
                    'total_chunks': len(simple_chunks)  # Add for test compatibility
                }
            }

            logger.info(f"Loaded {content_type} document into {len(simple_chunks)} chunks in {processing_time}ms")
            return result

        except Exception as e:
            logger.error(f"Document loading failed for {content_type}: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_metadata': {
                    **processing_metadata,
                    'processing_time_ms': int((time.time() - start_time) * 1000),
                    'error_occurred': True
                }
            }

    async def _load_document(self, content: Union[str, bytes, Path],
                           content_type: str,
                           metadata: Optional[Dict[str, Any]]) -> List[Document]:
        """Load document using appropriate LangChain loader"""
        # Implementation same as before in AdvancedDocumentProcessor
        # (keeping existing logic)

        base_metadata = metadata or {}
        base_metadata.update({
            'source_type': content_type,
            'processed_at': time.time()
        })

        if content_type == 'pdf':
            if isinstance(content, (str, Path)):
                # Handle both Django storage paths and absolute file paths
                content_str = str(content)
                content_path = Path(content_str)

                # Strategy 1: Try as absolute path first (for tests and direct file paths)
                if content_path.is_absolute() and content_path.exists():
                    loader = UnstructuredPDFLoader(content_str)
                    documents = loader.load()
                # Strategy 2: Try as Django storage path (for uploaded files)
                elif default_storage.exists(content_str):
                    try:
                        # Get absolute filesystem path from storage
                        abs_path = default_storage.path(content_str)
                        loader = UnstructuredPDFLoader(abs_path)
                        documents = loader.load()
                    except NotImplementedError:
                        # Storage backend doesn't support .path() (e.g., S3)
                        # Fall back to opening file and writing to temp file
                        import tempfile
                        with default_storage.open(content_str, 'rb') as storage_file:
                            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                                tmp_file.write(storage_file.read())
                                tmp_file.flush()
                                loader = UnstructuredPDFLoader(tmp_file.name)
                                documents = loader.load()
                            Path(tmp_file.name).unlink()
                    except SuspiciousFileOperation:
                        # File is outside MEDIA_ROOT, but might still be a valid path
                        # This can happen with test fixtures in /tmp
                        if content_path.exists():
                            loader = UnstructuredPDFLoader(content_str)
                            documents = loader.load()
                        else:
                            raise FileNotFoundError(f"PDF file not found: {content_str}")
                else:
                    raise FileNotFoundError(f"PDF file not found: {content_str}")
            else:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                    tmp_file.write(content)
                    tmp_file.flush()
                    loader = UnstructuredPDFLoader(tmp_file.name)
                    documents = loader.load()
                Path(tmp_file.name).unlink()

        elif content_type == 'github':
            repo_url = content if isinstance(content, str) else str(content)
            documents = await self._process_github_repository(repo_url, base_metadata)

        elif content_type in ['html', 'web_profile']:
            if isinstance(content, str) and content.startswith(('http://', 'https://')):
                loader = UnstructuredHTMLLoader(content)
                documents = loader.load()
            else:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                    tmp_file.write(content if isinstance(content, str) else content.decode('utf-8'))
                    tmp_file.flush()
                    loader = UnstructuredHTMLLoader(tmp_file.name)
                    documents = loader.load()
                Path(tmp_file.name).unlink()

        elif content_type == 'markdown':
            if isinstance(content, (str, Path)) and Path(content).exists():
                loader = UnstructuredMarkdownLoader(str(content))
                documents = loader.load()
            else:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp_file:
                    tmp_file.write(content if isinstance(content, str) else content.decode('utf-8'))
                    tmp_file.flush()
                    loader = UnstructuredMarkdownLoader(tmp_file.name)
                    documents = loader.load()
                Path(tmp_file.name).unlink()

        elif content_type == 'text':
            text_content = content if isinstance(content, str) else content.decode('utf-8')
            documents = [Document(page_content=text_content, metadata=base_metadata)]

        else:
            raise ValueError(f"Unsupported content type: {content_type}")

        for doc in documents:
            doc.metadata.update(base_metadata)

        return documents

    async def _process_github_repository(self, repo_url: str, metadata: Dict[str, Any]) -> List[Document]:
        """Process GitHub repository with specialized handling"""
        # Implementation same as before
        documents = []

        try:
            github_token = getattr(settings, 'GITHUB_TOKEN', '')

            # Load README files
            try:
                readme_loader = GithubFileLoader(
                    repo=repo_url,
                    access_token=github_token,
                    file_filter=lambda file_path: file_path.lower().endswith('readme.md') or
                                                file_path.lower() == 'readme'
                )
                readme_docs = readme_loader.load()
                for doc in readme_docs:
                    doc.metadata.update({**metadata, 'file_type': 'readme'})
                documents.extend(readme_docs)
            except Exception as e:
                logger.warning(f"Failed to load README files: {e}")

            # Load key source files (limited)
            try:
                code_loader = GithubFileLoader(
                    repo=repo_url,
                    access_token=github_token,
                    file_filter=lambda path: any(path.endswith(ext) for ext in
                                               ['.py', '.js', '.ts', '.java', '.cpp', '.go', '.rs']) and
                                            'test' not in path.lower() and
                                            len(path.split('/')) <= 3
                )
                code_docs = code_loader.load()

                max_files = self._service_config.get('max_code_files', 10)
                for doc in code_docs[:max_files]:
                    doc.metadata.update({**metadata, 'file_type': 'source_code'})
                documents.extend(code_docs[:max_files])

            except Exception as e:
                logger.warning(f"Failed to load source code files: {e}")

        except Exception as e:
            logger.error(f"GitHub repository processing failed: {e}")
            documents = [Document(
                page_content=f"GitHub Repository: {repo_url}",
                metadata={**metadata, 'file_type': 'repository_reference', 'error': str(e)}
            )]

        return documents

    def _apply_adaptive_splitting(self, documents: List[Document], content_type: str) -> List[Document]:
        """Apply intelligent text splitting based on document type"""
        # Implementation same as before
        if not HAS_LANGCHAIN:
            return documents

        all_chunks = []

        for doc in documents:
            content_length = len(doc.page_content)
            doc_type = doc.metadata.get('file_type', content_type)

            if doc_type == 'markdown' or content_type == 'markdown':
                if self.markdown_splitter and '##' in doc.page_content:
                    chunks = self.markdown_splitter.split_documents([doc])
                    if any(len(chunk.page_content) > 2000 for chunk in chunks):
                        final_chunks = []
                        for chunk in chunks:
                            if len(chunk.page_content) > 2000:
                                sub_chunks = self.recursive_splitter.split_documents([chunk])
                                final_chunks.extend(sub_chunks)
                            else:
                                final_chunks.append(chunk)
                        chunks = final_chunks
                else:
                    chunks = self.recursive_splitter.split_documents([doc])

            elif doc_type in ['html', 'web_profile']:
                if self.html_splitter and any(tag in doc.page_content.lower() for tag in ['<h1>', '<h2>', '<h3>']):
                    chunks = self.html_splitter.split_documents([doc])
                    if any(len(chunk.page_content) > 2000 for chunk in chunks):
                        final_chunks = []
                        for chunk in chunks:
                            if len(chunk.page_content) > 2000:
                                sub_chunks = self.recursive_splitter.split_documents([chunk])
                                final_chunks.extend(sub_chunks)
                            else:
                                final_chunks.append(chunk)
                        chunks = final_chunks
                else:
                    chunks = self.recursive_splitter.split_documents([doc])

            elif content_length > 5000 and doc_type in ['source_code', 'technical']:
                chunks = self.recursive_splitter.split_documents([doc])

            elif content_length > 2000:
                chunks = self.recursive_splitter.split_documents([doc])

            elif content_length > 500:
                chunks = self.character_splitter.split_documents([doc])

            else:
                chunks = [doc]

            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    'chunk_index': i,
                    'total_chunks_in_document': len(chunks),
                    'original_document_length': content_length,
                    'chunk_length': len(chunk.page_content),
                    'splitting_strategy': self._get_splitting_strategy_name(content_type, doc_type)
                })

            all_chunks.extend(chunks)

        max_chunks = self._service_config.get('max_chunks_per_document', 50)
        if len(all_chunks) > max_chunks:
            logger.warning(f"Document produced {len(all_chunks)} chunks, limiting to {max_chunks}")
            all_chunks = all_chunks[:max_chunks]

        return all_chunks

    async def _fallback_processing(self, content: Union[str, bytes, Path],
                                 content_type: str,
                                 metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback processing when LangChain is not available"""
        logger.warning("LangChain not available, using fallback processing")

        try:
            if isinstance(content, bytes):
                text_content = content.decode('utf-8', errors='ignore')
            elif isinstance(content, Path):
                text_content = content.read_text(encoding='utf-8', errors='ignore')
            else:
                text_content = str(content)

            chunks = []
            paragraphs = text_content.split('\n\n')
            current_chunk = ""
            chunk_index = 0

            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) > 1000:
                    if current_chunk:
                        chunks.append({
                            'content': current_chunk.strip(),
                            'metadata': {
                                **(metadata or {}),
                                'chunk_index': chunk_index,
                                'fallback_processing': True,
                                'content_type': content_type
                            },
                            'content_hash': hashlib.sha256(current_chunk.encode()).hexdigest()
                        })
                        chunk_index += 1
                    current_chunk = paragraph
                else:
                    current_chunk += "\n\n" + paragraph if current_chunk else paragraph

            if current_chunk:
                chunks.append({
                    'content': current_chunk.strip(),
                    'metadata': {
                        **(metadata or {}),
                        'chunk_index': chunk_index,
                        'fallback_processing': True,
                        'content_type': content_type
                    },
                    'content_hash': hashlib.sha256(current_chunk.encode()).hexdigest()
                })

            return {
                'success': True,
                'total_chunks': len(chunks),
                'chunks': chunks,
                'processing_metadata': {
                    'langchain_used': False,
                    'fallback_processing': True,
                    'content_type': content_type,
                    'total_chunks': len(chunks)  # Add for test compatibility
                }
            }

        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_metadata': {
                    'langchain_used': False,
                    'fallback_processing': True,
                    'error_occurred': True
                }
            }

    def _get_splitting_strategy_name(self, content_type: str, doc_type: str = None) -> str:
        """Get human-readable name for splitting strategy used"""
        effective_type = doc_type or content_type

        if effective_type == 'markdown':
            return 'markdown_header_aware'
        elif effective_type in ['html', 'web_profile']:
            return 'html_structure_aware'
        elif effective_type in ['source_code', 'technical']:
            return 'recursive_semantic'
        else:
            return 'adaptive_recursive'

    async def get_github_repo_stats(self, repo_url: str) -> Dict[str, Any]:
        """
        Fetch GitHub repository statistics via API.

        Returns:
            Dict with stars, commits, contributors, languages, topics, etc.
        """
        import requests
        import os

        try:
            parts = repo_url.strip('/').split('/')
            if len(parts) >= 2:
                owner = parts[-2]
                repo = parts[-1]

                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                headers = {}

                github_token = os.environ.get('GITHUB_TOKEN') or getattr(settings, 'GITHUB_TOKEN', '')
                if github_token:
                    headers['Authorization'] = f"token {github_token}"

                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    repo_data = response.json()

                    # Get languages
                    languages_url = repo_data.get('languages_url')
                    languages = {}
                    if languages_url:
                        lang_response = requests.get(languages_url, headers=headers, timeout=10)
                        if lang_response.status_code == 200:
                            languages = lang_response.json()

                    # Get contributors count
                    contributors_count = 0
                    contributors_url = repo_data.get('contributors_url')
                    if contributors_url:
                        try:
                            contrib_response = requests.get(contributors_url, headers=headers, timeout=10)
                            if contrib_response.status_code == 200:
                                contributors = contrib_response.json()
                                contributors_count = len(contributors) if isinstance(contributors, list) else 0
                        except Exception:
                            pass

                    # Get last commit date
                    last_commit_date = repo_data.get('pushed_at') or repo_data.get('updated_at')

                    return {
                        'name': repo_data.get('name'),
                        'description': repo_data.get('description'),
                        'language': repo_data.get('language'),
                        'languages': languages,
                        'stars': repo_data.get('stargazers_count', 0),
                        'forks': repo_data.get('forks_count', 0),
                        'contributors_count': contributors_count,
                        'contributors': contributors_count,  # Alias for test compatibility
                        'last_commit_date': last_commit_date,
                        'created_at': repo_data.get('created_at'),
                        'updated_at': repo_data.get('updated_at'),
                        'topics': repo_data.get('topics', []),
                        'default_branch': repo_data.get('default_branch'),
                        'size': repo_data.get('size'),
                        'open_issues': repo_data.get('open_issues_count', 0)
                    }
                elif response.status_code == 403:
                    # Rate limit or forbidden
                    return {'error': 'GitHub API rate limit exceeded or forbidden', 'stars': 0, 'forks': 0}
                elif response.status_code == 404:
                    # Repository not found
                    return {'error': 'Repository not found', 'stars': 0, 'forks': 0}
                else:
                    return {'error': f'GitHub API returned status {response.status_code}', 'stars': 0, 'forks': 0}

        except Exception as e:
            logger.error(f"Error fetching GitHub stats for {repo_url}: {e}")
            return {'error': str(e)}

    async def extract_pdf_basic_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract PDF metadata without LLM (fast extraction).

        Returns:
            Dict with title, author, page_count, creation_date, file_size, has_images, has_tables
        """
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            logger.warning("PyPDF2 not available, using fallback")
            return {'error': 'PyPDF2 not installed', 'page_count': 0, 'file_size': 0}

        import os

        try:
            # Handle both storage paths and absolute file paths
            if default_storage.exists(file_path):
                with default_storage.open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    file_size = file.size if hasattr(file, 'size') else 0
            elif os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    file_size = os.path.getsize(file_path)
            else:
                return {'error': 'File not found', 'page_count': 0, 'file_size': 0}

            metadata = reader.metadata if reader.metadata else {}

            extracted = {
                'title': metadata.get('/Title', '') if metadata else '',
                'author': metadata.get('/Author', '') if metadata else '',
                'subject': metadata.get('/Subject', '') if metadata else '',
                'creator': metadata.get('/Creator', '') if metadata else '',
                'producer': metadata.get('/Producer', '') if metadata else '',
                'creation_date': str(metadata.get('/CreationDate', '')) if metadata else '',
                'modification_date': str(metadata.get('/ModDate', '')) if metadata else '',
                'page_count': len(reader.pages),
                'file_size': file_size,
                'has_images': False,
                'has_tables': False
            }

            # Check for images and tables (basic heuristics)
            if reader.pages:
                first_page = reader.pages[0]
                first_page_text = first_page.extract_text()
                extracted['first_page_text'] = first_page_text[:1000] if first_page_text else ''

                # Check if page has images (simplified check)
                if hasattr(first_page, 'images') and first_page.images:
                    extracted['has_images'] = True

                # Check for table-like structure (look for tab characters or pipe characters)
                if first_page_text and any(indicator in first_page_text for indicator in ['\t', '|', '─']):
                    extracted['has_tables'] = True

            return extracted
        except Exception as e:
            logger.error(f"Error extracting PDF metadata from {file_path}: {e}")
            return {'error': str(e), 'page_count': 0, 'file_size': 0}

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics and configuration"""
        return {
            'langchain_available': HAS_LANGCHAIN,
            'configuration': self.config,
            'supported_formats': [
                'pdf', 'markdown', 'html', 'text', 'github'
            ],
            'splitting_strategies': [
                'recursive_character',
                'character_based',
                'markdown_header_aware',
                'html_structure_aware',
                'adaptive_semantic'
            ],
            'max_chunks_per_document': self._service_config.get('max_chunks_per_document', 50),
            'default_chunk_size': self._service_config.get('chunk_size', 1000),
            'default_chunk_overlap': self._service_config.get('chunk_overlap', 200)
        }