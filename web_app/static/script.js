// Chat application JavaScript
class ChatApp {
    constructor() {
        this.chatContainer = document.getElementById('chatContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.filesList = document.getElementById('filesList');
        this.isProcessing = false;
        this.currentModule = 'module_a';
        this.currentModuleName = 'ccGPT';
        this.currentThemeColor = 'rgba(220, 38, 38)';
        
        this.init();
    }

    init() {
        // Check system health
        this.checkHealth();
        
        // Load files list
        this.loadFiles();
        
        // Event listeners
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.clearBtn.addEventListener('click', () => this.clearConversation());
        
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });

        // Module icon click handlers
        document.querySelectorAll('.module-icon').forEach(icon => {
            icon.addEventListener('click', (e) => this.switchModule(e.currentTarget));
        });

        // Load conversation history
        this.loadHistory();
    }

    switchModule(iconElement) {
        const moduleId = iconElement.dataset.module;
        const moduleName = iconElement.dataset.moduleName;
        const themeColor = iconElement.dataset.themeColor;
        
        // Update active state
        document.querySelectorAll('.module-icon').forEach(icon => {
            icon.classList.remove('active');
        });
        iconElement.classList.add('active');
        
        this.currentModule = moduleId;
        this.currentModuleName = moduleName;
        this.currentThemeColor = themeColor;
        
        // Update theme
        document.body.setAttribute('data-theme', moduleId);
        
        // Update header
        this.updateHeader();
        
        // Clear and reload
        this.clearChatUI();
        this.checkHealth();
        this.loadFiles();
        this.loadHistory();
        
        console.log('Switched to module:', moduleId, moduleName);
    }

    updateHeader() {
        const headerTitle = document.getElementById('headerTitle');
        const headerSubtitle = document.getElementById('headerSubtitle');
        
        if (this.currentModule === 'module_a') {
            headerTitle.textContent = 'ccGPT - internal wiki';
            headerSubtitle.textContent = 'Internal CC Wiki';
        } else if (this.currentModule === 'module_b') {
            headerTitle.textContent = 'civilGPT';
            headerSubtitle.textContent = 'Civil 3D Command Knowledge Base';
        } else if (this.currentModule === 'module_c') {
            headerTitle.textContent = 'bimGPT';
            headerSubtitle.textContent = 'ISO 19650 Knowledge Master';
        }
    }

    clearChatUI() {
        const welcomeTitle = document.getElementById('welcomeTitle');
        const welcomeText = document.getElementById('welcomeText');
        
        this.chatContainer.innerHTML = `
            <div class="welcome-message">
                <img src="/static/cc-logo.png" alt="Logo" class="welcome-logo">
                <h2 id="welcomeTitle">Welcome to ${this.currentModuleName}</h2>
                <p id="welcomeText">Start a conversation by asking a question.</p>
            </div>
        `;
    }

    async checkHealth() {
        try {
            const response = await fetch(`/api/health?module=${this.currentModule}`);
            const data = await response.json();
            
            if (data.status === 'ready') {
                this.setStatus('ready', `${this.currentModuleName} ready`);
                this.messageInput.disabled = false;
                this.sendBtn.disabled = false;
            } else {
                this.setStatus('error', `Database not found for ${this.currentModuleName}. Please build the database first.`);
                this.messageInput.disabled = true;
                this.sendBtn.disabled = true;
            }
        } catch (error) {
            console.error('Health check failed:', error);
            this.setStatus('error', 'Failed to connect to server');
            this.messageInput.disabled = true;
            this.sendBtn.disabled = true;
        }
    }

    setStatus(status, text) {
        this.statusIndicator.className = `status-indicator ${status}`;
        this.statusIndicator.querySelector('.status-text').textContent = text;
    }

    async loadHistory() {
        try {
            const response = await fetch(`/api/history?module=${this.currentModule}`);
            const data = await response.json();
            
            if (data.history && data.history.length > 0) {
                // Remove welcome message
                const welcomeMsg = this.chatContainer.querySelector('.welcome-message');
                if (welcomeMsg) {
                    welcomeMsg.remove();
                }
                
                // Display history
                data.history.forEach(msg => {
                    this.addMessage(msg.content, msg.role, false);
                });
            }
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }

    async loadFiles() {
        try {
            const response = await fetch(`/api/files?module=${this.currentModule}`);
            const data = await response.json();
            
            if (data.files && data.files.length > 0) {
                this.displayFiles(data.files);
            } else {
                this.filesList.innerHTML = `
                    <div class="empty-files">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"/>
                            <polyline points="13 2 13 9 20 9"/>
                        </svg>
                        <p>No files found in the knowledge base</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load files:', error);
            this.filesList.innerHTML = `
                <div class="empty-files">
                    <p>Error loading files</p>
                </div>
            `;
        }
    }

    displayFiles(files) {
        this.filesList.innerHTML = '';
        
        files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            const fileName = document.createElement('div');
            fileName.className = 'file-name';
            fileName.textContent = file.name;
            
            const fileMeta = document.createElement('div');
            fileMeta.className = 'file-meta';
            
            const fileSize = document.createElement('span');
            fileSize.className = 'file-size';
            fileSize.textContent = this.formatFileSize(file.size);
            
            fileMeta.appendChild(fileSize);
            
            fileItem.appendChild(fileName);
            fileItem.appendChild(fileMeta);
            
            this.filesList.appendChild(fileItem);
        });
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || this.isProcessing) {
            return;
        }

        // Remove welcome message if present
        const welcomeMsg = this.chatContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        
        // Show typing indicator
        const typingIndicator = this.showTypingIndicator();
        
        // Disable input while processing
        this.isProcessing = true;
        this.messageInput.disabled = true;
        this.sendBtn.disabled = true;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    module: this.currentModule 
                }),
            });

            const data = await response.json();

            // Remove typing indicator
            typingIndicator.remove();

            if (response.ok) {
                // Add assistant response
                this.addMessage(data.response, 'assistant');
            } else {
                // Show error
                this.addMessage(
                    `Error: ${data.error || 'Failed to get response'}`,
                    'assistant'
                );
            }
        } catch (error) {
            console.error('Error sending message:', error);
            typingIndicator.remove();
            this.addMessage(
                'Error: Failed to communicate with the server',
                'assistant'
            );
        } finally {
            // Re-enable input
            this.isProcessing = false;
            this.messageInput.disabled = false;
            this.sendBtn.disabled = false;
            this.messageInput.focus();
        }
    }

    addMessage(text, role, scroll = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const roleSpan = document.createElement('div');
        roleSpan.className = 'message-role';
        roleSpan.textContent = role === 'user' ? 'You' : this.currentModuleName;

        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.textContent = text;

        contentDiv.appendChild(roleSpan);
        contentDiv.appendChild(textDiv);
        messageDiv.appendChild(contentDiv);

        this.chatContainer.appendChild(messageDiv);

        if (scroll) {
            this.scrollToBottom();
        }
    }

    showTypingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const roleSpan = document.createElement('div');
        roleSpan.className = 'message-role';
        roleSpan.textContent = this.currentModuleName;

        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;

        contentDiv.appendChild(roleSpan);
        contentDiv.appendChild(typingDiv);
        messageDiv.appendChild(contentDiv);

        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();

        return messageDiv;
    }

    async clearConversation() {
        if (!confirm('Are you sure you want to clear the conversation?')) {
            return;
        }

        try {
            const response = await fetch('/api/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ module: this.currentModule }),
            });

            if (response.ok) {
                // Clear chat container
                this.clearChatUI();
            }
        } catch (error) {
            console.error('Failed to clear conversation:', error);
            alert('Failed to clear conversation');
        }
    }

    scrollToBottom() {
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});

