document.addEventListener('DOMContentLoaded', () => {
    // Utility functions for security and API
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
    // getApiKey removed in favor of Auth module in auth.js

    const dayNav = document.getElementById('day-nav');
    const dayViewContainer = document.getElementById('day-view-container');
    const currentDayHeader = document.getElementById('current-day-header');
    const syncBtn = document.getElementById('sync-cal-btn');

    const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    const TIME_CHUNKS = [
        { id: 'late-night', label: 'Late Night (12am - 4am)' },
        { id: 'early-morning', label: 'Early Morning (4am - 8am)' },
        { id: 'late-morning', label: 'Late Morning (8am - 12pm)' },
        { id: 'afternoon', label: 'Afternoon (12pm - 4pm)' },
        { id: 'evening', label: 'Evening (4pm - 8pm)' },
        { id: 'early-night', label: 'Early Night (8pm - 12am)' }
    ];

    // Smart Mapping: Defines which hours belong to which chunk
    const TIME_CHUNK_RANGES = {
        'late-night': { start: 0, end: 4 },
        'early-morning': { start: 4, end: 8 },
        'late-morning': { start: 8, end: 12 },
        'afternoon': { start: 12, end: 16 },
        'evening': { start: 16, end: 20 },
        'early-night': { start: 20, end: 24 }
    };


    // --- Calendar Overlay State ---
    let activeWeekContext = 'current'; 
    let activeDateMap = {}; 
    let monthlyLogData = {};
    let calendarDate = new Date();

    const calendarGrid = document.getElementById('calendar-grid');
    const prevMonthBtn = document.getElementById('prev-month-btn');
    const nextMonthBtn = document.getElementById('next-month-btn');
    const currentMonthHeader = document.getElementById('current-month-header');
    const resetWeekBtn = document.getElementById('reset-current-week-btn');
    const activeWeekLabel = document.getElementById('active-week-label');

    let weeklyLog = {};

    const getStorageKey = () => `weeklyLog_${activeDateMap['monday'] || 'default'}`;

    const getWeeklyLog = () => {
        const log = localStorage.getItem(getStorageKey());
        if (log) {
            return JSON.parse(log);
        } else {
            const newLog = {};
            DAYS.forEach(day => {
                newLog[day] = {};
                TIME_CHUNKS.forEach(chunk => {
                    newLog[day][chunk.id] = {
                        intention: '',
                        activityTitle: '',
                        feeling: '',
                        brainFog: 0,
                        valuableDetour: false,
                        matchesIntent: false,
                        inventoryNote: '',
                        detrimentalDetour: false,
                        detrimentNote: '',
                        aiReflection: ''
                    };
                });
            });
            return newLog;
        }
    };

    const saveWeeklyLog = () => {
        if (activeWeekContext === 'current') {
            localStorage.setItem(getStorageKey(), JSON.stringify(weeklyLog));
        }
    };

    const renderDay = (day) => {
        // Highlight active day button
        document.querySelectorAll('.day-btn').forEach(btn => {
            const isActive = btn.dataset.day === day;
            btn.classList.toggle('bg-blue-600', isActive);
            btn.classList.toggle('text-white', isActive);
            btn.classList.toggle('bg-gray-300', !isActive);
        });

        if (currentDayHeader) {
            currentDayHeader.textContent = day.charAt(0).toUpperCase() + day.slice(1);
        }

        dayViewContainer.innerHTML = '';

        const dayData = weeklyLog[day];

        TIME_CHUNKS.forEach(chunk => {
            const chunkId = chunk.id;
            const chunkData = dayData[chunkId];
            const card = document.createElement('div');
            card.className = 'time-chunk-card bg-white p-6 rounded-lg shadow-md mb-6 border border-gray-200';
            card.dataset.day = day;
            card.dataset.chunk = chunkId;

            const isFilled = chunkData.intention.trim() !== '' || chunkData.activityTitle.trim() !== '' || chunkData.matchesIntent;
            const openAttr = isFilled ? '' : 'open';

            card.innerHTML = `
                <details class="group" ${openAttr}>
                    <summary class="flex justify-between items-center cursor-pointer list-none mb-2 outline-none">
                        <h3 class="text-xl font-bold text-gray-800 flex-grow">${chunk.label}</h3>
                        <span class="transition group-open:rotate-180">
                            <svg fill="none" height="24" shape-rendering="geometricPrecision" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" viewBox="0 0 24 24" width="24"><path d="M6 9l6 6 6-6"></path></svg>
                        </span>
                    </summary>
                    
                    <div class="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <!-- Intention Area -->
                        <div class="bg-gray-50 p-3 rounded-lg border border-gray-100">
                            <label for="intention-${day}-${chunkId}" class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">My Intention</label>
                            <textarea id="intention-${day}-${chunkId}" rows="2" class="intention-input w-full bg-white border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Sync from calendar or type here...">${escapeHTML(chunkData.intention)}</textarea>
                        </div>

                    <!-- Actuals Form -->
                    <div class="space-y-4">
                        <div class="flex items-center gap-4">
                            <div class="flex gap-2">
                                ${['happy', 'neutral', 'sad'].map(feeling => `
                                <label for="feeling-${day}-${chunkId}-${feeling}" class="cursor-pointer">
                                    <input type="radio" id="feeling-${day}-${chunkId}-${feeling}" name="feeling-${day}-${chunkId}" value="${feeling}" class="peer hidden" ${chunkData.feeling === feeling ? 'checked' : ''}>
                                    <span class="text-2xl opacity-40 peer-checked:opacity-100 hover:opacity-100 transition">${feeling === 'happy' ? '😊' : feeling === 'neutral' ? '😐' : '😔'}</span>
                                </label>
                                `).join('')}
                            </div>
                            
                            <div class="flex-grow">
                                <label for="brain-fog-${day}-${chunkId}" class="flex justify-between text-xs font-bold text-gray-500 mb-1">
                                    <span>FOG: <span id="brain-fog-value-${day}-${chunkId}">${chunkData.brainFog}</span>%</span>
                                </label>
                                <input type="range" id="brain-fog-${day}-${chunkId}" min="0" max="100" step="10" value="${chunkData.brainFog}" class="brain-fog-slider w-full h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                            </div>
                        </div>

                        <div>
                            <label for="matches-intent-${day}-${chunkId}" class="inline-flex items-center cursor-pointer">
                                <input type="checkbox" id="matches-intent-${day}-${chunkId}" class="matches-intent-checkbox form-checkbox h-4 w-4 text-green-600 rounded" ${chunkData.matchesIntent ? 'checked' : ''}>
                                <span class="ml-2 text-sm font-medium text-gray-600">Actual activity matches Intend</span>
                            </label>
                        </div>
                        <div class="mt-2">
                            <label for="valuable-detour-${day}-${chunkId}" class="inline-flex items-center cursor-pointer">
                                <input type="checkbox" id="valuable-detour-${day}-${chunkId}" class="valuable-detour-checkbox form-checkbox h-4 w-4 text-blue-600 rounded" ${chunkData.valuableDetour ? 'checked' : ''}>
                                <span class="ml-2 text-sm font-medium text-gray-600">Mark as Valuable Detour</span>
                            </label>
                        </div>

                        <div id="inventory-note-container-${day}-${chunkId}" class="${chunkData.valuableDetour ? '' : 'hidden'}">
                            <label for="inventory-note-${day}-${chunkId}" class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Inventory Note</label>
                            <textarea id="inventory-note-${day}-${chunkId}" rows="2" class="inventory-note-textarea w-full border border-yellow-200 bg-yellow-50 rounded-md p-2 focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="What did you gain?">${escapeHTML(chunkData.inventoryNote)}</textarea>
                        </div>
                        
                        <div class="mt-4">
                            <label for="detrimental-detour-${day}-${chunkId}" class="inline-flex items-center cursor-pointer">
                                <input type="checkbox" id="detrimental-detour-${day}-${chunkId}" class="detrimental-detour-checkbox form-checkbox h-4 w-4 text-red-600 rounded" ${chunkData.detrimentalDetour ? 'checked' : ''}>
                                <span class="ml-2 text-sm font-medium text-gray-600">Mark as Detrimental Detour</span>
                            </label>
                        </div>

                        <div id="detriment-note-container-${day}-${chunkId}" class="${chunkData.detrimentalDetour ? '' : 'hidden'}">
                            <label for="detriment-note-${day}-${chunkId}" class="block text-xs font-bold text-red-500 uppercase tracking-wider mb-2">What did we lose?</label>
                            <textarea id="detriment-note-${day}-${chunkId}" rows="2" class="detriment-note-textarea w-full border border-red-200 bg-red-50 rounded-md p-2 focus:ring-2 focus:ring-red-400 outline-none" placeholder="What did this cost you?">${escapeHTML(chunkData.detrimentNote)}</textarea>
                        </div>
                    </div>

                    <!-- Action Button & AI Output -->
                    <div class="mt-4 pt-3 border-t border-gray-100 flex justify-between items-center gap-4">
                        <button class="save-log-btn w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-8 rounded-lg transition shadow-sm active:scale-95 flex justify-center items-center gap-2">
                            <span>💾</span> Save Log
                        </button>
                        
                        <div id="save-status-${chunkId}" class="hidden text-green-600 font-bold text-sm animate-pulse">
                            Sovereign Sync Complete ✅
                        </div>
                    </div>
                </details>
            `;
            dayViewContainer.appendChild(card);
        });

        // Load Sovereign Reflection if it exists for this day
        fetchSovereignReflection(day);
    };

    const fetchSovereignReflection = async (day) => {
        const dateStr = activeDateMap[day];
        if (!dateStr) return;

        const container = document.getElementById('daily-reflection-container');
        const content = document.getElementById('daily-reflection-content');
        
        // Hide by default when switching days
        container.classList.add('hidden');
        content.innerHTML = '';

        try {
            const response = await Auth.fetchWithAuth(`/api/journal/reflection?date=${dateStr}`);
            if (response.ok) {
                const data = await response.json();
                if (data.data && data.data.reflection_text) {
                    content.innerHTML = escapeHTML(data.data.reflection_text).replace(/\\n/g, '<br>');
                    
                    // Show correlation ID if available (Hero lineage)
                    if (data.data.correlation_id) {
                        content.innerHTML += `<div class="mt-4 text-right"><span class="text-xs font-mono bg-purple-100 text-purple-600 px-2 py-1 rounded" title="Data Lineage ID">🔗 ${data.data.correlation_id.substring(0,12)}...</span></div>`;
                    }
                    
                    container.classList.remove('hidden');
                }
            }
        } catch (e) {
            console.error("Failed to fetch historical reflection", e);
        }
    };

    /**
     * SMART CALENDAR SYNC LOGIC
     */
    const fetchCalendarEvents = async (day) => {
        try {
            const dateStr = activeDateMap[day];

            console.log(`Fetching calendar events for ${day} (${dateStr})...`);

            // Using the endpoint from server.py with Auth module handling token
            const response = await Auth.fetchWithAuth(`/get_calendar_events?date=${dateStr}`);

            if (!response.ok) throw new Error(`Status: ${response.status}`);

            const data = await response.json();
            const events = data.events || [];

            // Map events to chunks based on hour
            const eventsByChunk = {};
            TIME_CHUNKS.forEach(chunk => eventsByChunk[chunk.id] = []);

            events.forEach(event => {
                const startTime = new Date(event.start);
                const hour = startTime.getHours();

                for (const [chunkId, range] of Object.entries(TIME_CHUNK_RANGES)) {
                    if (hour >= range.start && hour < range.end) {
                        eventsByChunk[chunkId].push(event);
                        break;
                    }
                }
            });
            return eventsByChunk;

        } catch (error) {
            console.error('Calendar Fetch Error:', error);
            return {};
        }
    };

    const populateIntentionsFromCalendar = (day, eventsByChunk) => {
        let foundEvents = 0;
        TIME_CHUNKS.forEach(chunk => {
            const chunkId = chunk.id;
            const events = eventsByChunk[chunkId] || [];
            const intentionInput = document.getElementById(`intention-${day}-${chunkId}`);

            if (intentionInput && events.length > 0) {
                foundEvents += events.length;
                // Format event titles
                const eventTitles = events.map(e => `• ${e.title}`).join('\n');

                // Only populate if empty to avoid overwriting user notes
                if (!intentionInput.value.trim()) {
                    intentionInput.value = eventTitles;
                    // Update the model immediately
                    if (weeklyLog[day] && weeklyLog[day][chunkId]) {
                        weeklyLog[day][chunkId].intention = eventTitles;
                    }

                    // Visual feedback flash
                    intentionInput.parentElement.classList.add('ring-2', 'ring-green-400');
                    setTimeout(() => intentionInput.parentElement.classList.remove('ring-2', 'ring-green-400'), 1500);
                }
            }
        });
        saveWeeklyLog();
        return foundEvents;
    };


    // --- EVENT LISTENERS ---

    // 1. Navigation
    dayNav.addEventListener('click', async (e) => {
        if (e.target.classList.contains('day-btn')) {
            const day = e.target.dataset.day;
            renderDay(day);
        }
    });

    // 2. Sync Button
    if (syncBtn) {
        syncBtn.addEventListener('click', async () => {
            const activeDayBtn = document.querySelector('.day-btn.bg-blue-600');
            const day = activeDayBtn ? activeDayBtn.dataset.day : 'monday';

            const originalText = syncBtn.innerText;
            syncBtn.innerHTML = `<span>⏳</span> Syncing...`;
            syncBtn.disabled = true;

            try {
                const events = await fetchCalendarEvents(day);
                const count = populateIntentionsFromCalendar(day, events);
                syncBtn.innerHTML = `<span>✅</span> Found ${count} Events`;
            } catch (e) {
                syncBtn.innerHTML = `<span>❌</span> Error`;
            }

            setTimeout(() => {
                syncBtn.innerHTML = originalText;
                syncBtn.disabled = false;
            }, 3000);
        });
    }

    // Sync local state dynamically on input
    const syncCardToLocal = (card) => {
        const day = card.dataset.day;
        const chunkId = card.dataset.chunk;
        if (!day || !chunkId) return;

        weeklyLog[day][chunkId] = {
            intention: card.querySelector(`#intention-${day}-${chunkId}`).value,
            feeling: card.querySelector(`input[name="feeling-${day}-${chunkId}"]:checked`)?.value || '',
            brainFog: parseInt(card.querySelector(`#brain-fog-${day}-${chunkId}`).value) || 0,
            matchesIntent: card.querySelector(`#matches-intent-${day}-${chunkId}`).checked,
            valuableDetour: card.querySelector(`#valuable-detour-${day}-${chunkId}`).checked,
            inventoryNote: card.querySelector(`#inventory-note-${day}-${chunkId}`).value,
            detrimentalDetour: card.querySelector(`#detrimental-detour-${day}-${chunkId}`).checked,
            detrimentNote: card.querySelector(`#detriment-note-${day}-${chunkId}`).value,
            aiReflection: weeklyLog[day][chunkId].aiReflection || ""
        };
        saveWeeklyLog();
    };

    // 3. UI Interactions (Delegation)
    dayViewContainer.addEventListener('input', (e) => {
        const card = e.target.closest('.time-chunk-card');
        if (!card) return;
        
        if (e.target.classList.contains('brain-fog-slider')) {
            const day = card.dataset.day;
            const chunkId = card.dataset.chunk;
            document.getElementById(`brain-fog-value-${day}-${chunkId}`).textContent = e.target.value;
        }
        
        // Auto-sync on text input
        if (e.target.tagName === 'TEXTAREA' || e.target.type === 'range') {
            syncCardToLocal(card);
        }
    });

    dayViewContainer.addEventListener('change', (e) => {
        const card = e.target.closest('.time-chunk-card');
        if (!card) return;
        
        if (e.target.classList.contains('valuable-detour-checkbox')) {
            const day = card.dataset.day;
            const chunkId = card.dataset.chunk;
            document.getElementById(`inventory-note-container-${day}-${chunkId}`).classList.toggle('hidden', !e.target.checked);
        } else if (e.target.classList.contains('detrimental-detour-checkbox')) {
            const day = card.dataset.day;
            const chunkId = card.dataset.chunk;
            document.getElementById(`detriment-note-container-${day}-${chunkId}`).classList.toggle('hidden', !e.target.checked);
        }
        
        // Auto-sync on checkbox/radio change
        syncCardToLocal(card);
    });

    // 4. MAIN ACTION: Save Log (No Reflection)
    dayViewContainer.addEventListener('click', async (e) => {
        if (e.target.classList.contains('save-log-btn')) {
            const btn = e.target;
            const card = btn.closest('.time-chunk-card');
            const day = card.dataset.day;
            const chunkId = card.dataset.chunk;

            // Gather Data
            const intention = card.querySelector(`#intention-${day}-${chunkId}`).value;
            const feelingRadio = card.querySelector(`input[name="feeling-${day}-${chunkId}"]:checked`);
            const feeling = feelingRadio ? feelingRadio.value : '';
            const brainFog = card.querySelector(`#brain-fog-${day}-${chunkId}`).value;
            const matchesIntent = card.querySelector(`#matches-intent-${day}-${chunkId}`).checked;
            const valuableDetour = card.querySelector(`#valuable-detour-${day}-${chunkId}`).checked;
            const inventoryNote = card.querySelector(`#inventory-note-${day}-${chunkId}`).value;
            const detrimentalDetour = card.querySelector(`#detrimental-detour-${day}-${chunkId}`).checked;
            const detrimentNote = card.querySelector(`#detriment-note-${day}-${chunkId}`).value;

            // Derive Actual Activity from checkboxes
            let activityTitle = "No actual activity recorded.";
            if (matchesIntent) {
                activityTitle = intention;
            } else if (valuableDetour) {
                activityTitle = inventoryNote;
            } else if (detrimentalDetour) {
                activityTitle = detrimentNote;
            }

            // Update Local State
            const chunkData = {
                intention, activityTitle, feeling, brainFog,
                matchesIntent, valuableDetour, inventoryNote,
                detrimentalDetour, detrimentNote,
                aiReflection: weeklyLog[day][chunkId].aiReflection || ""
            };
            weeklyLog[day][chunkId] = chunkData;
            saveWeeklyLog();

            // UI Feedback
            const statusMsg = card.querySelector(`#save-status-${chunkId}`);
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
            statusMsg.classList.remove('hidden');

            // Construct Payloads - CORRECT KEYS FOR NEO4J & SERVER
            // const journalEntry = `Intention: ${intention}. Actual: ${activityTitle}. Feeling: ${feeling}. Brain Fog: ${brainFog}%.`;
            const logDataForDb = {
                day: activeDateMap[day], timeChunk: chunkId, intention, actual: activityTitle,
                feeling, brainFog: parseInt(brainFog), matchesIntent,
                isValuableDetour: valuableDetour, inventoryNote,
                isDetrimentalDetour: detrimentalDetour, detrimentNote
            };

            try {
                const response = await Auth.fetchWithAuth('/api/save_log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(logDataForDb),
                });

                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

                // If this is the 8pm block, trigger reflection automatically
                if (chunkId === 'early-night') {
                    console.log("Final block logged. Triggering Socratic Reflection...");
                    triggerDailyReflection(day);
                }

            } catch (error) {
                console.error('Error saving journal entry:', error);
                statusMsg.textContent = "❌ Sync Failed";
                statusMsg.classList.add('text-red-600');
            } finally {
                setTimeout(() => {
                    statusMsg.classList.add('hidden');
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                }, 3000);
            }
        }
    });

    // 5. DAILY REFLECTION LOGIC
    const triggerDailyReflection = async (day) => {
        const reflectBtn = document.getElementById('daily-reflection-btn');
        const container = document.getElementById('daily-reflection-container');
        const content = document.getElementById('daily-reflection-content');

        // UI Loading State
        reflectBtn.disabled = true;
        reflectBtn.innerHTML = `<span>⏳</span> Analyzing...`;
        container.classList.remove('hidden');
        content.innerHTML = `<div class="animate-pulse flex items-center gap-2">Connecting to Sovereign Core<span class="dot-flashing">...</span></div>`;

        // Gather all day data for context
        const dayData = weeklyLog[day];
        let journalSummary = `Summary for ${day}:\n`;
        Object.entries(dayData).forEach(([chunk, data]) => {
            if (data.activityTitle) {
                journalSummary += `- ${chunk}: Intended ${data.intention}, Actual ${data.activityTitle}. Feeling: ${data.feeling}.\n`;
            }
        });

        try {
            const response = await Auth.fetchWithAuth('/process_journal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    journal_entry: journalSummary,
                    log_data: { day: activeDateMap[day] }
                }),
            });

            if (!response.ok) throw new Error(`Status: ${response.status}`);
            const data = await response.json();
            const reflection = data.result || "Reflection recorded.";

            // Display securely
            content.innerHTML = escapeHTML(reflection).replace(/\\n/g, '<br>');

        } catch (error) {
            console.error('Reflection Error:', error);
            content.innerHTML = `<p class="text-red-500 font-bold">⚠️ Core Mirror Offline. Try again later.</p>`;
        } finally {
            reflectBtn.disabled = false;
            reflectBtn.innerHTML = `<span>✨</span> Generate Daily Reflection`;
        }
    };

    if (document.getElementById('daily-reflection-btn')) {
        document.getElementById('daily-reflection-btn').addEventListener('click', () => {
            const activeDayBtn = document.querySelector('.day-btn.bg-blue-600');
            const day = activeDayBtn ? activeDayBtn.dataset.day : 'monday';
            triggerDailyReflection(day);
        });
    }

    // Init

    const calculateCurrentWeekMap = () => {
        const today = new Date();
        const currentDayIndex = (today.getDay() + 6) % 7;
        activeDateMap = {};
        DAYS.forEach((d, idx) => {
            const tDate = new Date(today);
            tDate.setDate(today.getDate() + (idx - currentDayIndex));
            activeDateMap[d] = tDate.toISOString().split('T')[0];
        });
    };

    // Calendar Overlay Logic
    const fetchMonthLogs = async (year, month) => {
        const monthId = `${year}-${String(month + 1).padStart(2, '0')}`;
        try {
            const response = await Auth.fetchWithAuth(`/api/logs?month=${monthId}`);
            if (response.ok) {
                const data = await response.json();
                return data.data || {};
            }
        } catch (e) {
            console.error("Failed", e);
        }
        return {};
    };

    const hasAnyLogsForDate = (dateStr) => {
        if (!monthlyLogData || !monthlyLogData.weeks) return false;
        for (const week of Object.values(monthlyLogData.weeks)) {
            if (week[dateStr] && week[dateStr].chunks && Object.keys(week[dateStr].chunks).length > 0) {
                return true;
            }
        }
        return false;
    };

    const isDayComplete = (dateStr) => {
        if (!monthlyLogData || !monthlyLogData.weeks) return false;
        
        let hasReflection = false;
        if (monthlyLogData.reflections && monthlyLogData.reflections.includes(dateStr)) {
            hasReflection = true;
        }

        // Fiona Protocol: Checkmark means Sovereign Report generated
        return hasReflection;
    };

    const loadHistoricalWeek = (mondayDateObj) => {
        activeWeekContext = 'historical';
        activeDateMap = {};
        const newLog = {};
        
        let startStr = "";
        let endStr = "";
        DAYS.forEach((day, idx) => {
            const d = new Date(mondayDateObj);
            d.setDate(mondayDateObj.getDate() + idx);
            const dateStr = d.toISOString().split('T')[0];
            activeDateMap[day] = dateStr;
            
            if (idx === 0) startStr = dateStr;
            if (idx === 6) endStr = dateStr;
            
            newLog[day] = {};
            TIME_CHUNKS.forEach(chunk => {
                let chunkData = null;
                if (monthlyLogData.weeks) {
                    for (const week of Object.values(monthlyLogData.weeks)) {
                        if (week[dateStr] && week[dateStr].chunks && week[dateStr].chunks[chunk.id]) {
                            chunkData = week[dateStr].chunks[chunk.id];
                        }
                    }
                }
                if (chunkData) {
                    newLog[day][chunk.id] = {
                        intention: chunkData.intention || '',
                        activityTitle: chunkData.activityTitle || chunkData.actual || '',
                        feeling: chunkData.feeling || '',
                        brainFog: chunkData.brainFog || 0,
                        valuableDetour: chunkData.isValuableDetour || false,
                        inventoryNote: chunkData.inventoryNote || '',
                        detrimentalDetour: chunkData.isDetrimentalDetour || false,
                        detrimentNote: chunkData.detrimentNote || '',
                        aiReflection: ''
                    };
                } else {
                    newLog[day][chunk.id] = {
                        intention: '', activityTitle: '', feeling: '', brainFog: 0,
                        matchesIntent: false, valuableDetour: false, inventoryNote: '',
                        detrimentalDetour: false, detrimentNote: '', aiReflection: ''
                    };
                }
            });
        });
        
        weeklyLog = newLog;
        if (activeWeekLabel) activeWeekLabel.textContent = `Historical Week: ${startStr} to ${endStr}`;
        if (resetWeekBtn) resetWeekBtn.classList.remove('hidden');
        renderDay('monday');
    };

    const renderCalendar = async () => {
        if (!calendarGrid) return;
        const year = calendarDate.getFullYear();
        const month = calendarDate.getMonth();
        
        monthlyLogData = await fetchMonthLogs(year, month);
        
        currentMonthHeader.textContent = new Date(year, month, 1).toLocaleString('default', { month: 'long', year: 'numeric' });
        
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        calendarGrid.innerHTML = '';
        
        for (let i = 0; i < firstDay; i++) {
            calendarGrid.appendChild(document.createElement('div'));
        }
        
        for (let i = 1; i <= daysInMonth; i++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
            const btn = document.createElement('button');
            const hasLogs = hasAnyLogsForDate(dateStr);
            const isComplete = isDayComplete(dateStr);
            
            btn.className = `relative p-2 aspect-square rounded-lg font-medium transition ${
                hasLogs ? 'bg-green-50 text-green-900 border border-green-200 hover:bg-green-100 shadow-sm'
                : 'bg-gray-50 text-gray-700 hover:bg-gray-200 border border-transparent'
            }`;
            
            btn.textContent = i;
            if (isComplete) {
                btn.innerHTML += `<div class="absolute bottom-1 right-1 text-xs">✅</div>`;
            }
            
            btn.addEventListener('click', () => {
                const clickedD = new Date(year, month, i);
                const dDay = clickedD.getDay(); // 0 is Sun, 1 is Mon
                const diff = clickedD.getDate() - dDay + (dDay === 0 ? -6:1);
                const monday = new Date(clickedD.setDate(diff));
                loadHistoricalWeek(monday);
            });
            calendarGrid.appendChild(btn);
        }
    };

    if (prevMonthBtn) prevMonthBtn.addEventListener('click', () => { calendarDate.setMonth(calendarDate.getMonth() - 1); renderCalendar(); });
    if (nextMonthBtn) nextMonthBtn.addEventListener('click', () => { calendarDate.setMonth(calendarDate.getMonth() + 1); renderCalendar(); });
    
    if (resetWeekBtn) resetWeekBtn.addEventListener('click', () => {
        activeWeekContext = 'current';
        calculateCurrentWeekMap();
        weeklyLog = getWeeklyLog();
        if (activeWeekLabel) activeWeekLabel.textContent = "Current Local Week";
        resetWeekBtn.classList.add('hidden');
        renderDay('monday');
    });

    const loadWeeklyExpectation = async () => {
        const mondayDate = activeDateMap['monday'];
        const textarea = document.getElementById('weekly-expectation-text');
        if (!mondayDate || !textarea) return;
        
        textarea.value = "Loading...";
        try {
            const response = await Auth.fetchWithAuth(`/api/planning/weekly?week_start_date=${mondayDate}`);
            if (response.ok) {
                const data = await response.json();
                textarea.value = data.data.expectation_text || "";
            } else {
                textarea.value = "";
            }
        } catch (e) {
            console.error("Failed to fetch weekly expectation", e);
            textarea.value = "";
        }
    };

    const saveWeeklyExpectationBtn = document.getElementById('save-weekly-expectation-btn');
    if (saveWeeklyExpectationBtn) {
        saveWeeklyExpectationBtn.addEventListener('click', async () => {
            const mondayDate = activeDateMap['monday'];
            const textarea = document.getElementById('weekly-expectation-text');
            const statusDiv = document.getElementById('weekly-expectation-status');
            if (!mondayDate || !textarea) return;

            const text = textarea.value;
            try {
                saveWeeklyExpectationBtn.disabled = true;
                saveWeeklyExpectationBtn.classList.add('opacity-50');
                
                const response = await Auth.fetchWithAuth('/api/planning/weekly', {
                    method: 'POST',
                    body: JSON.stringify({
                        week_start_date: mondayDate,
                        expectation_text: text
                    })
                });
                
                if (response.ok) {
                    statusDiv.classList.remove('hidden');
                    setTimeout(() => statusDiv.classList.add('hidden'), 3000);
                } else {
                    alert("Failed to save weekly expectation");
                }
            } catch (e) {
                console.error(e);
                alert("Error saving expectation.");
            } finally {
                saveWeeklyExpectationBtn.disabled = false;
                saveWeeklyExpectationBtn.classList.remove('opacity-50');
            }
        });
    }

    const init = async () => {
        calculateCurrentWeekMap();
        await renderCalendar();
        
        // Try to load current week from backend data (monthlyLogData) first
        const mondayDateStr = activeDateMap['monday'];
        let hasBackendData = false;
        
        if (monthlyLogData && monthlyLogData.weeks) {
            for (const week of Object.values(monthlyLogData.weeks)) {
                if (week[mondayDateStr] && week[mondayDateStr].chunks) {
                    hasBackendData = true;
                    loadHistoricalWeek(new Date(mondayDateStr + 'T00:00:00'));
                    activeWeekContext = 'current'; // Override historical status
                    if (activeWeekLabel) activeWeekLabel.textContent = "Current Local Week";
                    if (resetWeekBtn) resetWeekBtn.classList.add('hidden');
                    break;
                }
            }
        }
        
        if (!hasBackendData) {
            weeklyLog = getWeeklyLog();
        }

        const today = new Date().toLocaleString('en-us', { weekday: 'long' }).toLowerCase();
        const currentDay = DAYS.includes(today) ? today : 'monday';
        renderDay(currentDay);
    };

    init();
});