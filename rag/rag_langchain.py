"""
RAG (Retrieval-Augmented Generation) system using LangChain and Ollama.
Processes Markdown files and creates a vector database for semantic search.
"""

import argparse
import os
import shutil
from typing import List

from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from sentence_transformers import CrossEncoder

from .config import get_module_config, load_module_settings, load_module_prompt

# Get default module configuration (for backward compatibility)
module_config = get_module_config()
CHROMA_PATH = module_config["chroma_path"]
DATA_PATH = module_config["data_path"]

# Default settings (can be overridden by module-specific configs)
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.1"
SIMILARITY_TOP_K = 5
DISTANCE_METRIC = "l2"
ENABLE_RERANKING = False
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_K = 20
MAX_CHUNK_SIZE = 1000
MIN_CHUNK_SIZE = 200
PRESERVE_CONTEXT_LINES = 1


def load_documents() -> List[Document]:
    """
    Load all Markdown files from the data directory and convert them to Documents.
    
    Returns:
        List of Document objects
    """
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Data path '{DATA_PATH}' does not exist.")
    
    documents = []
    
    # Get all Markdown files
    all_files = os.listdir(DATA_PATH)
    md_files = [f for f in all_files if f.endswith('.md')]
    
    if not md_files:
        print(f"Warning: No Markdown files found in '{DATA_PATH}'")
        return documents
    
    # Process Markdown files
    for md_file in md_files:
        file_path = os.path.join(DATA_PATH, md_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": md_file,
                        "type": "markdown"
                    }
                )
                documents.append(doc)
                print(f"Loaded 1 document from {md_file}")
        except Exception as e:
            print(f"Error loading file {md_file}: {e}")
    
    return documents


def parse_markdown_structure(content: str) -> List[dict]:
    """
    Parse markdown content into a hierarchical structure of sections.
    
    Args:
        content: The markdown content to parse
        
    Returns:
        List of dictionaries containing section information
    """
    lines = content.split('\n')
    sections = []
    current_section = {
        'level': 0,
        'title': '',
        'content': [],
        'line_start': 0,
        'parent_headers': []
    }
    header_stack = []  # Track header hierarchy for context
    
    for i, line in enumerate(lines):
        # Detect headers (# to ######)
        if line.strip().startswith('#') and not line.strip().startswith('#####'):
            # Save previous section if it has content
            if current_section['content']:
                sections.append(current_section.copy())
            
            # Determine header level
            level = len(line) - len(line.lstrip('#'))
            title = line.lstrip('#').strip()
            
            # Update header stack for context tracking
            header_stack = [h for h in header_stack if h['level'] < level]
            header_stack.append({'level': level, 'title': title})
            
            # Start new section
            current_section = {
                'level': level,
                'title': title,
                'content': [line],
                'line_start': i,
                'parent_headers': [h['title'] for h in header_stack[:-1]]  # Exclude current header
            }
        else:
            current_section['content'].append(line)
    
    # Add the last section
    if current_section['content']:
        sections.append(current_section)
    
    return sections


