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
    let chats = JSON.parse(localStorage.getItem('nexus-chats')) || [];
    
    // Clean up empty chats from previous sessions
    chats = chats.filter(c => c.messages && c.messages.length > 0);
    
    // Auto-create a new chat for this session
    const startupChatId = Date.now();
    chats.unshift({ id: startupChatId, title: 'New Conversation', messages: [] });
    
    let activeChatId = startupChatId;
    let activeEditableChatId = startupChatId;
    localStorage.setItem('nexus-chats', JSON.stringify(chats));
    let ws;
    let lastProposedCommand = "";
    let pendingImageBase64 = null;
    let activeVisionAction = null;
    let mediaStream = null;

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
        
        // If all chats were deleted, generate a new one
        if (chats.length === 0) {
            const newId = Date.now();
            chats = [{ id: newId, title: 'New Conversation', messages: [] }];
            activeEditableChatId = newId;
        }
        
        // If the deleted chat was the editable one, transfer edit rights to the next available chat
        if (activeEditableChatId === id) {
            activeEditableChatId = chats[0].id;
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

    function updateAssistantName() {
        const settings = JSON.parse(localStorage.getItem('nexus-settings')) || {};
        const assistantName = settings.name || "Kruboo";
        if (promptInput && activeChatId === activeEditableChatId) {
            promptInput.placeholder = `Ask ${assistantName} anything...`;
        }
    }

    window.switchChat = (id) => {
        activeChatId = id;
        const activeChat = chats.find(c => c.id === id);
        if (activeChat) {
            currentChatTitle.innerText = activeChat.title;
            renderMessages();
            renderChatList();
            
            // Lock older conversations to view-only
            if (promptInput) {
                if (activeChatId === activeEditableChatId) {
                    promptInput.disabled = false;
                    updateAssistantName();
                    if (sendBtn) {
                        sendBtn.style.opacity = "1";
                        sendBtn.style.pointerEvents = "auto";
                    }
                } else {
                    promptInput.disabled = true;
                    promptInput.placeholder = "Past conversation (View only)";
                    if (sendBtn) {
                        sendBtn.style.opacity = "0.5";
                        sendBtn.style.pointerEvents = "none";
                    }
                }
            }
        }
    };

    function renderMessages() {
        if (!messagesContainer) return;
        const activeChat = chats.find(c => c.id === activeChatId);
        messagesContainer.innerHTML = '';
        if (activeChat && activeChat.messages) {
            activeChat.messages.forEach(msg => {
                addMessageToUI(msg.text, msg.isUser, msg.meta, msg.executionResult);
            });
        }
    }

    function extractProposedCommand(text) {
        const keyword = "[PROPOSED_COMMAND:";
        const index = text.indexOf(keyword);
        if (index === -1) return null;
        
        let depth = 0;
        let startIdx = index + keyword.length;
        for (let i = index; i < text.length; i++) {
            if (text[i] === '[') depth++;
            else if (text[i] === ']') {
                depth--;
                if (depth === 0) {
                    const commandBlock = text.substring(index, i + 1);
                    const command = text.substring(startIdx, i).trim();
                    return { block: commandBlock, command: command };
                }
            }
        }
        return null;
    }

    function formatText(text) {
        // Strip [MEMORIZE: ...]
        let cleaned = text.replace(/\[MEMORIZE:\s*([^\]]*?)(?:\]|$)/g, '');
        // Strip [WEB_RESEARCH_RESULTS] leaks
        cleaned = cleaned.replace(/\[WEB_RESEARCH_RESULTS\]/gi, '');
        cleaned = cleaned.replace(/WEB_RESEARCH_RESULTS:/gi, '');
        
        // Strip [PROPOSED_COMMAND: ...] using bracket depth resolution to avoid leftovers
        let cmdInfo;
        while ((cmdInfo = extractProposedCommand(cleaned)) !== null) {
            cleaned = cleaned.replace(cmdInfo.block, '');
        }
        
        // 1. Replace [Title](URL) with HTML links
        let formatted = cleaned.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="chat-link">$1</a>');
        // 2. Replace [Title]: URL style
        formatted = formatted.replace(/\[([^\]]+)\]:\s*(https?:\/\/[^\s<]+)/g, '<a href="$2" target="_blank" class="chat-link">$1</a>');
        // 3. Replace [https://...] style
        formatted = formatted.replace(/\[(https?:\/\/[^\]]+)\]/g, '<a href="$1" target="_blank" class="chat-link">$1</a>');
        
        // Replace newlines with <br>
        return formatted.replace(/\n/g, '<br>').replace(/(<br>\s*)+<br>/g, '<br><br>').trim();
    }

    function addMessageToUI(text, isUser, meta = '', executionResult = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        
        let hasProposedCommand = false;
        let command = "";
        
        if (!isUser) {
            if (text.startsWith("PROPOSED_COMMAND: ")) {
                hasProposedCommand = true;
                command = text.substring("PROPOSED_COMMAND: ".length).trim();
            } else {
                const cmdInfo = extractProposedCommand(text);
                if (cmdInfo) {
                    hasProposedCommand = true;
                    command = cmdInfo.command;
                }
            }
        }
        
        if (hasProposedCommand) {
            lastProposedCommand = command; // Save reference
            
            const textBubbleHtml = text.startsWith("PROPOSED_COMMAND: ") ? "" : `
                <div class="message-bubble">${formatText(text)}</div>
            `;
            
            msgDiv.innerHTML = `
                ${textBubbleHtml}
                <div class="message-bubble command-card" style="background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 16px; min-width: 280px; margin: 5px 0;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                        <span style="font-size: 18px;">💻</span>
                        <strong style="color: #fff; font-size: 13px;">Execute Command</strong>
                    </div>
                    <code style="background: #111; color: #00ff87; padding: 8px 12px; border-radius: 8px; display: block; font-family: monospace; font-size: 12px; margin-bottom: 12px; overflow-x: auto; white-space: pre-wrap; border: 1px solid rgba(0,255,135,0.2);">${command}</code>
                    <button class="execute-cmd-btn" style="background: var(--accent); color: white; border: none; padding: 10px 16px; border-radius: 10px; cursor: pointer; font-size: 12px; font-weight: 600; width: 100%; transition: opacity 0.2s;">Approve & Execute</button>
                    <pre class="cmd-out-pre" style="margin-top: 10px; background: #111; color: #fff; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 11px; display: none; max-height: 150px; overflow: auto; border: 1px solid rgba(255,255,255,0.05);"></pre>
                </div>
                ${meta ? `<div class="message-meta">${meta}</div>` : ''}
            `;
            const button = msgDiv.querySelector('.execute-cmd-btn');
            const outputPre = msgDiv.querySelector('.cmd-out-pre');
            
            const displayResult = (res) => {
                outputPre.style.display = "block";
                button.disabled = true;
                if (res.success) {
                    outputPre.textContent = res.stdout || '(Executed successfully, no output)';
                    outputPre.style.color = "#00ff87";
                    button.textContent = "Executed Successfully";
                    button.style.background = "#28a745";
                } else {
                    outputPre.textContent = `Error: ${res.error}\n${res.stderr || ''}`;
                    outputPre.style.color = "#ff4c4c";
                    button.textContent = "Execution Failed";
                    button.style.background = "#dc3545";
                }
            };
            
            if (executionResult) {
                displayResult(executionResult);
            } else {
                button.onclick = async () => {
                    button.disabled = true;
                    button.textContent = "Executing...";
                    button.style.opacity = "0.7";
                    try {
                        const result = await window.aiBackend.runCommand(command);
                        // Save in local storage
                        const activeChat = chats.find(c => c.id === activeChatId);
                        if (activeChat && activeChat.messages) {
                            const msgObj = activeChat.messages.find(m => m.text === text);
                            if (msgObj) {
                                msgObj.executionResult = result;
                                saveChats();
                            }
                        }
                        displayResult(result);
                    } catch (err) {
                        const errorRes = { success: false, error: err.message, stderr: '' };
                        displayResult(errorRes);
                    }
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                };
            }
        } else {
            msgDiv.innerHTML = `
                <div class="message-bubble">${formatText(text)}</div>
                ${meta ? `<div class="message-meta">${meta}</div>` : ''}
            `;
        }
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
        activeEditableChatId = newChat.id; // Make the newly created chat editable
        saveChats();
        window.switchChat(newChat.id);
    };

    function saveChats() {
        localStorage.setItem('nexus-chats', JSON.stringify(chats));
    }

    const stopBtn = document.getElementById('stop-btn');

    async function sendMessage() {
        if (activeChatId !== activeEditableChatId) return; // Prevent sending in view-only mode
        let text = promptInput.value.trim();
        if (!text && !pendingImageBase64) return;

        if (!text && pendingImageBase64) {
            text = "Describe this image";
        }

        const queryLower = text.toLowerCase().trim();
        const approvals = ["yes", "run it", "execute it", "proceed", "go ahead", "run", "execute"];
        if (typeof lastProposedCommand !== 'undefined' && lastProposedCommand && approvals.includes(queryLower)) {
            const buttons = messagesContainer.querySelectorAll('.execute-cmd-btn');
            if (buttons.length > 0) {
                const lastButton = buttons[buttons.length - 1];
                if (!lastButton.disabled) {
                    promptInput.value = '';
                    promptInput.style.height = 'auto';
                    const activeChat = chats.find(c => c.id === activeChatId);
                    activeChat.messages.push({ text: text, isUser: true, timestamp: Date.now() });
                    renderMessages();
                    saveChats();
                    
                    lastButton.click();
                    // Clear state
                    lastProposedCommand = "";
                    return;
                }
            }
        }

        promptInput.value = '';
        promptInput.style.height = 'auto';

        let displayPrompt = text;
        const activeChat = chats.find(c => c.id === activeChatId);
        
        const settings = JSON.parse(localStorage.getItem('nexus-settings')) || {};
        const selectedModel = settings.model || 'llama-3';
        let provider = 'local';
        if (selectedModel === 'gemma-litert') provider = 'local';
        else if (selectedModel.startsWith('gpt')) provider = 'openai';
        else if (selectedModel.startsWith('claude')) provider = 'anthropic';
        else if (selectedModel.startsWith('deepseek')) provider = 'deepseek';
        else if (selectedModel.startsWith('grok')) provider = 'xai';
        else if (selectedModel.startsWith('gemini')) provider = 'gemini';

        const imagePayload = pendingImageBase64;
        if (imagePayload) {
            displayPrompt = `[Sent an Image] ${text}`;
            pendingImageBase64 = null;
            const previewContainer = document.getElementById('image-preview-container');
            if (previewContainer) previewContainer.style.display = 'none';
        }

        const newMsg = { text: displayPrompt, isUser: true, timestamp: Date.now() };
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
                    language: settings.sttLang || settings.lang || "en-US",
                    feeling: settings.feeling || "siri",
                    image: imagePayload,
                    privacy_mode: settings.privacyMode || false
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
                    if (data.payload.action === "visual_interpreter" || data.payload.action === "object_recognition") {
                        activeVisionAction = data.payload.action;
                        setTimeout(() => {
                            if (cameraBtn) cameraBtn.click();
                        }, 1000);
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
        
        // Avoid duplicate (if general WS message listener already added this broadcast message)
        const lastMsg = activeChat.messages[activeChat.messages.length - 1];
        if (lastMsg && !lastMsg.isUser && lastMsg.text === finalFull) {
            sendBtn.style.display = 'flex';
            stopBtn.style.display = 'none';
            renderMessages();
            return;
        }

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
        promptInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight < 150 ? this.scrollHeight : 150) + 'px';
        });
    }

    // WebSocket Sync
    function setupWebSocket() {
        const token = "localhost"; // Local app always uses localhost token
        ws = new WebSocket(`${window.aiBackend.wsUrl}/ws/${token}`);

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
            const res = await fetch(`${window.aiBackend.baseUrl}/security/status`);
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
            const res = await fetch(`${window.aiBackend.baseUrl}/security/verify_passcode`, {
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

    // Webcam/Camera vision elements
    const cameraBtn = document.getElementById('camera-btn');
    const cameraOverlay = document.getElementById('camera-overlay');
    const cancelCameraBtn = document.getElementById('cancel-camera-btn');
    const captureBtn = document.getElementById('capture-btn');
    const webcamVideo = document.getElementById('webcam');
    const webcamCanvas = document.getElementById('webcam-canvas');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const removeImageBtn = document.getElementById('remove-image-btn');

    if (cameraBtn) {
        cameraBtn.onclick = async () => {
            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
                webcamVideo.srcObject = mediaStream;
                cameraOverlay.style.display = 'flex';
            } catch (err) {
                console.error("Failed to access webcam:", err);
                alert("Could not open camera. Please verify camera permissions.");
            }
        };
    }

    function stopWebcam() {
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
            mediaStream = null;
        }
        if (webcamVideo) webcamVideo.srcObject = null;
        if (cameraOverlay) cameraOverlay.style.display = 'none';
    }

    if (cancelCameraBtn) cancelCameraBtn.onclick = stopWebcam;

    if (captureBtn) {
        captureBtn.onclick = () => {
            if (!webcamVideo || !webcamCanvas) return;
            const width = webcamVideo.videoWidth || 640;
            const height = webcamVideo.videoHeight || 480;
            webcamCanvas.width = width;
            webcamCanvas.height = height;
            const ctx = webcamCanvas.getContext('2d');
            ctx.drawImage(webcamVideo, 0, 0, width, height);
            
            pendingImageBase64 = webcamCanvas.toDataURL('image/jpeg');
            if (imagePreview) imagePreview.src = pendingImageBase64;
            if (imagePreviewContainer) imagePreviewContainer.style.display = 'flex';
            
            stopWebcam();

            if (activeVisionAction) {
                const currentAction = activeVisionAction;
                activeVisionAction = null;
                setTimeout(async () => {
                    if (currentAction === 'visual_interpreter') {
                        promptInput.value = "";
                        sendMessage();
                    } else if (currentAction === 'object_recognition') {
                        const settings = JSON.parse(localStorage.getItem('nexus-settings')) || {};
                        const mode = settings.objectRecognitionMode || 'cloud';
                        if (mode === 'local') {
                            const activeChat = chats.find(c => c.id === activeChatId);
                            activeChat.messages.push({ text: "[Local Object Detection]", isUser: true, timestamp: Date.now() });
                            renderMessages();
                            
                            try {
                                const response = await fetch(`${window.aiBackend.baseUrl}/detect_objects_local`, {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ image: pendingImageBase64.replace(/^data:image\/[a-z]+;base64,/, "") })
                                });
                                const resData = await response.json();
                                activeChat.messages.push({ text: resData.response, isUser: false, timestamp: Date.now() });
                                renderMessages();
                                saveChats();
                                
                                pendingImageBase64 = null;
                                if (imagePreviewContainer) imagePreviewContainer.style.display = 'none';
                                
                                if (window.aiBackend && window.aiBackend.speak) {
                                    window.aiBackend.speak(resData.response);
                                }
                            } catch (e) {
                                console.error("Local object detection failed:", e);
                            }
                        } else {
                            promptInput.value = "Identify and list the objects you see in this image.";
                            sendMessage();
                        }
                    }
                }, 500);
            }
        };
    }

    if (removeImageBtn) {
        removeImageBtn.onclick = () => {
            pendingImageBase64 = null;
            if (imagePreviewContainer) imagePreviewContainer.style.display = 'none';
            if (imagePreview) imagePreview.src = '';
        };
    }

    // Final Init
    if (window.aiBackend && window.aiBackend.onTriggerAction) {
        window.aiBackend.onTriggerAction((action) => {
            if (action === 'visual_interpreter' || action === 'object_recognition') {
                activeVisionAction = action;
                if (cameraBtn) cameraBtn.click();
            }
        });
    }
    if (window.aiBackend && window.aiBackend.onSettingsUpdated) {
        window.aiBackend.onSettingsUpdated(() => {
            updateAssistantName();
        });
    }
    checkSecurity();
    setupWebSocket();
    window.switchChat(activeChatId);
});
