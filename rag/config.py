"""
Configuration for RAG modules.
This allows easy switching between different modules.
Each module can have its own configuration and prompt template.
"""

import os
import importlib.util

# Current active module
ACTIVE_MODULE = "module_b"

# Module configurations (paths and descriptions)
MODULES = {
    "module_b": {
        "chroma_path": "modules/module_b/chroma",
        "data_path": "modules/module_b/files",
        "description": "Module B - Civil 3D Command Knowledge Base"
    },
    "module_c": {
        "chroma_path": "modules/module_c/chroma",
        "data_path": "modules/module_c/files",
        "description": "Module C - ISO 19650 Knowledge Master"
    },
}

def get_module_config(module_name=None):
    """
    Get basic configuration for a specific module (paths and description).
    
    Args:
        module_name: Name of the module. If None, uses ACTIVE_MODULE.
        
    Returns:
        Dictionary with module configuration
    """
    if module_name is None:
        module_name = ACTIVE_MODULE
    
    if module_name not in MODULES:
        raise ValueError(f"Module '{module_name}' not found. Available modules: {list(MODULES.keys())}")
    
    return MODULES[module_name]


def load_module_settings(module_name):
    """
    Load module-specific settings (config.py) from the module directory.
    Falls back to default values if module config doesn't exist.
    
    Args:
        module_name: Name of the module
        
    Returns:
        Module settings object with all configuration attributes
    """
    module_path = f"modules/{module_name}/config.py"
    
    if os.path.exists(module_path):
        # Dynamically import the module's config
        spec = importlib.util.spec_from_file_location(f"{module_name}_config", module_path)
        module_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module_config)
        return module_config
    else:
        # Return default settings if module config doesn't exist
        class DefaultSettings:
            LLM_MODEL = "llama3.1"
            EMBEDDING_MODEL = "nomic-embed-text"
            SIMILARITY_TOP_K = 5
            DISTANCE_METRIC = "l2"
            ENABLE_RERANKING = False
            RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            RERANK_TOP_K = 20
            MAX_CHUNK_SIZE = 1000
            MIN_CHUNK_SIZE = 200
            PRESERVE_CONTEXT_LINES = 1
            MODULE_NAME = module_name
            MODULE_DESCRIPTION = f"Module {module_name}"
        
        return DefaultSettings()


def load_module_prompt(module_name):
    """
    Load module-specific prompt template from the module directory.
    Falls back to default prompt if module prompt doesn't exist.
    
    Args:
        module_name: Name of the module (if None, returns default prompt)
        
    Returns:
        Prompt template string
    """
    # If no module specified, return default prompt
    if module_name is None:
        return """
Answer the question based ONLY on the following context:

{context}

{conversation_history}

Current Question: {question}

Instructions:
- Answer the question based on the provided context
- If there is conversation history above, use it to understand context and follow-up questions
- If the context doesn't contain enough information, say you don't know
- Do NOT make assumptions or include information not in the context
- When answering follow-up questions, refer back to previous exchanges when relevant
"""
    
    module_path = f"modules/{module_name}/prompt_template.py"
    
    if os.path.exists(module_path):
        # Dynamically import the module's prompt template
        spec = importlib.util.spec_from_file_location(f"{module_name}_prompt", module_path)
        module_prompt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module_prompt)
        return module_prompt.PROMPT_TEMPLATE
    else:
        # Return default prompt if module prompt doesn't exist
        return """
Answer the question based ONLY on the following context:

{context}

{conversation_history}

Current Question: {question}

Instructions:
- Answer the question based on the provided context
- If there is conversation history above, use it to understand context and follow-up questions
- If the context doesn't contain enough information, say you don't know
- Do NOT make assumptions or include information not in the context
- When answering follow-up questions, refer back to previous exchanges when relevant
"""