def split_large_section(section: dict, source: str, section_index: int, 
                        max_chunk_size: int = None, min_chunk_size: int = None,
                        preserve_context_lines: int = None) -> List[Document]:
    """
    Split a large section into smaller chunks while preserving context.
    Uses intelligent splitting at paragraph boundaries, lists, and code blocks.
    
    Args:
        section: Dictionary containing section information
        source: The source filename
        section_index: Index of the section
        max_chunk_size: Maximum chunk size (uses global default if None)
        min_chunk_size: Minimum chunk size (uses global default if None)
        preserve_context_lines: Context lines to preserve (uses global default if None)
        
    Returns:
        List of Document objects
    """
    # Use provided values or fall back to globals
    _max_chunk = max_chunk_size if max_chunk_size is not None else MAX_CHUNK_SIZE
    _min_chunk = min_chunk_size if min_chunk_size is not None else MIN_CHUNK_SIZE
    _preserve_ctx = preserve_context_lines if preserve_context_lines is not None else PRESERVE_CONTEXT_LINES
    
    content = '\n'.join(section['content'])
    chunks = []
    
    # Build context header from parent headers
    context_headers = []
    if section['parent_headers']:
        context_headers = section['parent_headers'][-_preserve_ctx:]
    
    # If section is small enough, return as single chunk
    if len(content) <= _max_chunk:
        full_content = content
        if context_headers:
            context_str = ' > '.join(context_headers) + ' > ' + section['title']
        else:
            context_str = section['title']
            
        doc = Document(
            page_content=full_content,
            metadata={
                "source": source,
                "type": "markdown_section",
                "section_header": section['title'],
                "section_index": section_index,
                "chunk_index": 0,
                "hierarchy": context_str,
                "level": section['level']
            }
        )
        return [doc]
    
    # Split large sections intelligently
    lines = section['content']
    current_chunk = []
    current_size = 0
    chunk_index = 0
    header_line = lines[0] if lines and lines[0].strip().startswith('#') else None
    
    # Always include the section header in each chunk
    if header_line:
        lines = lines[1:]  # Remove header from lines to process
    
    for line in lines:
        line_size = len(line) + 1  # +1 for newline
        
        # Check if adding this line would exceed max size
        if current_size + line_size > _max_chunk and current_chunk:
            # Check if we've met minimum chunk size
            if current_size >= _min_chunk:
                # Create chunk with header
                chunk_lines = [header_line] + current_chunk if header_line else current_chunk
                chunk_content = '\n'.join(chunk_lines).strip()
                
                if context_headers:
                    context_str = ' > '.join(context_headers) + ' > ' + section['title']
                else:
                    context_str = section['title']
                
                doc = Document(
                    page_content=chunk_content,
                    metadata={
                        "source": source,
                        "type": "markdown_section",
                        "section_header": section['title'],
                        "section_index": section_index,
                        "chunk_index": chunk_index,
                        "hierarchy": context_str,
                        "level": section['level']
                    }
                )
                chunks.append(doc)
                chunk_index += 1
                current_chunk = []
                current_size = 0
        
        current_chunk.append(line)
        current_size += line_size
        
        # Smart splitting points: empty lines (paragraph breaks)
        if not line.strip() and current_size >= _min_chunk:
            chunk_lines = [header_line] + current_chunk if header_line else current_chunk
            chunk_content = '\n'.join(chunk_lines).strip()
            
            if chunk_content:  # Only create chunk if there's actual content
                if context_headers:
                    context_str = ' > '.join(context_headers) + ' > ' + section['title']
                else:
                    context_str = section['title']
                
                doc = Document(
                    page_content=chunk_content,
                    metadata={
                        "source": source,
                        "type": "markdown_section",
                        "section_header": section['title'],
                        "section_index": section_index,
                        "chunk_index": chunk_index,
                        "hierarchy": context_str,
                        "level": section['level']
                    }
                )
                chunks.append(doc)
                chunk_index += 1
                current_chunk = []
                current_size = 0
    
    # Add remaining content as final chunk
    if current_chunk:
        chunk_lines = [header_line] + current_chunk if header_line else current_chunk
        chunk_content = '\n'.join(chunk_lines).strip()
        
        if chunk_content:
            if context_headers:
                context_str = ' > '.join(context_headers) + ' > ' + section['title']
            else:
                context_str = section['title']
            
            doc = Document(
                page_content=chunk_content,
                metadata={
                    "source": source,
                    "type": "markdown_section",
                    "section_header": section['title'],
                    "section_index": section_index,
                    "chunk_index": chunk_index,
                    "hierarchy": context_str,
                    "level": section['level']
                }
            )
            chunks.append(doc)
    
    return chunks


def hybrid_markdown_chunking(content: str, source: str,
                            max_chunk_size: int = None, min_chunk_size: int = None,
                            preserve_context_lines: int = None) -> List[Document]:
    """
    Hybrid chunking strategy for markdown files.
    - Respects document structure (headers, sections)
    - Intelligently splits large sections at paragraph boundaries
    - Preserves hierarchical context in each chunk
    - Handles various markdown elements (lists, code blocks, etc.)
    
    Args:
        content: The markdown content to chunk
        source: The source filename
        max_chunk_size: Maximum chunk size (uses global default if None)
        min_chunk_size: Minimum chunk size (uses global default if None)
        preserve_context_lines: Context lines to preserve (uses global default if None)
        
    Returns:
        List of Document objects with intelligent chunking
    """
    # Parse markdown into structured sections
    sections = parse_markdown_structure(content)
    
    all_chunks = []
    section_index = 0
    
    for section in sections:
        # Split large sections, keep small ones intact
        section_chunks = split_large_section(
            section, source, section_index,
            max_chunk_size, min_chunk_size, preserve_context_lines
        )
        all_chunks.extend(section_chunks)
        section_index += 1
    
    return all_chunks


