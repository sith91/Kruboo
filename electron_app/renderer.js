document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const chatList = document.getElementById('chat-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const messagesContainer = document.getElementById('messages-container');
    const currentChatTitle = document.getElementById('current-chat-title');
    const promptInput = document.getElementById('prompt-input');
    const sendBtn = document.getElementById('send-btn');
    const minimizeBtn = document.getElementById('minimize-btn');

    // State Management
    let chats = JSON.parse(localStorage.getItem('nexus-chats')) || [
        { id: Date.now(), title: 'First Conversation', messages: [] }
    ];
    let activeChatId = chats[0].id;

    // Load Initial Chats
    function renderChatList() {
        if (!chatList) return;
        chatList.innerHTML = '';
        chats.forEach(chat => {
            const item = document.createElement('div');
            item.className = `chat-item ${chat.id === activeChatId ? 'active' : ''}`;
            
            // Fixed: Use addEventListener instead of inline onclick for closure safety
            item.onclick = () => window.switchChat(chat.id);
            
            item.innerHTML = `
                <div class="chat-item-text">
                    <span>💬</span> ${chat.title}
                </div>
                <div class="chat-item-actions">
                    <button onclick="window.shareChat(${chat.id}, event)" title="Share">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path><polyline points="16 6 12 2 8 6"></polyline><line x1="12" y1="2" x2="12" y2="15"></line></svg>
                    </button>
                    <button onclick="window.deleteChat(${chat.id}, event)" title="Delete">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            `;
            chatList.appendChild(item);
        });
    }

    window.deleteChat = (id, event) => {
        if (event) event.stopPropagation();
        chats = chats.filter(c => c.id !== id);
        if (chats.length === 0) {
            chats = [{ id: Date.now(), title: 'New Conversation', messages: [] }];
        }
        if (activeChatId === id) {
            activeChatId = chats[0].id;
        }
        saveChats();
        window.switchChat(activeChatId);
    };

    window.shareChat = (id, event) => {
        if (event) event.stopPropagation();
        const chat = chats.find(c => c.id === id);
        if (chat) {
            const content = chat.messages.map(m => `${m.isUser ? 'User' : 'AI'}: ${m.text}`).join('\n\n');
            navigator.clipboard.writeText(content);
            alert("Chat content copied to clipboard!");
        }
    };

    window.switchChat = (id) => {
        activeChatId = id;
        const activeChat = chats.find(c => c.id === id);
        if (activeChat) {
            currentChatTitle.innerText = activeChat.title;
            renderMessages();
            renderChatList();
        }
    };

    function renderMessages() {
        if (!messagesContainer) return;
        const activeChat = chats.find(c => c.id === activeChatId);
        messagesContainer.innerHTML = '';
        if (activeChat && activeChat.messages) {
            activeChat.messages.forEach(msg => {
                addMessageToUI(msg.text, msg.isUser, msg.meta);
            });
        }
    }

    function formatText(text) {
        // Replace Markdown links: [Title](URL) with <a href="URL" target="_blank">Title</a>
        let formatted = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="chat-link">$1</a>');
        // Replace newlines with <br>
        return formatted.replace(/\n/g, '<br>');
    }

    function addMessageToUI(text, isUser, meta = '') {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        msgDiv.innerHTML = `
            <div class="message-bubble">${formatText(text)}</div>
            ${meta ? `<div class="message-meta">${meta}</div>` : ''}
        `;
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    newChatBtn.onclick = () => {
        const newChat = { 
            id: Date.now(), 
            title: `New Chat ${chats.length + 1}`, 
            messages: [] 
        };
        chats.unshift(newChat);
        activeChatId = newChat.id;
        saveChats();
        window.switchChat(newChat.id);
    };

    function saveChats() {
        localStorage.setItem('nexus-chats', JSON.stringify(chats));
    }

    const stopBtn = document.getElementById('stop-btn');

    async function sendMessage() {
        const text = promptInput.value.trim();
        if (!text) return;

        promptInput.value = '';
        promptInput.style.height = 'auto';

        const activeChat = chats.find(c => c.id === activeChatId);
        const newMsg = { text, isUser: true, timestamp: Date.now() };
        activeChat.messages.push(newMsg);
        
        if (activeChat.messages.length === 1) {
            activeChat.title = text.substring(0, 20) + (text.length > 20 ? '...' : '');
        }

        renderMessages();
        saveChats();
        renderChatList();

        // Switch to Stop button
        sendBtn.style.display = 'none';
        stopBtn.style.display = 'flex';

        const settings = JSON.parse(localStorage.getItem('nexus-settings')) || {};
        const provider = settings.apiKey ? 'openai' : 'local';

        let fullResponse = "";
        const assistantMsgDiv = document.createElement('div');
        assistantMsgDiv.className = 'message assistant';
        assistantMsgDiv.innerHTML = `<div class="message-bubble">...</div>`;
        messagesContainer.appendChild(assistantMsgDiv);
        const bubble = assistantMsgDiv.querySelector('.message-bubble');

        window.aiBackend.onStreamToken((data) => {
            if (data.token) {
                fullResponse += data.token;
                bubble.innerHTML = formatText(fullResponse);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            if (data.action === "hide_orb") {
                setTimeout(() => window.aiBackend.toggleMainWindow(), 2000);
            }
            if (data.action === "stream_done") {
                finalizeResponse(fullResponse, data.full_response || fullResponse);
            }
        });

        window.aiBackend.onStreamError((err) => {
            bubble.innerText = "Error: " + err;
            finalizeResponse(fullResponse, "Error occurred");
        });

        window.aiBackend.askStream({
            query: text,
            chat_id: activeChatId.toString(),
            assistant_name: settings.name || "Nexus AI",
            llm_provider: provider,
            llm_model: settings.model || "llama-3",
            api_key: settings.apiKey || "",
            language: settings.lang || "en-US",
            feeling: settings.feeling || "professional"
        });
    }

    function finalizeResponse(response, finalFull) {
        const activeChat = chats.find(c => c.id === activeChatId);
        activeChat.messages.push({ text: finalFull, isUser: false, timestamp: Date.now() });
        saveChats();
        sendBtn.style.display = 'flex';
        stopBtn.style.display = 'none';
        renderMessages();
    }

    if (stopBtn) stopBtn.onclick = () => {
        window.aiBackend.stopStream();
        sendBtn.style.display = 'flex';
        stopBtn.style.display = 'none';
    };

    if (sendBtn) sendBtn.onclick = sendMessage;
    if (minimizeBtn) minimizeBtn.onclick = () => window.aiBackend.toggleMainWindow();

    if (promptInput) {
        promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        promptInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight < 150 ? this.scrollHeight : 150) + 'px';
        });
    }

    // Fixed: Logic to handle Voice Commands and other storage changes
    window.addEventListener('storage', (e) => {
        if (e.key === 'nexus-chats') {
            chats = JSON.parse(e.newValue);
            renderMessages();
            renderChatList();
        }
    });

    // Final Init
    window.switchChat(activeChatId);
});
