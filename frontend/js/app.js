document.addEventListener('DOMContentLoaded', () => {
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

    let weeklyLog = {};

    const getWeeklyLog = () => {
        const log = localStorage.getItem('weeklyLog');
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
                        inventoryNote: '',
                        aiReflection: ''
                    };
                });
            });
            return newLog;
        }
    };

    const saveWeeklyLog = () => {
        localStorage.setItem('weeklyLog', JSON.stringify(weeklyLog));
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

            card.innerHTML = `
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-bold text-gray-800">${chunk.label}</h3>
                </div>
                
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <!-- Intention Area -->
                    <div class="bg-gray-50 p-4 rounded-lg border border-gray-100">
                        <label for="intention-${chunkId}" class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">My Intention</label>
                        <textarea id="intention-${chunkId}" rows="2" class="intention-input w-full bg-white border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Sync from calendar or type here...">${chunkData.intention}</textarea>
                    </div>

                    <!-- Actuals Form -->
                    <div class="space-y-4">
                        <div>
                            <label for="actual-title-${chunkId}" class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Actual Activity</label>
                            <input type="text" id="actual-title-${chunkId}" value="${chunkData.activityTitle}" class="actual-title-input w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 outline-none" placeholder="What actually happened?">
                        </div>

                        <div class="flex items-center gap-4">
                            <div class="flex gap-2">
                                ${['happy', 'neutral', 'sad'].map(feeling => `
                                <label class="cursor-pointer">
                                    <input type="radio" name="feeling-${chunkId}" value="${feeling}" class="peer hidden" ${chunkData.feeling === feeling ? 'checked' : ''}>
                                    <span class="text-2xl opacity-40 peer-checked:opacity-100 hover:opacity-100 transition">${feeling === 'happy' ? '😊' : feeling === 'neutral' ? '😐' : '😔'}</span>
                                </label>
                                `).join('')}
                            </div>
                            
                            <div class="flex-grow">
                                <label class="flex justify-between text-xs font-bold text-gray-500 mb-1">
                                    <span>FOG: <span id="brain-fog-value-${chunkId}">${chunkData.brainFog}</span>%</span>
                                </label>
                                <input type="range" id="brain-fog-${chunkId}" min="0" max="100" step="10" value="${chunkData.brainFog}" class="brain-fog-slider w-full h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                            </div>
                        </div>

                        <div>
                            <label class="inline-flex items-center cursor-pointer">
                                <input type="checkbox" id="valuable-detour-${chunkId}" class="valuable-detour-checkbox form-checkbox h-4 w-4 text-blue-600 rounded" ${chunkData.valuableDetour ? 'checked' : ''}>
                                <span class="ml-2 text-sm font-medium text-gray-600">Mark as Valuable Detour</span>
                            </label>
                        </div>

                        <div id="inventory-note-container-${chunkId}" class="${chunkData.valuableDetour ? '' : 'hidden'}">
                            <label for="inventory-note-${chunkId}" class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Inventory Note</label>
                            <textarea id="inventory-note-${chunkId}" rows="2" class="inventory-note-textarea w-full border border-yellow-200 bg-yellow-50 rounded-md p-2 focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="What did you gain?">${chunkData.inventoryNote}</textarea>
                        </div>
                    </div>
                </div>

                <!-- Action Button & AI Output -->
                <div class="mt-6 pt-4 border-t border-gray-100">
                    <button class="save-reflect-btn w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition shadow-sm active:scale-95 flex justify-center items-center gap-2">
                        <span>✨</span> Save & Reflect
                    </button>
                    
                    <div id="loader-${chunkId}" class="hidden mt-4 text-center text-blue-600 font-medium animate-pulse">
                        Thinking...
                    </div>
                    
                    <div id="ai-output-${chunkId}" class="ai-output-container mt-4 p-4 bg-blue-50 rounded-lg border-l-4 border-blue-400 ${chunkData.aiReflection ? '' : 'hidden'}">
                        <p class="text-gray-700 italic text-sm">${chunkData.aiReflection || ''}</p>
                    </div>
                </div>
            `;
            dayViewContainer.appendChild(card);
        });
    };

    /**
     * SMART CALENDAR SYNC LOGIC
     */
    const fetchCalendarEvents = async (day) => {
        try {
            // Calculate the date for the selected day
            const today = new Date();
            const dayIndex = DAYS.indexOf(day);
            const currentDayIndex = (today.getDay() + 6) % 7; // Adjust to make Monday index 0
            const daysDiff = dayIndex - currentDayIndex;
            const targetDate = new Date(today);
            targetDate.setDate(today.getDate() + daysDiff);
            
            const dateStr = targetDate.toISOString().split('T')[0];
            
            console.log(`Fetching calendar events for ${day} (${dateStr})...`);
            
            // Using the endpoint from server.py
            const response = await fetch(`http://localhost:5000/get_calendar_events?date=${dateStr}`);
            
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
            const intentionInput = document.getElementById(`intention-${chunkId}`);
            
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

    // 3. UI Interactions (Delegation)
    dayViewContainer.addEventListener('input', (e) => {
        if (e.target.classList.contains('brain-fog-slider')) {
            const chunkId = e.target.closest('.time-chunk-card').dataset.chunk;
            document.getElementById(`brain-fog-value-${chunkId}`).textContent = e.target.value;
        }
    });

    dayViewContainer.addEventListener('change', (e) => {
        if (e.target.classList.contains('valuable-detour-checkbox')) {
            const chunkId = e.target.closest('.time-chunk-card').dataset.chunk;
            document.getElementById(`inventory-note-container-${chunkId}`).classList.toggle('hidden', !e.target.checked);
        }
    });

    // 4. MAIN ACTION: Save & Reflect
    dayViewContainer.addEventListener('click', async (e) => {
        if (e.target.classList.contains('save-reflect-btn')) {
            const btn = e.target;
            const card = btn.closest('.time-chunk-card');
            const day = card.dataset.day;
            const chunkId = card.dataset.chunk;

            // Gather Data
            const intention = card.querySelector(`#intention-${chunkId}`).value;
            const activityTitle = card.querySelector(`#actual-title-${chunkId}`).value;
            const feelingRadio = card.querySelector(`input[name="feeling-${chunkId}"]:checked`);
            const feeling = feelingRadio ? feelingRadio.value : '';
            const brainFog = card.querySelector(`#brain-fog-${chunkId}`).value;
            const valuableDetour = card.querySelector(`#valuable-detour-${chunkId}`).checked;
            const inventoryNote = card.querySelector(`#inventory-note-${chunkId}`).value;

            // Update Local State
            const chunkData = {
                intention, activityTitle, feeling, brainFog, valuableDetour, inventoryNote,
                aiReflection: weeklyLog[day][chunkId].aiReflection
            };
            weeklyLog[day][chunkId] = chunkData;
            saveWeeklyLog();

            // UI Feedback
            const loader = card.querySelector(`#loader-${chunkId}`);
            const aiOutputContainer = card.querySelector(`#ai-output-${chunkId}`);
            
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
            loader.classList.remove('hidden');
            aiOutputContainer.classList.add('hidden');

            // Construct Payloads - CORRECT KEYS FOR NEO4J & SERVER
            const journalEntry = `Intention: ${intention}. Actual: ${activityTitle}. Feeling: ${feeling}. Brain Fog: ${brainFog}%.`;
            const logDataForDb = {
                day, timeChunk: chunkId, intention, actual: activityTitle,
                feeling, brainFog: parseInt(brainFog), isValuableDetour: valuableDetour, inventoryNote
            };

            try {
                const response = await fetch('http://localhost:5000/process_journal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        journal_entry_text: journalEntry, // FIXED: Matches server expectation
                        log_data: logDataForDb 
                    }),
                });

                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

                const data = await response.json();
                
                // Handle different potential response structures
                const reflectionText = (data.result || data.reflection || "Insight recorded.").replace(/\n/g, '<br>');

                // Display
                aiOutputContainer.innerHTML = `<p class="text-gray-700 italic leading-relaxed">${reflectionText}</p>`;
                aiOutputContainer.classList.remove('hidden');
                
                // Save Result
                weeklyLog[day][chunkId].aiReflection = reflectionText;
                saveWeeklyLog();

            } catch (error) {
                console.error('Error processing journal entry:', error);
                aiOutputContainer.innerHTML = `<p class="text-red-500 font-bold">⚠️ Connection Error. Ensure server is running.</p>`;
                aiOutputContainer.classList.remove('hidden');
            } finally {
                loader.classList.add('hidden');
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }
    });

    // Init
    const init = async () => {
        weeklyLog = getWeeklyLog();
        const today = new Date().toLocaleString('en-us', { weekday: 'long' }).toLowerCase();
        const currentDay = DAYS.includes(today) ? today : 'monday';
        renderDay(currentDay);
    };

    init();
});