def split_documents(documents: List[Document], module_settings=None) -> List[Document]:
    """
    Split markdown documents into smaller chunks for better retrieval.
    Uses hybrid chunking strategy to intelligently preserve structure
    while maintaining optimal chunk sizes.
    
    Args:
        documents: List of markdown documents to split
        module_settings: Module-specific settings object (optional)
        
    Returns:
        List of chunked documents
    """
    # Extract chunking parameters from module settings if provided
    max_chunk = module_settings.MAX_CHUNK_SIZE if module_settings else None
    min_chunk = module_settings.MIN_CHUNK_SIZE if module_settings else None
    preserve_ctx = module_settings.PRESERVE_CONTEXT_LINES if module_settings else None
    
    all_chunks = []
    
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        
        # Apply hybrid chunking with module-specific settings
        md_chunks = hybrid_markdown_chunking(
            doc.page_content, source,
            max_chunk, min_chunk, preserve_ctx
        )
        all_chunks.extend(md_chunks)
        
        # Calculate statistics
        avg_size = sum(len(chunk.page_content) for chunk in md_chunks) / len(md_chunks) if md_chunks else 0
        print(f"Chunked {source}: {len(md_chunks)} chunks, avg {avg_size:.0f} chars")
    
    print(f"Total: {len(documents)} documents → {len(all_chunks)} chunks")
    return all_chunks


def calculate_chunk_ids(chunks: List[Document]) -> List[Document]:
    """
    Calculate unique IDs for each chunk based on source and position.
    
    Args:
        chunks: List of document chunks
        
    Returns:
        List of chunks with IDs added to metadata
    """
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        section_index = chunk.metadata.get("section_index", 0)
        current_page_id = f"{source}:section:{section_index}"

        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id
        chunk.metadata["id"] = chunk_id

    return chunks


def create_or_update_database(reset: bool = False, module_name: str = None) -> None:
    """
    Create or update the vector database with documents.
    
    Args:
        reset: If True, clear existing database before adding documents
        module_name: Name of the module (if None, uses ACTIVE_MODULE)
    """
    # Load module-specific settings
    if module_name:
        module_config = get_module_config(module_name)
        module_settings = load_module_settings(module_name)
        chroma_path = module_config["chroma_path"]
        data_path = module_config["data_path"]
    else:
        module_settings = None
        chroma_path = CHROMA_PATH
        data_path = DATA_PATH
    
    if reset:
        if os.path.exists(chroma_path):
            shutil.rmtree(chroma_path)

    print("Loading documents...")
    # Temporarily override DATA_PATH for load_documents
    original_data_path = globals()['DATA_PATH']
    globals()['DATA_PATH'] = data_path
    
    try:
        documents = load_documents()
        
        if not documents:
            print("No documents to process.")
            return
        
        print("Splitting documents into chunks...")
        chunks = split_documents(documents, module_settings)
        
        print("Calculating chunk IDs...")
        chunks_with_ids = calculate_chunk_ids(chunks)

        print("Initializing vector database...")
        embedding_model = module_settings.EMBEDDING_MODEL if module_settings else EMBEDDING_MODEL
        distance_metric = module_settings.DISTANCE_METRIC if module_settings else DISTANCE_METRIC
        
        db = Chroma(
            persist_directory=chroma_path,
            embedding_function=OllamaEmbeddings(model=embedding_model),
            collection_metadata={"hnsw:space": distance_metric}
        )
    finally:
        globals()['DATA_PATH'] = original_data_path

    # Get existing document IDs
    existing_items = db.get(include=[])
    existing_ids = set(existing_items["ids"])
    print(f"Existing chunks in database: {len(existing_ids)}")

    # Filter out chunks that already exist
    new_chunks = [
        chunk for chunk in chunks_with_ids
        if chunk.metadata["id"] not in existing_ids
    ]

    if new_chunks:
        print(f"Adding {len(new_chunks)} new chunks to database...")
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids)
        print("✓ Database updated successfully")
    else:
        print("✓ Database is up to date")


def clear_database() -> None:
    """Remove the existing vector database."""
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)


def rerank_results(query_text: str, results: List[tuple], debug: bool = False, reranker_model: str = None) -> List[tuple]:
    """
    Rerank search results using a cross-encoder model for better accuracy.
    
    Cross-encoders process the query and document together, providing more
    accurate relevance scores than bi-encoders (embeddings) alone.
    
    Args:
        query_text: The search query
        results: List of (document, score) tuples from initial search
        debug: If True, print reranking information
        reranker_model: Model to use for reranking (uses global default if None)
        
    Returns:
        Reranked list of (document, score) tuples with new relevance scores
    """
    if not results:
        return results
    
    model_name = reranker_model if reranker_model else RERANKER_MODEL
    
    if debug:
        print(f"[DEBUG] Reranking with {model_name}")
    
    # Initialize reranker model
    reranker = CrossEncoder(model_name)
    
    # Prepare query-document pairs for the cross-encoder
    pairs = [(query_text, doc.page_content) for doc, _score in results]
    
    # Get reranker scores (higher = more relevant)
    rerank_scores = reranker.predict(pairs)
    
    # Combine documents with new scores
    reranked = [
        (doc, float(score)) 
        for (doc, _old_score), score in zip(results, rerank_scores)
    ]
    
    # Sort by new scores (higher = more relevant for cross-encoder)
    reranked.sort(key=lambda x: x[1], reverse=True)
    
    return reranked


