document.addEventListener('DOMContentLoaded', () => {
    if (!Auth.checkAuth()) return;

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
    };

    // --- Daily Journal Logic ---
    const loadJournal = async (dateStr) => {
        try {
            const token = localStorage.getItem('porter_token');
            const res = await fetch(`/api/journal/freeform?date=${dateStr}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
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
            const token = localStorage.getItem('porter_token');
            const res = await fetch('/api/journal/freeform', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
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
            const token = localStorage.getItem('porter_token');
            const response = await fetch(`/api/planning/weekly?week_start_date=${weekStartStr}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
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
            const token = localStorage.getItem('porter_token');
            const response = await fetch('/api/planning/weekly', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
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
            }
        } catch (e) {
            console.error("Failed to save expectation", e);
        } finally {
            saveExpBtn.innerHTML = originalText;
            saveExpBtn.disabled = false;
        }
    };

    saveExpBtn.addEventListener('click', saveWeeklyExpectation);

    init();
});
