document.addEventListener('DOMContentLoaded', () => {
    const dayNav = document.getElementById('day-nav');
    const dayViewContainer = document.getElementById('day-view-container');
    const currentDayHeader = document.getElementById('current-day-header');

    const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    const TIME_CHUNKS = [
        { id: 'late-night', label: 'Late Night (12am - 4am)' },
        { id: 'early-morning', label: 'Early Morning (4am - 8am)' },
        { id: 'late-morning', label: 'Late Morning (8am - 12pm)' },
        { id: 'afternoon', label: 'Afternoon (12pm - 4pm)' },
        { id: 'evening', label: 'Evening (4pm - 8pm)' },
        { id: 'early-night', label: 'Early Night (8pm - 12am)' }
    ];

    let weeklyLog = {};

    const getWeeklyLog = () => {
        const log = localStorage.getItem('weeklyLog');
        if (log) {
            return JSON.parse(log);
        } else {
            // Create a new empty log structure
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
            btn.classList.toggle('bg-blue-500', btn.dataset.day === day);
            btn.classList.toggle('text-white', btn.dataset.day === day);
            btn.classList.toggle('bg-gray-300', btn.dataset.day !== day);
        });

        currentDayHeader.textContent = day.charAt(0).toUpperCase() + day.slice(1);
        dayViewContainer.innerHTML = ''; // Clear previous content

        const dayData = weeklyLog[day];

        TIME_CHUNKS.forEach(chunk => {
            const chunkId = chunk.id;
            const chunkData = dayData[chunkId];
            const card = document.createElement('div');
            card.className = 'time-chunk-card bg-white p-6 rounded-lg shadow-md';
            card.dataset.day = day;
            card.dataset.chunk = chunkId;

            card.innerHTML = `
                <h3 class="text-xl font-bold mb-4">${chunk.label}</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- Intention Area -->
                    <div>
                        <label for="intention-${chunkId}" class="block text-sm font-medium text-gray-700 mb-1">My Intention</label>
                        <input type="text" id="intention-${chunkId}" value="${chunkData.intention}" class="intention-input mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" placeholder="e.g., Deep work on project X">
                    </div>

                    <!-- Actuals Form -->
                    <div class="space-y-4">
                        <h4 class="text-lg font-semibold">Log Actuals</h4>
                        <div>
                            <label for="actual-title-${chunkId}" class="block text-sm font-medium text-gray-700">Activity Title</label>
                            <input type="text" id="actual-title-${chunkId}" value="${chunkData.activityTitle}" class="actual-title-input mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" required>
                        </div>

                        <div>
                            <label class="block text-sm font-medium text-gray-700">Feeling</label>
                            <div class="mt-2 flex space-x-4">
                                ${['happy', 'neutral', 'sad'].map(feeling => `
                                <label class="inline-flex items-center">
                                    <input type="radio" name="feeling-${chunkId}" value="${feeling}" class="feeling-input form-radio h-5 w-5 text-indigo-600" ${chunkData.feeling === feeling ? 'checked' : ''}>
                                    <span class="ml-2 text-3xl">${feeling === 'happy' ? '😊' : feeling === 'neutral' ? '😐' : '😔'}</span>
                                </label>
                                `).join('')}
                            </div>
                        </div>

                        <div>
                            <label for="brain-fog-${chunkId}" class="block text-sm font-medium text-gray-700">Brain Fog: <span id="brain-fog-value-${chunkId}">${chunkData.brainFog}</span>%</label>
                            <input type="range" id="brain-fog-${chunkId}" min="0" max="100" step="10" value="${chunkData.brainFog}" class="brain-fog-slider w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                        </div>

                        <div>
                            <label class="inline-flex items-center">
                                <input type="checkbox" id="valuable-detour-${chunkId}" class="valuable-detour-checkbox form-checkbox h-5 w-5 text-blue-600" ${chunkData.valuableDetour ? 'checked' : ''}>
                                <span class="ml-2 text-sm font-medium text-gray-700">Valuable Detour?</span>
                            </label>
                        </div>

                        <div id="inventory-note-container-${chunkId}" class="${chunkData.valuableDetour ? '' : 'hidden'}">
                            <label for="inventory-note-${chunkId}" class="block text-sm font-medium text-gray-700">Inventory Note</label>
                            <textarea id="inventory-note-${chunkId}" rows="3" class="inventory-note-textarea mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">${chunkData.inventoryNote}</textarea>
                        </div>
                    </div>
                </div>

                <!-- Action Button & AI Output -->
                <div class="mt-6">
                    <button class="save-reflect-btn w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">Save & Reflect</button>
                    <div id="loader-${chunkId}" class="hidden text-center mt-4"><p>Processing...</p></div>
                    <div id="ai-output-${chunkId}" class="ai-output-container mt-4 p-4 bg-gray-50 rounded-lg min-h-[50px]">
                        <p class="text-gray-700">${chunkData.aiReflection || 'Your reflection will appear here.'}</p>
                    </div>
                </div>
            `;
            dayViewContainer.appendChild(card);
        });
    };

    const init = () => {
        weeklyLog = getWeeklyLog();
        const today = new Date().toLocaleString('en-us', { weekday: 'long' }).toLowerCase();
        const currentDay = DAYS.includes(today) ? today : 'monday';
        renderDay(currentDay);
    };

    // --- Event Handling ---

    // Day navigation
    dayNav.addEventListener('click', (e) => {
        if (e.target.classList.contains('day-btn')) {
            const day = e.target.dataset.day;
            renderDay(day);
        }
    });

    // Event delegation for dynamically created elements within the cards
    dayViewContainer.addEventListener('input', (e) => {
        // Update brain fog value display
        if (e.target.classList.contains('brain-fog-slider')) {
            const chunkId = e.target.closest('.time-chunk-card').dataset.chunk;
            document.getElementById(`brain-fog-value-${chunkId}`).textContent = e.target.value;
        }
    });

    dayViewContainer.addEventListener('change', (e) => {
        // Toggle inventory note visibility
        if (e.target.classList.contains('valuable-detour-checkbox')) {
            const chunkId = e.target.closest('.time-chunk-card').dataset.chunk;
            document.getElementById(`inventory-note-container-${chunkId}`).classList.toggle('hidden', !e.target.checked);
        }
    });

    dayViewContainer.addEventListener('click', async (e) => {
        // Handle Save & Reflect button clicks
        if (e.target.classList.contains('save-reflect-btn')) {
            const card = e.target.closest('.time-chunk-card');
            const day = card.dataset.day;
            const chunkId = card.dataset.chunk;

            // 1. Read all data from the card's form fields
            const intention = card.querySelector(`#intention-${chunkId}`).value;
            const activityTitle = card.querySelector(`#actual-title-${chunkId}`).value;
            const feelingRadio = card.querySelector(`input[name="feeling-${chunkId}"]:checked`);
            const feeling = feelingRadio ? feelingRadio.value : '';
            const brainFog = card.querySelector(`#brain-fog-${chunkId}`).value;
            const valuableDetour = card.querySelector(`#valuable-detour-${chunkId}`).checked;
            const inventoryNote = card.querySelector(`#inventory-note-${chunkId}`).value;

            // 2. Update the weeklyLog object
            const chunkData = {
                intention,
                activityTitle,
                feeling,
                brainFog,
                valuableDetour,
                inventoryNote,
                aiReflection: weeklyLog[day][chunkId].aiReflection // Preserve existing reflection for now
            };
            weeklyLog[day][chunkId] = chunkData;

            // 3. Save the entire log to localStorage
            saveWeeklyLog();

            // 4. Trigger the AI reflection process
            const loader = card.querySelector(`#loader-${chunkId}`);
            const aiOutputContainer = card.querySelector(`#ai-output-${chunkId}`);

            loader.classList.remove('hidden');
            aiOutputContainer.innerHTML = '';

            const journalEntry = `Intention: ${intention}. Activity: ${activityTitle}. Feeling: ${feeling}. Brain Fog: ${brainFog}%.`;

            try {
                const response = await fetch('http://localhost:5000/process_journal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ journal_entry: journalEntry, // string for CrewAI
                    log_data: {
                        day: day,
                        timeChunk: chunkId, // or the full label if you prefer
                        intention: chunkData.intention,
                        actual: chunkData.activityTitle,
                        feeling: chunkData.feeling,
                        brainFog: chunkData.brainFog,
                        isValuableDetour: chunkData.valuableDetour,
                        inventoryNote: chunkData.inventoryNote
                    }


                     }),
                });

                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

                const data = await response.json();
                const reflectionText = data.result.replace(/\n/g, '<br>');

                // 5. Display the AI response and save it
                aiOutputContainer.innerHTML = `<p class="text-gray-700">${reflectionText}</p>`;
                weeklyLog[day][chunkId].aiReflection = reflectionText;
                saveWeeklyLog();

            } catch (error) {
                console.error('Error processing journal entry:', error);
                aiOutputContainer.innerHTML = `<p class="text-red-500">Error fetching reflection. Please try again.</p>`;
            } finally {
                loader.classList.add('hidden');
            }
        }
    });


    init();
});