def query_rag(query_text: str, debug: bool = False, module_name: str = None, 
              conversation_history: List[dict] = None) -> str:
    """
    Query the RAG system with a question, optionally with conversation history.
    
    Args:
        query_text: The question to ask
        debug: If True, print debug information about retrieved chunks
        module_name: Name of the module to query (if None, uses default from config)
        conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
        
    Returns:
        The generated answer
    """
    # Load module-specific configuration and settings
    if module_name:
        module_config = get_module_config(module_name)
        module_settings = load_module_settings(module_name)
        module_prompt = load_module_prompt(module_name)
        chroma_path = module_config["chroma_path"]
        
        # Use module-specific settings
        embedding_model = module_settings.EMBEDDING_MODEL
        distance_metric = module_settings.DISTANCE_METRIC
        similarity_top_k = module_settings.SIMILARITY_TOP_K
        enable_reranking = module_settings.ENABLE_RERANKING
        reranker_model = module_settings.RERANKER_MODEL
        rerank_top_k = module_settings.RERANK_TOP_K
        llm_model = module_settings.LLM_MODEL
    else:
        chroma_path = CHROMA_PATH
        embedding_model = EMBEDDING_MODEL
        distance_metric = DISTANCE_METRIC
        similarity_top_k = SIMILARITY_TOP_K
        enable_reranking = ENABLE_RERANKING
        reranker_model = RERANKER_MODEL
        rerank_top_k = RERANK_TOP_K
        llm_model = LLM_MODEL
        # Use fallback prompt from config.py (which has a default)
        module_prompt = load_module_prompt(None)
    
    db = Chroma(
        persist_directory=chroma_path,
        embedding_function=OllamaEmbeddings(model=embedding_model),
        collection_metadata={"hnsw:space": distance_metric}
    )
    
    # Perform similarity search - get more results if reranking is enabled
    initial_k = rerank_top_k if enable_reranking else similarity_top_k
    results = db.similarity_search_with_score(query_text, k=initial_k)
    
    if not results:
        return "No relevant documents found in the database."
    
    # Debug output - initial results
    if debug and enable_reranking:
        print(f"\n[DEBUG] Initial: {len(results)} chunks retrieved for reranking")
        for i, (doc, score) in enumerate(results[:5], 1):
            print(f"  [{i}] {score:.4f} | {doc.metadata.get('section_header', 'N/A')[:50]}")
    
    # Rerank results if enabled
    if enable_reranking:
        results = rerank_results(query_text, results, debug=debug, reranker_model=reranker_model)
        # Take top K after reranking
        results = results[:similarity_top_k]
    
    # Debug output - final results
    if debug:
        result_type = "Reranked" if enable_reranking else "Retrieved"
        print(f"\n[DEBUG] {result_type} chunks:")
        for i, (doc, score) in enumerate(results, 1):
            section = doc.metadata.get('section_header', 'N/A')
            print(f"  [{i}] {score:.4f} | {section[:50]}")
    
    # Combine retrieved documents into context
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    
    # Build conversation history string if provided
    history_text = ""
    if conversation_history and len(conversation_history) > 0:
        # Limit to last 5 exchanges (10 messages) to avoid context overflow
        recent_history = conversation_history[-10:]
        history_lines = []
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {msg['content']}")
        history_text = "\n".join(history_lines)
    
    # Create prompt and query LLM
    prompt_template = ChatPromptTemplate.from_template(module_prompt)
    
    # Always pass conversation_history (empty string if no history)
    prompt = prompt_template.format(
        context=context_text, 
        question=query_text,
        conversation_history=history_text
    )
    
    model = OllamaLLM(model=llm_model)
    response_text = model.invoke(prompt)
    
    return response_text


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="RAG system for querying Markdown documents using LangChain and Ollama"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the existing database before building"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Query the RAG system with a question"
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build/update the vector database from Markdown files"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information about retrieved chunks"
    )
    
    args = parser.parse_args()
    
    # Build or reset database
    if args.build or args.reset:
        try:
            create_or_update_database(reset=args.reset)
        except Exception as e:
            print(f"Error building database: {e}")
            return
    
    # Query the system
    if args.query:
        if not os.path.exists(CHROMA_PATH):
            print(f"Error: Database not found at '{CHROMA_PATH}'. Please build the database first using --build.")
            return
        
        try:
            print(query_rag(args.query, debug=args.debug))
        except Exception as e:
            print(f"Error querying RAG system: {e}")
            return
    
    # Show help if no arguments provided
    if not (args.build or args.reset or args.query):
        parser.print_help()


if __name__ == "__main__":
    main()
