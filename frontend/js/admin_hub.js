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

    setTimeout(loadVerificationDashboard, 700);
    setTimeout(loadPulseMetrics, 500);
});
