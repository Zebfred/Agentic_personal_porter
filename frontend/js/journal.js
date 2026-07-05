document.addEventListener('DOMContentLoaded', () => {
    if (!Auth.isAuthenticated()) return;

    const datePicker = document.getElementById('journal-date-picker');
    const journalText = document.getElementById('daily-journal-text');
    const saveJournalBtn = document.getElementById('save-journal-btn');
    const journalStatus = document.getElementById('journal-status');

    const weekLabel = document.getElementById('active-week-label');
    const expText = document.getElementById('weekly-expectation-text');
    const saveExpBtn = document.getElementById('save-weekly-expectation-btn');
    const expStatus = document.getElementById('weekly-expectation-status');
    const expLastSaved = document.getElementById('weekly-expectation-last-saved');
    const dailyLastSaved = document.getElementById('daily-journal-last-saved');

    const formatDailyDate = (isoString) => {
        if (!isoString) return '';
        const d = new Date(isoString);
        const hh = String(d.getHours()).padStart(2, '0');
        const mm = String(d.getMinutes()).padStart(2, '0');
        const MM = String(d.getMonth() + 1).padStart(2, '0');
        const DD = String(d.getDate()).padStart(2, '0');
        const YYYY = d.getFullYear();
        return `${hh}:${mm} ${MM}/${DD}/${YYYY}`;
    };

    const formatWeeklyDate = (isoString) => {
        if (!isoString) return '';
        const d = new Date(isoString);
        const MM = String(d.getMonth() + 1).padStart(2, '0');
        const DD = String(d.getDate()).padStart(2, '0');
        const YYYY = d.getFullYear();
        return `${MM}/${DD}/${YYYY} Weekly Expectation`;
    };

    let currentWeekStartStr = '';

    const init = () => {
        // Init Date Picker to today
        const today = new Date();
        const todayStr = today.toISOString().split('T')[0];
        datePicker.value = todayStr;

        // Calculate Monday for current week
        const d = new Date();
        const dDay = d.getDay();
        const diff = d.getDate() - dDay + (dDay === 0 ? -6:1);
        const monday = new Date(d.setDate(diff));
        currentWeekStartStr = monday.toISOString().split('T')[0];
        
        weekLabel.textContent = `Week of ${currentWeekStartStr}`;

        loadJournal(todayStr);
        loadWeeklyExpectation(currentWeekStartStr);
        loadHistory();
    };

    // --- Daily Journal Logic ---
    const loadJournal = async (dateStr) => {
        try {
            const res = await Auth.fetchWithAuth(`/api/journal/freeform?date=${dateStr}`);
            if (res.ok) {
                const data = await res.json();
                journalText.value = data.data?.text || '';
                if (data.data?.updated_at) {
                    dailyLastSaved.textContent = formatDailyDate(data.data.updated_at);
                    dailyLastSaved.classList.remove('hidden');
                } else {
                    dailyLastSaved.classList.add('hidden');
                }
            } else {
                journalText.value = '';
                dailyLastSaved.classList.add('hidden');
            }
        } catch (e) {
            console.error("Failed to load journal", e);
            journalText.value = '';
            dailyLastSaved.classList.add('hidden');
        }
    };

    const saveJournal = async () => {
        const dateStr = datePicker.value;
        const text = journalText.value;
        if (!dateStr) return;

        const originalText = saveJournalBtn.innerHTML;
        saveJournalBtn.innerHTML = 'Saving...';
        saveJournalBtn.disabled = true;

        try {
            const res = await Auth.fetchWithAuth('/api/journal/freeform', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ date: dateStr, text: text })
            });

            if (res.ok) {
                const data = await res.json();
                if (data.updated_at) {
                    dailyLastSaved.textContent = formatDailyDate(data.updated_at);
                    dailyLastSaved.classList.remove('hidden');
                }
                journalStatus.classList.remove('hidden');
                setTimeout(() => {
                    journalStatus.classList.add('hidden');
                }, 3000);
                loadHistory(); // Refresh history
            }
        } catch (e) {
            console.error("Failed to save journal", e);
            alert("Failed to save journal.");
        } finally {
            saveJournalBtn.innerHTML = originalText;
            saveJournalBtn.disabled = false;
        }
    };

    datePicker.addEventListener('change', (e) => {
        loadJournal(e.target.value);
    });

    saveJournalBtn.addEventListener('click', saveJournal);

    // --- Weekly Expectation Logic ---
    const loadWeeklyExpectation = async (weekStartStr) => {
        try {
            const response = await Auth.fetchWithAuth(`/api/planning/weekly?week_start_date=${weekStartStr}`);
            if (response.ok) {
                const data = await response.json();
                expText.value = data.data?.expectation_text || "";
                if (data.data?.updated_at) {
                    expLastSaved.textContent = formatWeeklyDate(data.data.updated_at);
                    expLastSaved.classList.remove('hidden');
                } else {
                    expLastSaved.classList.add('hidden');
                }
            }
        } catch (e) {
            console.error("Failed to load expectation", e);
        }
    };

    const saveWeeklyExpectation = async () => {
        const text = expText.value;
        const originalText = saveExpBtn.innerHTML;
        saveExpBtn.innerHTML = 'Saving...';
        saveExpBtn.disabled = true;
        
        try {
            const response = await Auth.fetchWithAuth('/api/planning/weekly', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    week_start_date: currentWeekStartStr,
                    expectation_text: text
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.updated_at) {
                    expLastSaved.textContent = formatWeeklyDate(data.updated_at);
                    expLastSaved.classList.remove('hidden');
                }
                expStatus.classList.remove('hidden');
                setTimeout(() => {
                    expStatus.classList.add('hidden');
                }, 3000);
                loadHistory(); // Refresh history
            }
        } catch (e) {
            console.error("Failed to save expectation", e);
        } finally {
            saveExpBtn.innerHTML = originalText;
            saveExpBtn.disabled = false;
        }
    };

    saveExpBtn.addEventListener('click', saveWeeklyExpectation);

    // --- History Logic ---
    const loadHistory = async () => {
        const container = document.getElementById('journal-history-container');
        if (!container) return;
        
        try {
            const res = await Auth.fetchWithAuth('/api/journal/history?limit=15');
            if (res.ok) {
                const data = await res.json();
                renderHistory(data.data || []);
            }
        } catch (e) {
            console.error("Failed to load history", e);
        }
    };

    const renderHistory = (historyItems) => {
        const container = document.getElementById('journal-history-container');
        container.innerHTML = '';
        
        if (historyItems.length === 0) {
            container.innerHTML = '<p class="text-gray-500 italic">No past journals or expectations found.</p>';
            return;
        }

        historyItems.forEach(item => {
            const card = document.createElement('div');
            // Fiona Protocol: Glassmorphism and high contrast UI
            card.className = "bg-white bg-opacity-70 backdrop-blur-md p-6 rounded-2xl shadow-sm border border-gray-200 transition hover:shadow-md";
            
            const isJournal = item.type === 'journal';
            const icon = isJournal ? '📝' : '🎯';
            const title = isJournal ? `Journal: ${item.date}` : `Expectation: Week of ${item.date}`;
            const colorClass = isJournal ? 'text-blue-800' : 'text-indigo-900';
            const badgeClass = isJournal ? 'bg-blue-100 text-blue-800' : 'bg-indigo-100 text-indigo-800';

            // Show correlation ID if available (Hero lineage)
            const lineageBadge = item.correlation_id ? `<span class="text-xs font-mono bg-gray-100 text-gray-500 px-2 py-1 rounded ml-2" title="Data Lineage ID">🔗 ${item.correlation_id.substring(0,12)}...</span>` : '';

            card.innerHTML = `
                <div class="flex justify-between items-center mb-3">
                    <h4 class="text-lg font-bold ${colorClass} flex items-center gap-2">
                        <span>${icon}</span> ${title}
                    </h4>
                    <div class="flex items-center">
                        <span class="${badgeClass} text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider">${item.type}</span>
                        ${lineageBadge}
                    </div>
                </div>
                <div class="text-gray-700 whitespace-pre-wrap font-medium">${item.text}</div>
            `;
            container.appendChild(card);
        });
    };

    init();
});
