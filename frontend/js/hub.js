document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('porter-chat-container');
    const chatInput = document.getElementById('porter-chat-input');
    const sendButton = document.getElementById('porter-chat-send');

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
     * @param {string} role - 'user' or 'porter'
     * @param {string} content - The message content
     * @param {Array<string>} logs - Transparency logs (optional)
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
            // Use Auth.fetchWithAuth from auth.js if available
            const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
            
            const response = await fetchFn('http://localhost:5090/api/chat/porter', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            // Remove thinking indicator
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
});
