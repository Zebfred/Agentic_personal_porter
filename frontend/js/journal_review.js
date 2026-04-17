document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const targetId = urlParams.get('target_id'); // If arriving from hub link
    
    // Default to today if no date specified. (We could add a date parameter later if needed)
    let selectedDate = urlParams.get('date') ? urlParams.get('date') : new Date().toISOString().split('T')[0];

    const datePicker = document.getElementById('date-picker');
    const loadBtn = document.getElementById('load-btn');
    const syncGcalBtn = document.getElementById('sync-gcal-btn');
    
    const intentList = document.getElementById('intent-list');
    const actualList = document.getElementById('actual-list');
    const focusContainer = document.getElementById('focus-container');

    if (datePicker) {
        datePicker.value = selectedDate;
    }

    if (loadBtn) {
        loadBtn.addEventListener('click', () => {
            selectedDate = datePicker.value;
            fetchReviewData(selectedDate);
        });
    }

    if (syncGcalBtn) {
        syncGcalBtn.addEventListener('click', () => {
            alert("This feature pushes current edits direct to the Google Cloud workspace via bi-directional sync! (WIP: Will iterate events shortly if authorized)");
        });
    }

    fetchReviewData(selectedDate);
    
    function fetchReviewData(dateStr) {
        // We call the newly minted adventure log which returns Socratic Delta over X days
        // Right now our backend logic takes days_back, so passing the date string handles it.
        fetch(`/api/calendar/adventure_log?date=${dateStr}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('porter_token')}` }
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success' && data.data) {
                renderReviewData(data.data);
            } else {
                console.error("Failed to load delta:", data);
                if (actualList) actualList.innerHTML = `<p class="text-red-500">Error loading data.</p>`;
            }
        })
        .catch(err => {
            console.error(err);
        });

        // Also fetch the events natively if we want to build a re-classification target list
        fetch(`/api/calendar/get_calendar_events?date=${dateStr}`, {
             headers: { 'Authorization': `Bearer ${localStorage.getItem('porter_token')}` }
        }).then(res => res.json()).then(data => {
            window.currentEvents = data.events || [];
        });
    }

    function renderReviewData(analysis) {
        // analysis = result of calculate_daily_delta()
        if (intentList) {
            intentList.innerHTML = '';
            analysis.active_intentions.forEach(intent => {
                intentList.innerHTML += `<div class="bg-indigo-50 border-l-4 border-indigo-400 p-2 mb-2 text-sm rounded shadow-sm">${escapeHTML(intent)}</div>`;
            });
        }

        if (actualList) {
            actualList.innerHTML = '';
            let uncatCount = 0;
            
            analysis.observations.forEach((obs, idx) => {
                let badgeColor = "bg-gray-200 text-gray-800";
                if (obs.status === "Fog of War") {
                    badgeColor = "bg-red-100 text-red-800 border border-red-300";
                    uncatCount++;
                } else if (obs.status === "Aligned") {
                    badgeColor = "bg-green-100 text-green-800 border border-green-300";
                } else if (obs.status === "Valuable Detour") {
                    badgeColor = "bg-yellow-100 text-yellow-800 border border-yellow-300";
                }

                const isTarget = obs.title && targetId && window.currentEvents && window.currentEvents.find(e => e.id === targetId && e.title === obs.title);
                const highlightClass = isTarget ? "ring-2 ring-indigo-500 shadow-md transform scale-105" : "";

                let html = `
                <div class="bg-white p-3 mb-3 rounded shadow-sm border border-gray-100 ${highlightClass} transition-all" data-event-id="${idx}">
                    <div class="flex justify-between items-start mb-2">
                        <strong class="text-gray-900">${escapeHTML(obs.title)}</strong>
                        <span class="text-xs px-2 py-1 rounded-full font-bold ${badgeColor}">${escapeHTML(obs.status)}</span>
                    </div>
                    <div class="text-xs text-gray-500 mb-2">
                        Pillar: <span class="font-semibold text-gray-700">${escapeHTML(obs.pillar)}</span> • Duration: ${obs.duration}m
                    </div>
                    <div class="flex gap-2">
                        ${obs.status === 'Fog of War' || obs.pillar === 'Uncategorized' ? 
                            `<button class="reclassify-btn text-xs bg-indigo-500 hover:bg-indigo-600 text-white px-2 py-1 rounded" data-title="${escapeHTML(obs.title)}">Re-Classify</button>` : 
                            `<button class="reclassify-btn text-xs bg-gray-200 hover:bg-gray-300 text-gray-700 px-2 py-1 rounded" data-title="${escapeHTML(obs.title)}">Change Pillar</button>`
                        }
                        <button class="delete-btn text-xs bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 px-2 py-1 rounded" data-title="${escapeHTML(obs.title)}">Delete Garbage Data</button>
                    </div>
                </div>
                `;
                actualList.innerHTML += html;
            });

            // Focus Container Alert
            if (focusContainer) {
                if (uncatCount > 0) {
                    focusContainer.innerHTML = `<div class="bg-red-50 text-red-700 p-4 rounded-xl border border-red-200 font-medium flex items-center justify-between shadow-sm">
                        <span><strong>Fog of War Detected:</strong> Provide category mapping for ${uncatCount} uncategorized block(s)!</span>
                    </div>`;
                } else {
                    focusContainer.innerHTML = `<div class="bg-emerald-50 text-emerald-700 p-4 rounded-xl border border-emerald-200 font-medium flex items-center shadow-sm">
                        <span class="mr-2">✨</span> Perfect Alignment. No missing data for this timeframe.
                    </div>`;
                }
            }

            attachActionListeners();
        }
    }

    function attachActionListeners() {
        document.querySelectorAll('.reclassify-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const title = e.target.getAttribute('data-title');
                const gcal_id = findGcalId(title);
                if (!gcal_id) return alert("Could not resolve specific event ID. Load more specific data.");
                
                const newPillar = prompt(`Map '${title}' into the knowledge base.\nEnter Target Pillar (e.g. 'Leisure Goal' or 'Health Goal'):`);
                if (newPillar) {
                    executeJournalAction('reclassify', gcal_id, { new_pillar: newPillar, summary: title });
                }
            });
        });

        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const title = e.target.getAttribute('data-title');
                const gcal_id = findGcalId(title);
                if (!gcal_id) return alert("Could not resolve specific event ID.");
                
                if (confirm(`Are you sure you want to annihilate '${title}'?`)) {
                    executeJournalAction('delete', gcal_id, {});
                }
            });
        });
    }

    function findGcalId(title) {
        if (!window.currentEvents) return null;
        const e = window.currentEvents.find(ev => ev.title === title);
        return e ? e.id : null;
    }

    function executeJournalAction(action, gcalId, extraData) {
        const payload = { action, gcal_id: gcalId, ...extraData };
        fetch('/api/journal/edit_event', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('porter_token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                alert(data.message);
                fetchReviewData(selectedDate); // Reload
            } else {
                alert("Error: " + data.error);
            }
        });
    }

    function escapeHTML(str) {
        if (!str) return '';
        return String(str).replace(/[&<>'"]/g, tag => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
        }[tag]));
    }
});
