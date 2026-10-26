document.addEventListener('DOMContentLoaded', () => {
    // Stealth trigger to wake up the cloud vector infrastructure while admin is browsing
    fetch('/api/wake_infrastructure', { method: 'POST' }).catch(e => console.log('Wake pulse ignored'));

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

    if (syncButton) {
        syncButton.addEventListener('click', async () => {
            const originalText = syncButton.innerText;
            syncButton.innerText = "⏳ Syncing System State...";
            syncButton.disabled = true;
            try {
                const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
                const response = await fetchFn('/api/admin/system_sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    syncButton.innerText = "✅ System Synced!";
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

    const loadPulseMetrics = async () => {
        try {
            const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
            const res = await fetchFn('/api/admin/pulse');
            if (res.ok) {
                const data = await res.json();
                if (document.getElementById('pulse-synced-events')) {
                    document.getElementById('pulse-synced-events').innerText = data.total_synced_events || "0";
                }
                if (document.getElementById('pulse-valuable-detours')) {
                    document.getElementById('pulse-valuable-detours').innerText = data.weekly_detours || "0";
                }
                if (document.getElementById('pulse-logged-reflections')) {
                    document.getElementById('pulse-logged-reflections').innerText = data.total_reflections || "0";
                }
            }
        } catch (e) {
            console.error("Failed to load pulse metrics", e);
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
                     const originalText = btnApprove.innerText;
                     btnApprove.innerText = "Approving...";
                     btnApprove.disabled = true;
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

    // Impersonation feature
    const btnImpersonate = document.getElementById('btn-impersonate');
    if (btnImpersonate) {
        btnImpersonate.addEventListener('click', async () => {
            const email = document.getElementById('impersonate-email').value.trim();
            if (!email) {
                alert("Please enter an email to impersonate.");
                return;
            }
            
            btnImpersonate.innerText = "Processing...";
            btnImpersonate.disabled = true;
            try {
                const fetchFn = window.Auth && window.Auth.fetchWithAuth ? window.Auth.fetchWithAuth : fetch;
                const response = await fetchFn('/api/admin/impersonate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target_email: email })
                });
                
                const data = await response.json();
                if (response.ok) {
                    // Save admin token
                    sessionStorage.setItem('admin_token', Auth.getToken());
                    sessionStorage.setItem('is_impersonation', 'true');
                    
                    // Set new token and roles
                    Auth.setToken(data.token);
                    sessionStorage.setItem('porter_role', data.role);
                    sessionStorage.setItem('porter_account_type', data.account_type);
                    
                    alert(`Now impersonating ${email}. Redirecting to User Hub...`);
                    window.location.href = 'index.html';
                } else {
                    alert(`Error: ${data.error || 'Failed to impersonate'}`);
                    btnImpersonate.innerText = "Impersonate User";
                    btnImpersonate.disabled = false;
                }
            } catch (e) {
                console.error(e);
                alert("Network error.");
                btnImpersonate.innerText = "Impersonate User";
                btnImpersonate.disabled = false;
            }
        });
    }

    // Spec-Kit / Jira <-> Google Jules Command Center Wiring (Admin View)
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
                }
                if (julesBadge) {
                    julesBadge.textContent = info.jules_cli_available ? 'Jules CLI: Ready' : 'Jules CLI: Dry-Run';
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
                    stagedList.innerHTML = `<div class="text-xs text-muted p-3 rounded-lg border border-border">No staged Jira issues or Jules Work Orders yet. Click <strong>Stage Spec-Kit Tasks (T001+)</strong> or <strong>Preview Jules Work Order</strong> above.</div>`;
                } else {
                    let listHtml = '';
                    orders.slice(0, 5).forEach(wo => {
                        listHtml += `
                            <div class="bg-surface border border-border rounded-lg p-2.5 text-xs flex justify-between items-center">
                                <div>
                                    <span class="font-mono font-bold text-primary">${escapeHTML(wo.jira_key)}</span>
                                    <span class="ml-2 bg-gray-200 text-gray-800 px-2 py-0.5 rounded font-mono">${escapeHTML(wo.persona)}</span>
                                    <span class="text-muted ml-2">${escapeHTML(wo.work_order_id)}</span>
                                </div>
                                <span class="font-mono font-bold text-secondary">${escapeHTML(wo.dispatch_status)}</span>
                            </div>
                        `;
                    });
                    staged.slice(0, 8).forEach(item => {
                        listHtml += `
                            <div class="bg-surface border border-border rounded-lg p-2.5 text-xs flex justify-between items-center">
                                <div class="truncate max-w-[75%]">
                                    <span class="font-mono font-bold text-main">${escapeHTML(item.jira_key)}</span>
                                    ${item.task_id ? `<span class="ml-1 font-mono text-muted">[${escapeHTML(item.task_id)}]</span>` : ''}
                                    <span class="ml-2 text-main">${escapeHTML(item.summary)}</span>
                                </div>
                                <span class="font-mono text-[11px] bg-gray-100 text-gray-700 px-2 py-0.5 rounded">${escapeHTML(item.sync_status || item.status)}</span>
                            </div>
                        `;
                    });
                    stagedList.innerHTML = listHtml;
                }
            } catch (e) {
                console.error('Failed to load admin Jira/Jules bridge status:', e);
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
                        body: JSON.stringify({ feature_dir: `specs/${currentFeatureId}`, dry_run: false })
                    });
                    const data = await res.json();
                    if (res.ok) {
                        if (feedbackEl) feedbackEl.textContent = `✅ Staged ${data.total_tasks || 0} Spec-Kit tasks`;
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
                        feedbackEl.textContent = `ℹ️ ${data.error || 'Jira sync deferred'}`;
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

    setTimeout(loadVerificationDashboard, 700);
    setTimeout(loadPulseMetrics, 500);
    setTimeout(initJiraJulesCommandCenter, 600);
});
