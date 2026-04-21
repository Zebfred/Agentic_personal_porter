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
            let response;
            const chatOptions = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            };

            if (window.Auth && window.Auth.fetchWithAuth) {
                response = await window.Auth.fetchWithAuth('/api/chat/porter', chatOptions);
            } else {
                response = await fetch('/api/chat/porter', chatOptions);
            }

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
    
    // --- Phase 4 UI Widgets ---
    
    // 1. Fetch GTKY Scans
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
                        
                        // Bind button to send directly to porter
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

    // 2. Load Verification Dashboard
    const loadVerificationDashboard = async () => {
        const unvContainer = document.getElementById('dashboard-unverified');
        const verContainer = document.getElementById('dashboard-verified');
        const btnApprove = document.getElementById('btn-approve-audits');
        
        if (!unvContainer || !verContainer) return;

        const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
        
        let batchGcalIds = [];

        try {
            // Unverified queue
            const unvRes = await fetchFn('/api/admin/unverified_audits');
            if (unvRes.ok) {
                const data = await unvRes.json();
                unvContainer.innerHTML = '';
                if(data.records && data.records.length > 0) {
                     btnApprove.classList.remove('hidden');
                     data.records.forEach(r => {
                          batchGcalIds.push(r.gcal_id);
                          const isLowConfidence = (r.confidence_score !== undefined && r.confidence_score < 70);
                          const bg = isLowConfidence ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200';
                          const tag = isLowConfidence ? `<span class="text-red-600 font-bold text-xs ml-2">(${r.confidence_score}% Conf)</span>` : '';
                          
                          unvContainer.innerHTML += `
                            <a href="/journal_review?target_id=${encodeURIComponent(r.gcal_id)}" class="block hover:-translate-y-0.5 transition-transform">
                                <div class="border ${bg} rounded p-2 text-sm flex justify-between items-center cursor-pointer hover:shadow-md transition-shadow">
                                    <div><strong class="text-gray-800">${escapeHTML(r.pillar || 'Uncategorized')}</strong> ${tag}<br><span class="text-gray-600 text-xs truncate max-w-[200px] inline-block">${escapeHTML(r.summary || 'Event')}</span></div>
                                </div>
                            </a>
                          `;
                     });
                } else {
                     unvContainer.innerHTML = '<div class="text-green-600 font-bold text-sm">✅ Zero unverified actions.</div>';
                }
            }

            // Verified history
            const verRes = await fetchFn('/api/admin/verified_history');
            if (verRes.ok) {
                const data = await verRes.json();
                verContainer.innerHTML = '';
                if(data.records && data.records.length > 0) {
                     data.records.forEach(r => {
                          verContainer.innerHTML += `
                            <div class="border bg-gray-50 border-emerald-100 rounded p-2 text-sm">
                                <div><span class="text-emerald-500 font-bold">✓ ${escapeHTML(r.pillar || 'Clean')}</span> <span class="text-gray-400 text-xs">${new Date(r.verification_time).toLocaleDateString()}</span></div>
                            </div>
                          `;
                     });
                } else {
                     verContainer.innerHTML = '<div class="text-gray-400 text-sm italic">No history yet.</div>';
                }
            }
            
            if(btnApprove) {
                 btnApprove.addEventListener('click', async () => {
                     btnApprove.innerText = "Approving...";
                     try {
                         const response = await fetchFn('/api/admin/approve_audits', {
                             method: 'POST',
                             headers: { 'Content-Type': 'application/json' },
                             body: JSON.stringify({ gcal_ids: batchGcalIds })
                         });
                         if(response.ok) {
                             btnApprove.classList.add('hidden');
                             unvContainer.innerHTML = '<div class="text-green-600 font-bold text-sm">✅ Approved all!</div>';
                             setTimeout(loadVerificationDashboard, 2000); // refresh layout
                         }
                     } catch(e) { console.error(e); }
                 });
            }
            
        } catch (e) {
            console.error("Dashboard Load Error", e);
        }
    };

    // Load widgets
    setTimeout(loadArtifactScans, 500);
    setTimeout(loadVerificationDashboard, 700);
});
