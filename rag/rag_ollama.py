from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.prompts import PromptTemplate

from .config import get_module_config, load_module_prompt

# Load default prompt template
PROMPT_TEMPLATE = load_module_prompt(None)


def configure_settings(
    model="llama2",
    embed_model="nomic-embed-text",
    chunk_size=1024,
    chunk_overlap=20,
    request_timeout=120.0
):
    """Configure global LlamaIndex settings."""
    Settings.llm = Ollama(model=model, request_timeout=request_timeout)
    Settings.embed_model = OllamaEmbedding(model_name=embed_model)
    Settings.chunk_size = chunk_size
    Settings.chunk_overlap = chunk_overlap


def load_documents(directory_path):
    """Load documents from the specified directory."""
    documents = SimpleDirectoryReader(directory_path).load_data()
    print(f"Loaded {len(documents)} document(s) from {directory_path}")
    return documents


def create_vector_index(documents):
    """Create a vector index from documents."""
    vector_index = VectorStoreIndex.from_documents(documents)
    return vector_index


def get_qa_prompt_template():
    """Define and return the custom prompt template for the query engine."""
    # Convert LangChain format to LlamaIndex format
    llamaindex_template = PROMPT_TEMPLATE.replace("{context}", "{context_str}").replace("{question}", "{query_str}")
    return PromptTemplate(template=llamaindex_template)


def create_query_engine(vector_index, similarity_top_k=3):
    """Create a query engine with custom prompt template."""
    qa_prompt_template = get_qa_prompt_template()
    query_engine = vector_index.as_query_engine(
        similarity_top_k=similarity_top_k,
        text_qa_template=qa_prompt_template
    )
    return query_engine


def print_response(query, response):
    """Print the query response in a formatted way."""
    print(f"\nQUERY: {query}")
    print(f"RESPONSE: {response}")


def print_source_nodes(response):
    """Print the source nodes (retrieved context) from the response."""
    print("\nSOURCES:")
    for i, node in enumerate(response.source_nodes, 1):
        preview = node.text[:200] + "..." if len(node.text) > 200 else node.text
        print(f"  [{i}] Score: {node.score:.4f} | {preview}")


def query_documents(query_engine, query):
    """Execute a query and return the response."""
    response = query_engine.query(query)
    return response


def main():
    """Main function to run the RAG system."""
    # Configure settings
    configure_settings()
    
    # Load documents
    module_config = get_module_config()
    documents_path = module_config["data_path"]
    documents = load_documents(documents_path)
    
    # Create vector index
    vector_index = create_vector_index(documents)
    
    # Create query engine
    query_engine = create_query_engine(vector_index, similarity_top_k=3)
    
    # Execute query
    query = "Who has Revit skills in their software list? I need someone who can work on a Revit project."
    response = query_documents(query_engine, query)
    
    # Print results
    print_response(query, response)
    print_source_nodes(response)


if __name__ == "__main__":
    main()
