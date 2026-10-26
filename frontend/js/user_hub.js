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

    // Initial dynamic welcome message
    appendMessage('porter', '⏳ Booting consciousness...');
    
    const loadWelcomeMessage = async () => {
        try {
            const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
            const res = await fetchFn('/api/chat/welcome');
            if (res.ok) {
                const data = await res.json();
                
                // Remove the loading message
                const msgs = chatContainer.querySelectorAll('.flex.gap-4');
                if (msgs.length > 0) msgs[msgs.length - 1].remove();

                if (data.response) {
                    appendMessage('porter', data.response);
                } else {
                    appendMessage('porter', "Greetings! Systems are online, but I couldn't generate a personalized greeting. Let me know if you need to update any core motivations.");
                }
            } else {
                throw new Error("Failed to load greeting");
            }
        } catch (e) {
            const msgs = chatContainer.querySelectorAll('.flex.gap-4');
            if (msgs.length > 0) msgs[msgs.length - 1].remove();
            appendMessage('porter', "⚠️ Core systems are online, but the LLM engine seems to be unresponsive for greetings. Please check your API keys or infrastructure.");
        }
    };
    
    setTimeout(loadWelcomeMessage, 300);

    const sendMessage = async () => {
        const message = chatInput.value.trim();
        if (!message) return;

        // Optimistically append user message
        appendMessage('user', message);
        chatInput.value = '';
        chatInput.disabled = true;

        const originalText = sendButton.innerText;
        sendButton.innerText = 'Sending...';
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
            sendButton.innerText = originalText;
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
                            <label for="gap-input-${index}" class="sr-only">Write memory details</label>
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

    // Load Verification Dashboard
    const loadVerificationDashboard = async () => {
        const unvContainer = document.getElementById('dashboard-unverified');
        const verContainer = document.getElementById('dashboard-verified');
        const btnApprove = document.getElementById('btn-approve-audits');
        
        if (!unvContainer || !verContainer) return;

        const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
        
        let batchGcalIds = [];

        try {
            // Unverified queue
            const unvRes = await fetchFn('/api/calendar/unverified_audits');
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
            let verCount = 0;
            const verRes = await fetchFn('/api/calendar/verified_history');
            if (verRes.ok) {
                const data = await verRes.json();
                verContainer.innerHTML = '';
                if(data.records && data.records.length > 0) {
                     verCount = data.records.length;
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
            
            // Poke user if there's absolutely no verifications to review
            if (batchGcalIds.length === 0 && verCount === 0) {
                unvContainer.innerHTML = `
                    <div class="bg-blue-50 border border-blue-200 rounded p-4 text-center mt-2 shadow-sm">
                        <span class="text-2xl mb-2 block">📝</span>
                        <p class="text-sm text-blue-800 font-bold mb-2">No verifications needed right now!</p>
                        <p class="text-xs text-blue-600 mb-3">Have you logged your time chunks for today?</p>
                        <a href="/adventure_time_log" class="inline-block bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-4 rounded-lg transition shadow">Go to Time Log</a>
                    </div>
                `;
            }
            
            if(btnApprove) {
                 btnApprove.addEventListener('click', async () => {
                     const originalText = btnApprove.innerText;
                     btnApprove.innerText = "Approving...";
                     btnApprove.disabled = true;
                     try {
                         const response = await fetchFn('/api/calendar/approve_audits', {
                             method: 'POST',
                             headers: { 'Content-Type': 'application/json' },
                             body: JSON.stringify({ gcal_ids: batchGcalIds })
                         });
                         if(response.ok) {
                             btnApprove.classList.add('hidden');
                             unvContainer.innerHTML = '<div class="text-green-600 font-bold text-sm">✅ Approved all!</div>';
                             setTimeout(loadVerificationDashboard, 2000); // refresh layout
                         }
                     } catch(e) {
                         console.error(e);
                     } finally {
                         btnApprove.innerText = originalText;
                         btnApprove.disabled = false;
                     }
                 });
            }
            
        } catch (e) {
            console.error("Dashboard Load Error", e);
        }
    };

    // Fetch Hub Progress Metrics & Adventure Log Delta for Overview
    const loadAdventureLog = async () => {
        try {
            const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
            let res = await fetchFn('/api/user/hub_metrics');
            if (!res.ok) {
                res = await fetchFn('/api/calendar/adventure_log');
            }
            if (res.ok) {
                const data = await res.json();
                if (data.data) {
                    if (document.getElementById('user-intentions-logged')) {
                        document.getElementById('user-intentions-logged').innerText = String(data.data.intentions ?? 0);
                    }
                    if (document.getElementById('user-calendar-events')) {
                        document.getElementById('user-calendar-events').innerText = String(data.data.calendar_events ?? data.data.actuals ?? 0);
                    }
                    if (document.getElementById('user-events-classified')) {
                        document.getElementById('user-events-classified').innerText = String(data.data.unclassified ?? 0);
                    }
                    if (document.getElementById('user-matched-intentions')) {
                        document.getElementById('user-matched-intentions').innerText = String(data.data.matched ?? 0);
                    }
                    if (document.getElementById('user-valuable-detours')) {
                        document.getElementById('user-valuable-detours').innerText = String(data.data.valuable_detours ?? 0);
                    }
                    if (document.getElementById('user-detrimental-detours')) {
                        document.getElementById('user-detrimental-detours').innerText = String(data.data.detrimental_detours ?? 0);
                    }
                    if (document.getElementById('user-detrimental-delta') && data.data.detrimental_delta) {
                        const deltaEl = document.getElementById('user-detrimental-delta');
                        deltaEl.innerText = data.data.detrimental_delta;
                        deltaEl.classList.remove('hidden');
                    }
                }
            }
        } catch (e) {
            console.error("Failed to load adventure log", e);
        }
    };

    const renderSagaBadge = (sagaStatus) => {
        const status = sagaStatus || 'GRAPH_INJECTED';
        const styles = {
            'GRAPH_INJECTED': 'bg-emerald-100 text-emerald-800 border-emerald-300',
            'LLM_PROCESSING': 'bg-amber-100 text-amber-800 border-amber-300',
            'RECEIVED': 'bg-blue-100 text-blue-800 border-blue-300',
            'FAILED': 'bg-red-100 text-red-800 border-red-300'
        };
        const cls = styles[status] || styles['GRAPH_INJECTED'];
        return `<span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${cls}">${escapeHTML(status)}</span>`;
    };

    // Fetch Weekly Trajectory & Historical Saga Status
    const loadWeeklyTrajectory = async () => {
        const trajectoryList = document.getElementById('weekly-trajectory-list');
        if (!trajectoryList) return;
        
        try {
            const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
            const res = await fetchFn('/api/journal/history?limit=10');
            if (res.ok) {
                const data = await res.json();
                const allRecords = data.data || [];
                const expectations = allRecords.filter(item => item.type === 'expectation');
                const recentJournals = allRecords.filter(item => item.type === 'journal').slice(0, 2);
                
                if (expectations.length > 0 || recentJournals.length > 0) {
                    let html = '';
                    if (expectations.length > 0) {
                        const latest = expectations[0];
                        html += `
                            <li class="bg-indigo-50 p-4 rounded-xl border border-indigo-100 shadow-sm">
                                <div class="flex justify-between items-center mb-1">
                                    <span class="text-xs font-bold text-indigo-600 uppercase tracking-wide">Weekly Expectation (${escapeHTML(latest.date)})</span>
                                    ${renderSagaBadge(latest.saga_status)}
                                </div>
                                <div class="text-sm text-indigo-900 whitespace-pre-wrap leading-relaxed">${escapeHTML(latest.text)}</div>
                                <div class="mt-3 flex justify-between items-center border-t border-indigo-200 pt-2">
                                    <span class="text-xs text-indigo-500">Synced</span>
                                    ${latest.correlation_id ? `<span class="text-xs font-mono bg-indigo-200 text-indigo-800 px-2 py-0.5 rounded opacity-75">🔗 ${escapeHTML(latest.correlation_id.substring(0,8))}</span>` : ''}
                                </div>
                            </li>
                        `;
                    }
                    recentJournals.forEach(j => {
                        html += `
                            <li class="bg-white p-3 rounded-xl border border-gray-200 shadow-sm">
                                <div class="flex justify-between items-center mb-1">
                                    <span class="text-xs font-bold text-gray-600">Journal • ${escapeHTML(j.date)}</span>
                                    ${renderSagaBadge(j.saga_status)}
                                </div>
                                <div class="text-xs text-gray-700 line-clamp-2">${escapeHTML(j.text)}</div>
                            </li>
                        `;
                    });
                    trajectoryList.innerHTML = html;
                } else {
                    trajectoryList.innerHTML = `
                        <li class="bg-gray-50 p-4 rounded-xl border border-gray-200 text-center shadow-sm">
                            <p class="text-sm text-gray-600 mb-3">No trajectory defined for this week.</p>
                            <a href="/adventure_journal" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-1.5 px-4 rounded-lg transition text-sm shadow">Define Weekly Expectation</a>
                        </li>
                    `;
                }
            }
        } catch (e) {
            trajectoryList.innerHTML = '<li class="text-red-500 text-sm">Failed to load trajectory.</li>';
        }
    };

    // One-Shot Weekly Planning Form Wiring (US2)
    const initOneShotWeeklyPlanning = () => {
        const planDateInput = document.getElementById('weekly-plan-date');
        const btnSavePlan = document.getElementById('btn-save-weekly-plan');
        const statusBadge = document.getElementById('weekly-plan-status');
        if (planDateInput && !planDateInput.value) {
            planDateInput.value = new Date().toISOString().split('T')[0];
        }
        if (!btnSavePlan) return;

        btnSavePlan.addEventListener('click', async () => {
            const weekStartDate = document.getElementById('weekly-plan-date')?.value;
            const pillar = document.getElementById('weekly-intent-pillar')?.value || 'General';
            const priority = document.getElementById('weekly-intent-priority')?.value || 'High';
            const title = document.getElementById('weekly-intent-title')?.value?.trim();
            const summary = document.getElementById('weekly-plan-summary')?.value?.trim() || '';

            if (!weekStartDate || !title) {
                if (statusBadge) {
                    statusBadge.textContent = '⚠️ Enter a Week Start Date and Primary Intention.';
                    statusBadge.classList.remove('hidden');
                }
                return;
            }

            const originalText = btnSavePlan.innerText;
            btnSavePlan.innerText = '⏳ Saving Plan...';
            btnSavePlan.disabled = true;

            try {
                const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
                const res = await fetchFn('/api/planning', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        week_start_date: weekStartDate,
                        expectation_summary: summary || title,
                        intentions: [
                            {
                                title: title,
                                pillar: pillar,
                                priority: priority,
                                start_date: weekStartDate,
                                duration_minutes: 60
                            }
                        ]
                    })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    if (statusBadge) {
                        statusBadge.textContent = `✅ Saved (${data.intentions_saved} intention)`;
                        statusBadge.classList.remove('hidden');
                    }
                    document.getElementById('weekly-intent-title').value = '';
                    loadAdventureLog();
                    loadWeeklyTrajectory();
                } else {
                    if (statusBadge) {
                        statusBadge.textContent = `❌ ${data.error || 'Failed to save weekly plan'}`;
                        statusBadge.classList.remove('hidden');
                    }
                }
            } catch (err) {
                console.error('Weekly planning error:', err);
                if (statusBadge) {
                    statusBadge.textContent = '❌ Network error saving weekly plan';
                    statusBadge.classList.remove('hidden');
                }
            } finally {
                btnSavePlan.innerText = originalText;
                btnSavePlan.disabled = false;
            }
        });
    };

    // Spec-Kit / Jira <-> Google Jules Command Center Wiring (US4)
    const initJiraJulesCommandCenter = () => {
        const taskSelect = document.getElementById('jules-task-select');
        const personaSelect = document.getElementById('jules-persona-select');
        const stagedList = document.getElementById('jira-staged-list');
        const feedbackEl = document.getElementById('bridge-action-feedback');
        const drawer = document.getElementById('jules-work-order-drawer');
        const btnSpecKitPush = document.getElementById('btn-speckit-push');
        const btnJiraSync = document.getElementById('btn-jira-sync');
        const btnJulesPreview = document.getElementById('btn-jules-preview');
        const btnJulesDispatch = document.getElementById('btn-jules-dispatch');

        if (!taskSelect || !stagedList) return;
        const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
        let currentFeatureId = '003-first-serving-hub-api';

        const loadBridgeStatus = async () => {
            try {
                const res = await fetchFn('/api/integrations/jira/status');
                if (!res.ok) return;
                const payload = await res.json();
                const info = payload.data || {};
                currentFeatureId = info.feature_id || currentFeatureId;

                const featBadge = document.getElementById('bridge-feature-badge');
                const jiraBadge = document.getElementById('bridge-jira-badge');
                const julesBadge = document.getElementById('bridge-jules-badge');

                if (featBadge) featBadge.textContent = `spec: ${currentFeatureId}`;
                if (jiraBadge) {
                    jiraBadge.textContent = info.jira_configured ? 'Jira: Ready' : 'Jira: Local Queue Mode';
                    jiraBadge.className = info.jira_configured
                        ? 'text-xs font-mono bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded-full font-bold'
                        : 'text-xs font-mono bg-amber-100 text-amber-800 px-2.5 py-1 rounded-full font-bold';
                }
                if (julesBadge) {
                    julesBadge.textContent = info.jules_cli_available ? 'Jules CLI: Ready' : 'Jules CLI: Dry-Run';
                    julesBadge.className = info.jules_cli_available
                        ? 'text-xs font-mono bg-blue-100 text-blue-800 px-2.5 py-1 rounded-full font-bold'
                        : 'text-xs font-mono bg-gray-200 text-gray-700 px-2.5 py-1 rounded-full font-bold';
                }

                const tasks = info.speckit_tasks || [];
                const staged = info.staged_jira_issues || [];
                const stagedMap = {};
                staged.forEach(s => { if (s.task_id) stagedMap[s.task_id] = s; });

                taskSelect.innerHTML = '';
                tasks.forEach(t => {
                    const stagedIssue = stagedMap[t.task_id];
                    const jiraKey = stagedIssue ? stagedIssue.jira_key : `LOCAL-${currentFeatureId}-${t.task_id}`;
                    const opt = document.createElement('option');
                    opt.value = JSON.stringify({ jira_key: jiraKey, task_id: t.task_id, persona: t.persona });
                    opt.textContent = `[${t.task_id}] (${t.persona}) ${t.title.substring(0, 75)} — ${stagedIssue ? stagedIssue.jira_key : t.status}`;
                    taskSelect.appendChild(opt);
                });

                const orders = info.recent_work_orders || [];
                if (staged.length === 0 && orders.length === 0) {
                    stagedList.innerHTML = `<div class="text-xs text-gray-500 bg-gray-50 p-3 rounded-lg border border-gray-200">No staged Jira issues or Jules Work Orders yet. Click <strong>Stage Spec-Kit Tasks (T001+)</strong> or <strong>Preview Jules Work Order</strong> above!</div>`;
                } else {
                    let listHtml = '';
                    orders.slice(0, 5).forEach(wo => {
                        listHtml += `
                            <div class="bg-purple-50 border border-purple-200 rounded-lg p-2.5 text-xs flex justify-between items-center">
                                <div>
                                    <span class="font-mono font-bold text-purple-900">${escapeHTML(wo.jira_key)}</span>
                                    <span class="ml-2 bg-purple-200 text-purple-800 px-2 py-0.5 rounded font-mono">${escapeHTML(wo.persona)}</span>
                                    <span class="text-gray-600 ml-2">${escapeHTML(wo.work_order_id)}</span>
                                </div>
                                <span class="font-mono font-bold text-purple-700">${escapeHTML(wo.dispatch_status)}</span>
                            </div>
                        `;
                    });
                    staged.slice(0, 8).forEach(item => {
                        listHtml += `
                            <div class="bg-white border border-gray-200 rounded-lg p-2.5 text-xs flex justify-between items-center">
                                <div class="truncate max-w-[75%]">
                                    <span class="font-mono font-bold text-indigo-700">${escapeHTML(item.jira_key)}</span>
                                    ${item.task_id ? `<span class="ml-1 font-mono text-gray-500">[${escapeHTML(item.task_id)}]</span>` : ''}
                                    <span class="ml-2 text-gray-800">${escapeHTML(item.summary)}</span>
                                </div>
                                <span class="font-mono text-[11px] bg-gray-100 text-gray-700 px-2 py-0.5 rounded">${escapeHTML(item.sync_status || item.status)}</span>
                            </div>
                        `;
                    });
                    stagedList.innerHTML = listHtml;
                }
            } catch (e) {
                console.error('Failed to load Jira/Jules bridge status:', e);
            }
        };

        if (btnSpecKitPush) {
            btnSpecKitPush.addEventListener('click', async () => {
                const orig = btnSpecKitPush.innerText;
                btnSpecKitPush.innerText = '⏳ Staging Tasks...';
                btnSpecKitPush.disabled = true;
                try {
                    const res = await fetchFn('/api/integrations/jira/speckit-push', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            feature_dir: `specs/${currentFeatureId}`,
                            dry_run: false
                        })
                    });
                    const data = await res.json();
                    if (res.ok) {
                        if (feedbackEl) feedbackEl.textContent = `✅ Staged ${data.total_tasks || 0} Spec-Kit tasks (${data.epic_key || 'PORTER'})`;
                        await loadBridgeStatus();
                    } else if (feedbackEl) {
                        feedbackEl.textContent = `❌ ${data.error || 'Failed to stage tasks'}`;
                    }
                } catch (e) {
                    if (feedbackEl) feedbackEl.textContent = '❌ Network error staging tasks';
                } finally {
                    btnSpecKitPush.innerText = orig;
                    btnSpecKitPush.disabled = false;
                }
            });
        }

        if (btnJiraSync) {
            btnJiraSync.addEventListener('click', async () => {
                const orig = btnJiraSync.innerText;
                btnJiraSync.innerText = '⏳ Syncing Jira...';
                btnJiraSync.disabled = true;
                try {
                    const res = await fetchFn('/api/integrations/jira/sync', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ flush_pending: true, max_results: 25 })
                    });
                    const data = await res.json();
                    if (res.ok) {
                        if (feedbackEl) feedbackEl.textContent = `✅ Pulled ${data.pulled_count || 0}, Flushed ${data.flushed_count || 0}`;
                        await loadBridgeStatus();
                    } else if (feedbackEl) {
                        feedbackEl.textContent = `ℹ️ ${data.error || 'Jira sync deferred (local staging active)'}`;
                    }
                } catch (e) {
                    if (feedbackEl) feedbackEl.textContent = '❌ Network error syncing Jira';
                } finally {
                    btnJiraSync.innerText = orig;
                    btnJiraSync.disabled = false;
                }
            });
        }

        const triggerJulesDispatch = async (dryRun, btnEl) => {
            if (!taskSelect.value) return;
            let parsed;
            try {
                parsed = JSON.parse(taskSelect.value);
            } catch (e) {
                return;
            }
            const orig = btnEl.innerText;
            btnEl.innerText = dryRun ? '⏳ Building Preview...' : '⏳ Dispatching to Jules...';
            btnEl.disabled = true;
            try {
                const payload = {
                    jira_key: parsed.jira_key,
                    task_id: parsed.task_id,
                    feature_dir: `specs/${currentFeatureId}`,
                    dry_run: dryRun
                };
                if (personaSelect && personaSelect.value) {
                    payload.persona_override = personaSelect.value;
                }
                const res = await fetchFn('/api/integrations/jules/dispatch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok && data.work_order) {
                    const wo = data.work_order;
                    if (drawer) {
                        drawer.classList.remove('hidden');
                        document.getElementById('jules-drawer-title').textContent = `Work Order: ${wo.work_order_id} (${wo.persona})`;
                        document.getElementById('jules-drawer-status').textContent = wo.dispatch_status;
                        document.getElementById('jules-drawer-command').textContent = `$ ${wo.jules_command || 'jules session start'}`;
                        document.getElementById('jules-drawer-prompt').textContent = wo.prompt_payload || '';
                    }
                    if (feedbackEl) {
                        feedbackEl.textContent = dryRun
                            ? `✅ Previewed Work Order for ${wo.jira_key} (${wo.persona})`
                            : `🚀 Dispatched ${wo.jira_key} to ${wo.persona} (${wo.dispatch_status})`;
                    }
                    await loadBridgeStatus();
                } else if (feedbackEl) {
                    feedbackEl.textContent = `❌ ${data.error || 'Dispatch failed'}`;
                }
            } catch (e) {
                if (feedbackEl) feedbackEl.textContent = '❌ Network error dispatching to Jules';
            } finally {
                btnEl.innerText = orig;
                btnEl.disabled = false;
            }
        };

        if (btnJulesPreview) {
            btnJulesPreview.addEventListener('click', () => triggerJulesDispatch(true, btnJulesPreview));
        }
        if (btnJulesDispatch) {
            btnJulesDispatch.addEventListener('click', () => triggerJulesDispatch(false, btnJulesDispatch));
        }

        loadBridgeStatus();
    };

    initOneShotWeeklyPlanning();
    setTimeout(loadArtifactScans, 400);
    setTimeout(loadWeeklyTrajectory, 500);
    setTimeout(loadAdventureLog, 600);
    setTimeout(loadVerificationDashboard, 700);
    setTimeout(initJiraJulesCommandCenter, 750);
});
