"""
Flask web application for the RAG chatbot.
Provides a web interface for conversational interactions with the RAG system.
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
import sys
import secrets
from datetime import datetime

# Add parent directory to path to import from rag folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rag.rag_langchain import query_rag
from rag.config import get_module_config, MODULES

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

# Store conversation history in memory (in production, use a database)
conversations = {}


@app.route('/')
def index():
    """Render the main chat interface."""
    return render_template('index.html')


@app.route('/api/files', methods=['GET'])
def get_files():
    """Get list of files in the data directory."""
    try:
        module_name = request.args.get('module', 'module_a')
        module_config = get_module_config(module_name)
        data_path = module_config['data_path']
        
        if not os.path.exists(data_path):
            return jsonify({'files': []})
        
        files = []
        for filename in os.listdir(data_path):
            if filename.endswith('.md'):
                file_path = os.path.join(data_path, filename)
                file_stats = os.stat(file_path)
                files.append({
                    'name': filename,
                    'size': file_stats.st_size,
                    'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                })
        
        # Sort by name
        files.sort(key=lambda x: x['name'])
        
        return jsonify({'files': files})
    
    except Exception as e:
        print(f"Error getting files: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat messages and return RAG responses.
    Maintains conversation history in the session.
    """
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        module_name = data.get('module', 'module_a')
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get module configuration
        module_config = get_module_config(module_name)
        chroma_path = module_config['chroma_path']
        
        # Check if database exists
        if not os.path.exists(chroma_path):
            return jsonify({
                'error': f'Database not found for {module_name}. Please build the database first.'
            }), 500
        
        # Get or create session ID with module context
        session_key = f'session_id_{module_name}'
        if session_key not in session:
            session[session_key] = secrets.token_hex(8)
        
        session_id = session[session_key]
        
        # Initialize conversation history for this session and module
        conversation_key = f"{session_id}_{module_name}"
        if conversation_key not in conversations:
            conversations[conversation_key] = []
        
        # Get existing conversation history (without current message)
        # Pass only the content and role, not timestamps
        history_for_rag = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in conversations[conversation_key]
        ]
        
        # Query the RAG system with module context and conversation history
        response = query_rag(
            user_message, 
            debug=False, 
            module_name=module_name,
            conversation_history=history_for_rag
        )
        
        # Add user message to history (after querying, so it's not in the history passed to RAG)
        conversations[conversation_key].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Add assistant response to history
        conversations[conversation_key].append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'response': response,
            'session_id': session_id
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history for the current session."""
    try:
        module_name = request.args.get('module', 'module_a')
        session_key = f'session_id_{module_name}'
        session_id = session.get(session_key)
        
        if not session_id:
            return jsonify({'history': []})
        
        conversation_key = f"{session_id}_{module_name}"
        if conversation_key not in conversations:
            return jsonify({'history': []})
        
        return jsonify({'history': conversations[conversation_key]})
    
    except Exception as e:
        print(f"Error getting history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear conversation history for the current session."""
    try:
        data = request.json or {}
        module_name = data.get('module', 'module_a')
        session_key = f'session_id_{module_name}'
        session_id = session.get(session_key)
        
        if session_id:
            conversation_key = f"{session_id}_{module_name}"
            if conversation_key in conversations:
                conversations[conversation_key] = []
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"Error clearing history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Check if the RAG system is ready."""
    module_name = request.args.get('module', 'module_a')
    try:
        module_config = get_module_config(module_name)
        chroma_path = module_config['chroma_path']
        db_exists = os.path.exists(chroma_path)
        return jsonify({
            'status': 'ready' if db_exists else 'not_ready',
            'database_exists': db_exists,
            'module': module_name
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/modules', methods=['GET'])
def get_modules():
    """Get list of available modules."""
    return jsonify({
        'modules': [
            {
                'id': module_id,
                'description': config['description']
            }
            for module_id, config in MODULES.items()
        ]
    })


if __name__ == '__main__':
    # Get the directory where app.py is located
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create templates directory if it doesn't exist
    os.makedirs(os.path.join(app_dir, 'templates'), exist_ok=True)
    os.makedirs(os.path.join(app_dir, 'static'), exist_ok=True)
    
    print(f"🤖 Multi-Module RAG Chatbot | Server: http://localhost:5000")
    for module_id, config in MODULES.items():
        db_status = "Ready" if os.path.exists(config['chroma_path']) else "Not found"
        print(f"   - {module_id}: {db_status}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

