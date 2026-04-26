document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('porter-chat-container');
    const chatInput = document.getElementById('porter-chat-input');
    const sendButton = document.getElementById('porter-chat-send');

    // Stealth trigger to wake up the cloud vector infrastructure while user is browsing
    if (window.Auth && window.Auth.fetchWithAuth) {
        window.Auth.fetchWithAuth('/api/wake_infrastructure', { method: 'POST' }).catch(e => console.log('Wake pulse ignored'));
    } else {
        fetch('/api/wake_infrastructure', { method: 'POST' }).catch(e => console.log('Wake pulse ignored'));
    }
    const syncButton = document.getElementById('sync-calendar-btn');

    // Utility function to escape HTML to prevent XSS
    const escapeHTML = (str) => {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag])
        );
    };

    /**
     * Appends a message to the chat container
     */
    const appendMessage = (role, content, logs = []) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = role === 'user' ? 'flex gap-4 flex-row-reverse' : 'flex gap-4';

        let logHTML = '';
        if (logs && logs.length > 0) {
            logHTML = logs.map(log => `<p class="text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded p-1 mt-2 font-mono">🔍 ${escapeHTML(log)}</p>`).join('');
        }

        if (role === 'user') {
            messageDiv.innerHTML = `
                <div class="bg-blue-600 text-white rounded-2xl rounded-tr-none p-4 max-w-[80%]">
                    <p>${escapeHTML(content)}</p>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-xl flex-shrink-0">🤖</div>
                <div class="bg-gray-100 rounded-2xl rounded-tl-none p-4 text-gray-800 max-w-[80%]">
                    <p>${escapeHTML(content).replace(/\\n/g, '<br>')}</p>
                    ${logHTML}
                </div>
            `;
        }

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };

    const sendMessage = async () => {
        const message = chatInput.value.trim();
        if (!message) return;

        // Optimistically append user message
        appendMessage('user', message);
        chatInput.value = '';
        chatInput.disabled = true;
        sendButton.disabled = true;

        // Show a temporary "Thinking" indicator
        const thinkingId = 'thinking-' + Date.now();
        const thinkingDiv = document.createElement('div');
        thinkingDiv.id = thinkingId;
        thinkingDiv.className = 'flex gap-4';
        thinkingDiv.innerHTML = `
            <div class="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-xl flex-shrink-0">🤖</div>
            <div class="bg-gray-100 rounded-2xl p-4 text-gray-500 italic">Thinking...</div>
        `;
        chatContainer.appendChild(thinkingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
            
            const response = await fetchFn('/api/chat/porter', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            document.getElementById(thinkingId)?.remove();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.error) {
                appendMessage('porter', `Error: ${data.error}`);
            } else {
                appendMessage('porter', data.response, data.transparency_logs);
            }

        } catch (error) {
            console.error('Chat error:', error);
            document.getElementById(thinkingId)?.remove();
            appendMessage('porter', 'Sorry, I encountered an issue connecting to my core logic module.');
        } finally {
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        }
    };

    if (sendButton && chatInput) {
        sendButton.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    if (syncButton) {
        syncButton.addEventListener('click', async () => {
            const originalText = syncButton.innerText;
            syncButton.innerText = "⏳ Syncing...";
            syncButton.disabled = true;
            try {
                const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
                const response = await fetchFn('/api/calendar/user_sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    syncButton.innerText = "✅ Synced!";
                } else {
                    syncButton.innerText = "❌ Sync Failed";
                }
            } catch (e) {
                console.error(e);
                syncButton.innerText = "❌ Sync Failed";
            } finally {
                setTimeout(() => {
                    syncButton.innerText = originalText;
                    syncButton.disabled = false;
                }, 3000);
            }
        });
    }
    
    // Fetch GTKY Scans
    const loadArtifactScans = async () => {
        const scanContainer = document.getElementById('dynamic-artifact-scans');
        if (!scanContainer) return;
        
        try {
            const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
            const res = await fetchFn('/api/artifacts/scan');
            if (res.ok) {
                const data = await res.json();
                if (data.results && data.results.includes("I noticed some gaps")) {
                    const lines = data.results.split('\\n').filter(l => l.trim().startsWith('-'));
                    scanContainer.innerHTML = ''; // clear loader
                    
                    lines.forEach((line, index) => {
                        const div = document.createElement('div');
                        div.className = "bg-yellow-50 border border-yellow-200 p-4 rounded-xl mb-3";
                        div.innerHTML = `
                            <h4 class="font-bold text-yellow-800 mb-1">Gap Detected</h4>
                            <p class="text-sm text-yellow-700 mb-3">${escapeHTML(line)}</p>
                            <textarea id="gap-input-${index}" class="w-full bg-white border border-yellow-300 rounded-lg p-3 outline-none focus:ring-2 focus:ring-yellow-400 mb-2" rows="2" placeholder="Write memory details here to satisfy the architect..."></textarea>
                            <button id="gap-btn-${index}" class="bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-2 px-4 rounded-lg text-sm transition shadow-sm">Send to Porter to Save</button>
                        `;
                        scanContainer.appendChild(div);
                        
                        document.getElementById(`gap-btn-${index}`).addEventListener('click', () => {
                             const mem = document.getElementById(`gap-input-${index}`).value;
                             if(mem.trim() === '') return;
                             chatInput.value = `Update my origin story regarding this gap: [${line}] with this new memory: ${mem}`;
                             sendMessage();
                             div.style.opacity = '0.5';
                             document.getElementById(`gap-btn-${index}`).disabled = true;
                        });
                    });
                } else {
                     scanContainer.innerHTML = `<div class="text-green-600 font-bold bg-green-50 p-4 rounded"><p>✅ ${escapeHTML(data.results)}</p></div>`;
                }
            }
        } catch (e) {
            scanContainer.innerHTML = '<p class="text-red-500">Failed to load scans.</p>';
        }
    };

    // Fetch Adventure Log Delta for Overview
    const loadAdventureLog = async () => {
        try {
            const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
            const res = await fetchFn('/api/calendar/adventure_log');
            if (res.ok) {
                const data = await res.json();
                if (data.data) {
                    if (document.getElementById('user-intentions-logged')) {
                        document.getElementById('user-intentions-logged').innerText = data.data.intentions || "0";
                    }
                    if (document.getElementById('user-actual-activities')) {
                        document.getElementById('user-actual-activities').innerText = data.data.actuals || "0";
                    }
                    if (document.getElementById('user-matched-intentions')) {
                        document.getElementById('user-matched-intentions').innerText = data.data.matched || "0";
                    }
                }
            }
        } catch (e) {
            console.error("Failed to load adventure log", e);
        }
    };

    setTimeout(loadArtifactScans, 500);
    setTimeout(loadAdventureLog, 700);
});
