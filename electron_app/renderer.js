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
    let ws;

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
        const selectedModel = settings.model || 'llama-3';
        let provider = 'local';
        if (selectedModel.startsWith('gpt')) provider = 'openai';
        else if (selectedModel.startsWith('claude')) provider = 'anthropic';
        else if (selectedModel.startsWith('deepseek')) provider = 'deepseek';
        else if (selectedModel.startsWith('grok')) provider = 'xai';

        // --- WebSocket Chat Implementation ---
        const assistantMsgDiv = document.createElement('div');
        assistantMsgDiv.className = 'message assistant';
        assistantMsgDiv.innerHTML = `<div class="message-bubble">...</div>`;
        messagesContainer.appendChild(assistantMsgDiv);
        const bubble = assistantMsgDiv.querySelector('.message-bubble');
        
        let fullResponse = "";

        // Send query over WebSocket
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: "chat_query",
                payload: {
                    query: text,
                    chat_id: activeChatId.toString(),
                    assistant_name: settings.name || "Kruuboo",
                    llm_provider: provider,
                    llm_model: selectedModel,
                    api_key: settings.apiKey || "",
                    language: settings.lang || "en-US",
                    feeling: settings.feeling || "siri"
                }
            }));

            // Temporary listener for this specific query's tokens
            const handleIncoming = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === "chat_token") {
                    const token = data.payload.token;
                    if (token) {
                        fullResponse += token;
                        bubble.innerHTML = formatText(fullResponse);
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    }
                    if (data.payload.action === "hide_orb") {
                        setTimeout(() => window.aiBackend.toggleMainWindow(), 2000);
                    }
                } else if (data.type === "chat_done") {
                    finalizeResponse(fullResponse, fullResponse);
                    ws.removeEventListener('message', handleIncoming);
                }
            };

            ws.addEventListener('message', handleIncoming);
        } else {
            bubble.innerText = "Error: WebSocket Disconnected. Reconnecting...";
            setupWebSocket();
            finalizeResponse("", "Error: Connection lost.");
        }
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

    // WebSocket Sync
    function setupWebSocket() {
        const token = "localhost"; // Local app always uses localhost token
        ws = new WebSocket(`ws://127.0.0.1:8000/ws/${token}`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
                const activeChat = chats.find(c => c.id === activeChatId);
                const isUser = data.role === 'user';
                const text = data.content;

                // Avoid duplicate (if this device sent the message)
                const lastMsg = activeChat.messages[activeChat.messages.length - 1];
                if (lastMsg && lastMsg.text === text) return;

                activeChat.messages.push({ text, isUser, timestamp: Date.now() });
                
                if (activeChat.messages.length === 1) {
                    activeChat.title = text.substring(0, 20) + (text.length > 20 ? '...' : '');
                }

                saveChats();
                renderMessages();
                renderChatList();
                
                // If it's a remote user query, auto-switch to chat view iforb is active
                if (isUser && window.aiBackend) {
                    // Logic to show chat view if it was hidden
                }
            }
        };

        ws.onclose = () => {
            console.log("WS closed, retrying...");
            setTimeout(setupWebSocket, 3000);
        };
    }

    // --- Security Logic ---
    const lockScreen = document.getElementById('lock-screen');
    const passcodeInp = document.getElementById('master-passcode');
    const unlockBtn = document.getElementById('unlock-btn');
    const unlockError = document.getElementById('unlock-error');

    async function checkSecurity() {
        try {
            const res = await fetch('http://localhost:8000/security/status');
            const data = await res.json();
            if (data.is_locked) {
                lockScreen.style.display = 'flex';
                passcodeInp.focus();
            }
        } catch (e) { console.error("Security check failed:", e); }
    }

    async function verifyPasscode() {
        const passcode = passcodeInp.value;
        if (!passcode) return;

        try {
            const res = await fetch('http://localhost:8000/security/verify_passcode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ passcode })
            });
            const data = await res.json();
            if (data.status === "success") {
                lockScreen.style.display = 'none';
                unlockError.innerText = '';
            } else {
                unlockError.innerText = 'Invalid Passcode';
                passcodeInp.value = '';
                passcodeInp.focus();
            }
        } catch (e) { unlockError.innerText = 'Server Error'; }
    }

    if (unlockBtn) unlockBtn.onclick = verifyPasscode;
    if (passcodeInp) passcodeInp.onkeydown = (e) => {
        if (e.key === 'Enter') verifyPasscode();
    };

    // Final Init
    checkSecurity();
    setupWebSocket();
    window.switchChat(activeChatId);
});
