"""
Universal database builder for all modules.
Builds or rebuilds vector databases for all configured modules.
"""

import sys
import os
import argparse
from typing import List

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from rag.config import MODULES, get_module_config, load_module_settings
from rag.rag_langchain import (
    load_documents, 
    split_documents, 
    calculate_chunk_ids
)
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import shutil


def build_module_database(module_name: str, reset: bool = False, show_chunks: bool = False) -> bool:
    """
    Build the vector database for a specific module.
    
    Args:
        module_name: Name of the module to build
        reset: If True, clear existing database before building
        show_chunks: If True, display the content of each chunk
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\n{'='*60}")
        print(f"Building database for: {module_name}")
        print(f"{'='*60}")
        
        # Get module configuration and settings
        module_config = get_module_config(module_name)
        module_settings = load_module_settings(module_name)
        chroma_path = module_config["chroma_path"]
        data_path = module_config["data_path"]
        description = module_config["description"]
        
        print(f"Description: {description}")
        print(f"Data path: {data_path}")
        print(f"Chroma path: {chroma_path}")
        
        # Display module-specific settings
        print(f"Settings: LLM={module_settings.LLM_MODEL}, "
              f"TopK={module_settings.SIMILARITY_TOP_K}, "
              f"Reranking={'ON' if module_settings.ENABLE_RERANKING else 'OFF'}")
        
        # Check if data path exists
        if not os.path.exists(data_path):
            print(f"⚠️  Warning: Data path does not exist: {data_path}")
            print("   Creating directory...")
            os.makedirs(data_path, exist_ok=True)
            print(f"   Please add .md files to {data_path} and run again.")
            return False
        
        # Clear existing database if reset is True
        if reset and os.path.exists(chroma_path):
            print(f"🗑️  Removing existing database at {chroma_path}")
            shutil.rmtree(chroma_path)
        
        # Temporarily override the module paths in rag_langchain
        import rag.rag_langchain as rag_module
        original_data_path = rag_module.DATA_PATH
        original_chroma_path = rag_module.CHROMA_PATH
        
        rag_module.DATA_PATH = data_path
        rag_module.CHROMA_PATH = chroma_path
        
        try:
            # Load documents
            print("📄 Loading documents...")
            documents = load_documents()
            
            if not documents:
                print(f"⚠️  No documents found in {data_path}")
                print("   Please add .md files to this directory.")
                return False
            
            print(f"✓ Loaded {len(documents)} document(s)")
            
            # Split documents into chunks (using module-specific settings)
            print("✂️  Splitting documents into chunks...")
            chunks = split_documents(documents, module_settings)
            
            # Calculate chunk IDs
            print("🔢 Calculating chunk IDs...")
            chunks_with_ids = calculate_chunk_ids(chunks)
            
            # Display chunks if requested
            if show_chunks:
                print("\n" + "-"*60)
                print("📋 CHUNK DETAILS")
                print("-"*60)
                for i, chunk in enumerate(chunks_with_ids, 1):
                    print(f"\n{'='*60}")
                    print(f"CHUNK {i}/{len(chunks_with_ids)}")
                    print(f"{'='*60}")
                    print(f"ID: {chunk.metadata.get('id', 'N/A')}")
                    print(f"Source: {chunk.metadata.get('source', 'N/A')}")
                    print(f"Section: {chunk.metadata.get('section_header', 'N/A')}")
                    print(f"Hierarchy: {chunk.metadata.get('hierarchy', 'N/A')}")
                    print(f"Level: {chunk.metadata.get('level', 'N/A')}")
                    print(f"Size: {len(chunk.page_content)} chars")
                    print("-"*60)
                    print("CONTENT:")
                    print("-"*60)
                    print(chunk.page_content)
                print("\n" + "-"*60 + "\n")
            
            # Generate chunks.txt file in chroma folder
            print("📝 Generating chunks.txt...")
            os.makedirs(chroma_path, exist_ok=True)
            chunks_file_path = os.path.join(chroma_path, "chunks.txt")
            with open(chunks_file_path, 'w', encoding='utf-8') as f:
                f.write(f"CHUNKS FOR MODULE: {module_name}\n")
                f.write(f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total chunks: {len(chunks_with_ids)}\n")
                f.write("=" * 60 + "\n\n")
                
                for i, chunk in enumerate(chunks_with_ids, 1):
                    f.write(f"{'=' * 60}\n")
                    f.write(f"CHUNK {i}/{len(chunks_with_ids)}\n")
                    f.write(f"{'=' * 60}\n")
                    f.write(f"ID: {chunk.metadata.get('id', 'N/A')}\n")
                    f.write(f"Source: {chunk.metadata.get('source', 'N/A')}\n")
                    f.write(f"Section: {chunk.metadata.get('section_header', 'N/A')}\n")
                    f.write(f"Hierarchy: {chunk.metadata.get('hierarchy', 'N/A')}\n")
                    f.write(f"Level: {chunk.metadata.get('level', 'N/A')}\n")
                    f.write(f"Size: {len(chunk.page_content)} chars\n")
                    f.write("-" * 60 + "\n")
                    f.write("CONTENT:\n")
                    f.write("-" * 60 + "\n")
                    f.write(chunk.page_content + "\n\n")
            
            print(f"   Saved to: {chunks_file_path}")
            
            # Create or update database (using module-specific settings)
            print("💾 Creating vector database...")
            db = Chroma(
                persist_directory=chroma_path,
                embedding_function=OllamaEmbeddings(model=module_settings.EMBEDDING_MODEL),
                collection_metadata={"hnsw:space": module_settings.DISTANCE_METRIC}
            )
            
            # Check for existing chunks
            existing_items = db.get(include=[])
            existing_ids = set(existing_items["ids"])
            
            if existing_ids and not reset:
                print(f"📊 Existing chunks in database: {len(existing_ids)}")
                # Filter out chunks that already exist
                new_chunks = [
                    chunk for chunk in chunks_with_ids
                    if chunk.metadata["id"] not in existing_ids
                ]
                
                if new_chunks:
                    print(f"➕ Adding {len(new_chunks)} new chunk(s)...")
                    chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
                    db.add_documents(new_chunks, ids=chunk_ids)
                else:
                    print("✓ Database is already up to date")
            else:
                # Add all chunks
                print(f"➕ Adding {len(chunks_with_ids)} chunk(s) to database...")
                chunk_ids = [chunk.metadata["id"] for chunk in chunks_with_ids]
                db.add_documents(chunks_with_ids, ids=chunk_ids)
            
            print(f"✅ Database for '{module_name}' built successfully!")
            print(f"   Total chunks: {len(chunks_with_ids)}")
            return True
            
        finally:
            # Restore original paths
            rag_module.DATA_PATH = original_data_path
            rag_module.CHROMA_PATH = original_chroma_path
            
    except Exception as e:
        print(f"❌ Error building database for '{module_name}': {e}")
        import traceback
        traceback.print_exc()
        return False


def build_all_modules(reset: bool = False, modules: List[str] = None, show_chunks: bool = False) -> None:
    """
    Build databases for all modules or specified modules.
    
    Args:
        reset: If True, clear existing databases before building
        modules: List of specific module names to build. If None, builds all.
        show_chunks: If True, display the content of each chunk
    """
    print("\n" + "="*60)
    print("UNIVERSAL DATABASE BUILDER")
    print("="*60)
    
    # Determine which modules to build
    if modules:
        # Validate specified modules
        invalid_modules = [m for m in modules if m not in MODULES]
        if invalid_modules:
            print(f"❌ Error: Invalid module(s): {', '.join(invalid_modules)}")
            print(f"   Available modules: {', '.join(MODULES.keys())}")
            sys.exit(1)
        modules_to_build = modules
    else:
        modules_to_build = list(MODULES.keys())
    
    print(f"\nModules to build: {', '.join(modules_to_build)}")
    print(f"Reset mode: {'ON (will clear existing databases)' if reset else 'OFF (incremental update)'}")
    print(f"Show chunks: {'ON' if show_chunks else 'OFF'}")
    
    # Build each module
    results = {}
    for module_name in modules_to_build:
        success = build_module_database(module_name, reset=reset, show_chunks=show_chunks)
        results[module_name] = success
    
    # Print summary
    print("\n" + "="*60)
    print("BUILD SUMMARY")
    print("="*60)
    
    for module_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status} - {module_name}")
    
    # Overall result
    all_success = all(results.values())
    if all_success:
        print("\n🎉 All modules built successfully!")
    else:
        failed_modules = [m for m, s in results.items() if not s]
        print(f"⚠️  Some modules failed: {', '.join(failed_modules)}")
        sys.exit(1)


def list_modules() -> None:
    """List all available modules and their status."""
    print("\n" + "="*60)
    print("AVAILABLE MODULES")
    print("="*60 + "\n")
    
    for module_name, config in MODULES.items():
        print(f"📦 {module_name}")
        print(f"   Description: {config['description']}")
        print(f"   Data path: {config['data_path']}")
        print(f"   Chroma path: {config['chroma_path']}")
        
        # Check status
        data_exists = os.path.exists(config['data_path'])
        db_exists = os.path.exists(config['chroma_path'])
        
        if data_exists:
            md_files = [f for f in os.listdir(config['data_path']) if f.endswith('.md')]
            print(f"   Data files: {len(md_files)} .md file(s)")
        else:
            print("   Data files: ⚠️  Directory not found")
        
        if db_exists:
            print("   Database: ✅ Built")
        else:
            print("   Database: ⚠️  Not built")
        
        print()


def main():
    """Main entry point for the universal database builder."""
    parser = argparse.ArgumentParser(
        description="Universal database builder for all RAG modules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build all modules (incremental update)
  python build_all_modules.py
  
  # Rebuild all modules from scratch
  python build_all_modules.py --reset
  
  # Build specific modules only
  python build_all_modules.py --modules module_a module_b
  
  # Rebuild specific module
  python build_all_modules.py --reset --modules module_a
  
  # List all available modules
  python build_all_modules.py --list
  
  # Build and show all chunk contents
  python build_all_modules.py --reset --show-chunks
  
  # Show chunks for a specific module
  python build_all_modules.py --reset --modules module_c --show-chunks
        """
    )
    
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing databases before building"
    )
    
    parser.add_argument(
        "--modules",
        nargs="+",
        metavar="MODULE",
        help="Specific module(s) to build (default: all modules)"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available modules and their status"
    )
    
    parser.add_argument(
        "--show-chunks",
        action="store_true",
        help="Display the content of each chunk during build"
    )
    
    args = parser.parse_args()
    
    try:
        if args.list:
            list_modules()
        else:
            build_all_modules(reset=args.reset, modules=args.modules, show_chunks=args.show_chunks)
    except KeyboardInterrupt:
        print("\n\n⚠️  Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

