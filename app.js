document.addEventListener('DOMContentLoaded', () => {
    // --- Global Variables ---
    let currentUserId = null;
    let weeklyLog = {};

    // --- DOM Elements ---
    const authContainer = document.getElementById('auth-container');
    const appContainer = document.getElementById('app-container');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const loginTab = document.getElementById('login-tab');
    const registerTab = document.getElementById('register-tab');
    const logoutBtn = document.getElementById('logout-btn');
    const userGreeting = document.getElementById('user-greeting');

    // --- Event Listeners ---
    const dayNav = document.getElementById('day-nav');
    const dayViewContainer = document.getElementById('day-view-container');
    const currentDayHeader = document.getElementById('current-day-header');
    
    // --- Constants ---
    const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    const TIME_CHUNKS = [
        { id: 'late-night', label: 'Late Night (12am - 4am)' },
        { id: 'early-morning', label: 'Early Morning (4am - 8am)' },
        { id: 'late-morning', label: 'Late Morning (8am - 12pm)' },
        { id: 'afternoon', label: 'Afternoon (12pm - 4pm)' },
        { id: 'evening', label: 'Evening (4pm - 8pm)' },
        { id: 'early-night', label: 'Early Night (8pm - 12am)' }
    ];
    const API_BASE_URL = 'http://127.0.0.1:5000';

    // --- Authentication Logic ---

    const checkLoginStatus = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/check_session`, { credentials: 'include' });
            const data = await response.json();

            if (data.logged_in) {
                currentUserId = data.user_id;
                showApp();
                initApp(); // Initialize the main application
            } else {
                showAuth();
            }
        } catch (error) {
            console.error('Error checking session status:', error);
            showAuth();
        }
    };

    const showApp = () => {
        authContainer.classList.add('hidden');
        appContainer.classList.remove('hidden');
        userGreeting.textContent = `Hello, ${currentUserId}!`;
    };

    const showAuth = () => {
        authContainer.classList.remove('hidden');
        appContainer.classList.add('hidden');
        currentUserId = null;
    };

    loginTab.addEventListener('click', () => {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        loginTab.classList.add('border-b-2', 'border-blue-500', 'text-blue-500');
        registerTab.classList.remove('border-b-2', 'border-blue-500', 'text-blue-500');
    });

    registerTab.addEventListener('click', () => {
        registerForm.classList.remove('hidden');
        loginForm.classList.add('hidden');
        registerTab.classList.add('border-b-2', 'border-green-500', 'text-green-500');
        loginTab.classList.remove('border-b-2', 'border-blue-500', 'text-blue-500');
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const messageEl = document.getElementById('register-message');

        try {
            const response = await fetch(`${API_BASE_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });
            const data = await response.json();
            if (response.ok) {
                messageEl.textContent = 'Registration successful! Please log in.';
                messageEl.className = 'text-green-500 text-sm mt-2';
                registerForm.reset();
                loginTab.click(); // Switch to login tab
            } else {
                throw new Error(data.error || 'Registration failed');
            }
        } catch (error) {
            messageEl.textContent = error.message;
            messageEl.className = 'text-red-500 text-sm mt-2';
        }
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');

        try {
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
                credentials: 'include' // Important for sending session cookie
            });
            const data = await response.json();
            if (response.ok) {
                currentUserId = data.user_id;
                showApp();
                initApp();
            } else {
                throw new Error(data.error || 'Login failed');
            }
        } catch (error) {
            errorEl.textContent = error.message;
        }
    });

    logoutBtn.addEventListener('click', async () => {
        try {
            await fetch(`${API_BASE_URL}/logout`, {
                method: 'POST',
                credentials: 'include'
            });
            showAuth();
        } catch (error) {
            console.error('Logout failed:', error);
        }
    });


    // --- Main Application Logic ---

    // let weeklyLog = {};

    // User-specific local storage
    const getWeeklyLog = () => {
        if (!currentUserId) return createEmptyLog();
        const log = localStorage.getItem(`weeklyLog_${currentUserId}`);
        return log ? JSON.parse(log) : createEmptyLog();
    };

    const saveWeeklyLog = () => {
        if (!currentUserId) return;
        localStorage.setItem(`weeklyLog_${currentUserId}`, JSON.stringify(weeklyLog));
    };

    const createEmptyLog = () => {
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

 

    // --- NEW: Google Calendar Integration ---
    const fetchCalendarEvents = async (day) => {
        const dayIndex = DAYS.indexOf(day);

        // This logic calculates the actual date for the selected day in the current week.
        const today = new Date();
        const currentDayIndex = (today.getDay() + 6) % 7; // Monday = 0, Sunday = 6
        const dateOffset = dayIndex - currentDayIndex;

        const targetDate = new Date();
        targetDate.setDate(today.getDate() + dateOffset);

        // Format the date as YYYY-MM-DD
        const dateString = targetDate.toISOString().split('T')[0];

        console.log(`Fetching calendar events for ${day} (${dateString})...`);
        try {
            const response = await fetch(`http://localhost:5000/get_calendar_events?date=${dateString}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.events && data.events.length > 0) {
                const eventsString = data.events.join('; ');
                // We'll put all of the day's events into the first non-empty intention field,
                // or just the first field of the day. A simple but effective starting point.
                const targetChunkId = TIME_CHUNKS[2].id; // Default to 'late-morning'
                weeklyLog[day][targetChunkId].intention = eventsString;

                saveWeeklyLog();
                // We need to re-render the view to show the newly fetched intentions.
                renderDay(day);
                console.log(`Successfully populated intentions for ${day} with: ${eventsString}`);
            } else {
                console.log(`No events found for ${day}.`);
            }
        } catch (error) {
            console.error('Could not fetch Google Calendar events:', error);
            // You could show a small, non-intrusive error message to the user here.
        }
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

        const dayData = weeklyLog[day] || {};

        TIME_CHUNKS.forEach(chunk => {
            const chunkId = chunk.id;
            const chunkData = dayData[chunkId] || {};
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
                        <input type="text" id="intention-${chunkId}" value="${chunkData.intention || ''}" class="intention-input mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" placeholder="e.g., Deep work on project X">
                    </div>

                    <!-- Actuals Form -->
                    <div class="space-y-4">
                        <h4 class="text-lg font-semibold">Log Actuals</h4>
                        <div>
                            <label for="actual-title-${chunkId}" class="block text-sm font-medium text-gray-700">Activity Title</label>
                            <input type="text" id="actual-title-${chunkId}" value="${chunkData.activityTitle || ''}" class="actual-title-input mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" required>
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
                            <label for="brain-fog-${chunkId}" class="block text-sm font-medium text-gray-700">Brain Fog: <span id="brain-fog-value-${chunkId}">${chunkData.brainFog || 0}</span>%</label>
                            <input type="range" id="brain-fog-${chunkId}" min="0" max="100" step="10" value="${chunkData.brainFog || 0}" class="brain-fog-slider w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                        </div>

                        <div>
                            <label class="inline-flex items-center">
                                <input type="checkbox" id="valuable-detour-${chunkId}" class="valuable-detour-checkbox form-checkbox h-5 w-5 text-blue-600" ${chunkData.valuableDetour ? 'checked' : ''}>
                                <span class="ml-2 text-sm font-medium text-gray-700">Valuable Detour?</span>
                            </label>
                        </div>

                        <div id="inventory-note-container-${chunkId}" class="${chunkData.valuableDetour ? '' : 'hidden'}">
                            <label for="inventory-note-${chunkId}" class="block text-sm font-medium text-gray-700">Inventory Note</label>
                            <textarea id="inventory-note-${chunkId}" rows="3" class="inventory-note-textarea mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">${chunkData.inventoryNote || ''}</textarea>
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

    const initApp = () => {
        weeklyLog = getWeeklyLog();
        const today = new Date().toLocaleString('en-us', { weekday: 'long' }).toLowerCase();
        const currentDay = DAYS.includes(today) ? today : 'monday';
        renderDay(currentDay);
        // Automatically fetch events for the current day on load
        fetchCalendarEvents(currentDay);
    };

    // --- Event Handling for Main App ---

    // Day navigation
    dayNav.addEventListener('click', (e) => {
        if (e.target.classList.contains('day-btn')) {
            const day = e.target.dataset.day;
            renderDay(day);
            // Fetch events every time a new day is clicked
            fetchCalendarEvents(currentDay);
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
                intention, activityTitle,
                feeling, brainFog,
                valuableDetour, inventoryNote,
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
            const logData = {
                day, timeChunk: chunkId, intention, actual: activityTitle, feeling, brainFog,
                isValuableDetour: valuableDetour, inventoryNote
            };

            try {
                const response = await fetch(`${API_BASE_URL}/process_journal`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        journal_entry: journalEntry, // string for CrewAI
                        log_data: logData  // structured data for context
                    }),
                    credentials: 'include' // Important for sending session cookie                    
                });

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.error || `HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                const reflectionText = data.reflection.replace(/\n/g, '<br>');

                // 5. Display the AI response and save it
                aiOutputContainer.innerHTML = `<p class="text-gray-700">${reflectionText}</p>`;
                weeklyLog[day][chunkId].aiReflection = reflectionText;
                saveWeeklyLog();

            } catch (error) {
                console.error('Error processing journal entry:', error);
                aiOutputContainer.innerHTML = `<p class="text-red-500">${error.message}</p>`;
            } finally {
                loader.classList.add('hidden');
            }
        }
    });

    // --- Initial Load ---
    //init();
    checkLoginStatus();
});
