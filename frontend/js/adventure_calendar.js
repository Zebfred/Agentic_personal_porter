document.addEventListener('DOMContentLoaded', () => {
    // Utilities
    const escapeHTML = (str) => {
        if (!str) return '';
        return String(str).replace(/[&<>'"]/g,
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag])
        );
    };

    const MONTH_NAMES = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    const calendarTitle = document.getElementById('calendar-title');
    const monthlyGridContainer = document.getElementById('monthly-grid-container');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    // Controls
    const prevMonthBtn = document.getElementById('prev-month-btn');
    const nextMonthBtn = document.getElementById('next-month-btn');
    const todayBtn = document.getElementById('today-btn');

    // Modal
    const dayModal = document.getElementById('day-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalDateTitle = document.getElementById('modal-date-title');
    const modalBody = document.getElementById('modal-body');

    let activeYear = new Date().getFullYear();
    let activeMonth = new Date().getMonth(); // 0-11
    let yearlyDataCache = {}; // Cache to prevent excessive fetching
    
    // --- Initial Setup ---
    const init = async () => {
        await loadMonthData(activeYear, activeMonth);
    };

    // --- Data Fetching ---
    const loadMonthData = async (year, month) => {
        calendarTitle.textContent = `${MONTH_NAMES[month]} ${year}`;
        monthlyGridContainer.innerHTML = '';
        loadingSpinner.classList.remove('hidden');

        try {
            // Check cache first
            if (!yearlyDataCache[year]) {
                const response = await fetch(`/api/logs/year?year=${year}`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('porter_token')}` }
                });
                
                if (response.ok) {
                    const payload = await response.json();
                    let formattedData = {};
                    if (payload.status === 'success' && payload.data) {
                        payload.data.forEach(monthDoc => {
                            formattedData[monthDoc.month_id] = monthDoc;
                        });
                    }
                    yearlyDataCache[year] = formattedData;
                } else {
                    console.error('Failed to fetch yearly block', response.status);
                    yearlyDataCache[year] = {};
                }
            }
            renderMonthGrid(year, month, yearlyDataCache[year]);
        } catch (e) {
            console.error('Error fetching yearly logs:', e);
            monthlyGridContainer.innerHTML = '<div class="col-span-7 bg-white p-6"><p class="text-red-500 font-bold text-center">Failed to load temporal grid.</p></div>';
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    };

    // --- Rendering Logic ---
    const renderMonthGrid = (year, month, yearData) => {
        monthlyGridContainer.innerHTML = '';
        const monthStr = `${year}-${String(month + 1).padStart(2, '0')}`;
        const monthDoc = yearData[monthStr] || {};
        
        // Date math
        const firstDay = new Date(year, month, 1).getDay(); // 0 (Sun) to 6 (Sat)
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const daysInPrevMonth = new Date(year, month, 0).getDate();

        // Total weeks to show: usually 5, sometimes 6
        const totalCells = Math.ceil((firstDay + daysInMonth) / 7) * 7;
        
        // Render padding (previous month)
        for (let i = firstDay - 1; i >= 0; i--) {
            const padDay = daysInPrevMonth - i;
            const cell = createDayCell(null, padDay, true);
            monthlyGridContainer.appendChild(cell);
        }

        // Render actual days
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            
            // Extract data
            let hasData = false;
            let dayData = null;
            if (monthDoc.weeks) {
                for (const week of Object.values(monthDoc.weeks)) {
                    if (week[dateStr] && week[dateStr].chunks && Object.keys(week[dateStr].chunks).length > 0) {
                        hasData = true;
                        dayData = week[dateStr];
                        break;
                    }
                }
            }
            
            const cell = createDayCell(dateStr, day, false, hasData, dayData);
            monthlyGridContainer.appendChild(cell);
        }

        // Render padding (next month)
        const filledCells = firstDay + daysInMonth;
        let nextMonthDay = 1;
        for (let i = filledCells; i < totalCells; i++) {
            const cell = createDayCell(null, nextMonthDay++, true);
            monthlyGridContainer.appendChild(cell);
        }
    };

    const createDayCell = (dateStr, dayNum, isPadding, hasData = false, dayData = null) => {
        const cell = document.createElement('div');
        cell.className = 'day-cell bg-white hover:bg-gray-50 flex flex-col p-2 transition group';
        
        if (isPadding) {
            cell.classList.add('bg-gray-50', 'text-gray-400');
            cell.innerHTML = `<span class="text-sm font-medium self-end opacity-50">${dayNum}</span>`;
            return cell;
        }

        // Highlight today
        const today = new Date();
        const isToday = (today.getFullYear() === activeYear && today.getMonth() === activeMonth && today.getDate() === dayNum);
        
        const dateEl = document.createElement('span');
        dateEl.className = 'text-sm font-medium self-end mb-1 z-10 ' + (isToday ? 'bg-indigo-600 text-white rounded-full w-6 h-6 flex items-center justify-center shadow-md' : 'text-gray-700');
        dateEl.textContent = dayNum;
        cell.appendChild(dateEl);

        if (hasData) {
            cell.classList.add('cursor-pointer');
            cell.addEventListener('click', () => {
                openDayModal(dateStr, dayData);
            });

            const chunkContainer = document.createElement('div');
            chunkContainer.className = 'flex flex-col gap-1 overflow-y-auto custom-scrollbar no-scrollbar text-xs mt-1';
            
            const timeOrdered = ['late-night', 'early-morning', 'late-morning', 'afternoon', 'evening', 'early-night'];
            timeOrdered.forEach(chunkId => {
                if (dayData.chunks[chunkId]) {
                    const chunk = dayData.chunks[chunkId];
                    const pill = document.createElement('div');
                    let colorClass = 'bg-blue-50 text-blue-800 border-blue-200';
                    if (chunk.isValuableDetour) colorClass = 'bg-yellow-50 text-yellow-800 border-yellow-200';
                    if (chunk.isDetrimentalDetour) colorClass = 'bg-red-50 text-red-800 border-red-200';
                    
                    pill.className = `truncate px-1.5 py-0.5 rounded border ${colorClass} font-semibold shadow-sm`;
                    pill.textContent = chunk.activityTitle || chunk.actual || chunkId.replace('-', ' ');
                    chunkContainer.appendChild(pill);
                }
            });
            cell.appendChild(chunkContainer);
        } else {
            cell.innerHTML += `<div class="flex-grow flex items-center justify-center opacity-0 group-hover:opacity-100 transition"><span class="text-xs text-gray-400 font-bold tracking-wider uppercase">+ Log Details</span></div>`;
        }

        return cell;
    };

    // --- Modal Logic ---
    const openDayModal = (dateStr, dayData) => {
        modalDateTitle.textContent = new Date(dateStr).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        modalBody.innerHTML = '';
        
        const chunks = dayData.chunks || {};
        const timeOrdered = ['late-night', 'early-morning', 'late-morning', 'afternoon', 'evening', 'early-night'];
        const chunkLabels = {
            'late-night': 'Late Night',
            'early-morning': 'Early Morning',
            'late-morning': 'Late Morning',
            'afternoon': 'Afternoon',
            'evening': 'Evening',
            'early-night': 'Early Night'
        };

        let foundAny = false;
        
        timeOrdered.forEach(chunkId => {
            const chunk = chunks[chunkId];
            if (chunk) {
                foundAny = true;
                const activityVal = chunk.activityTitle || chunk.actual || "No actual recorded";
                
                const card = document.createElement('div');
                card.className = "bg-gray-50 p-4 rounded-lg border border-gray-200";
                
                let highlightClass = "";
                if (chunk.isValuableDetour) highlightClass = "border-l-4 border-l-yellow-400";
                else if (chunk.isDetrimentalDetour) highlightClass = "border-l-4 border-l-red-500";
                else highlightClass = "border-l-4 border-l-green-400";
                
                card.classList.add(...highlightClass.split(' '));

                card.innerHTML = `
                    <div class="flex justify-between items-center mb-2">
                        <strong class="text-sm text-gray-700 tracking-wider uppercase">${chunkLabels[chunkId]}</strong>
                        <span class="text-xs bg-white border px-2 py-1 rounded shadow-sm text-gray-600 font-bold">FOG: ${chunk.brainFog || 0}%</span>
                    </div>
                    <div class="space-y-1 text-sm text-gray-800">
                        <p><span class="opacity-50">Intended:</span> ${escapeHTML(chunk.intention)}</p>
                        <p class="font-bold"><span class="font-normal opacity-50">Actual:</span> ${escapeHTML(activityVal)}</p>
                    </div>
                `;

                if (chunk.isValuableDetour && chunk.inventoryNote) {
                    card.innerHTML += `<div class="mt-2 text-xs bg-yellow-50 text-yellow-800 p-2 rounded border border-yellow-200"><strong>Valuable:</strong> ${escapeHTML(chunk.inventoryNote)}</div>`;
                }
                if (chunk.isDetrimentalDetour && chunk.detrimentNote) {
                    card.innerHTML += `<div class="mt-2 text-xs bg-red-50 text-red-800 p-2 rounded border border-red-200"><strong>Detrimental:</strong> ${escapeHTML(chunk.detrimentNote)}</div>`;
                }

                modalBody.appendChild(card);
            }
        });

        if (!foundAny) {
            modalBody.innerHTML = '<p class="text-gray-500 italic">Data structure malformed or empty.</p>';
        }

        dayModal.classList.remove('hidden');
        // Small delay for transition
        setTimeout(() => {
            document.getElementById('day-modal-content').classList.remove('scale-95');
        }, 10);
    };

    const closeDayModal = () => {
        document.getElementById('day-modal-content').classList.add('scale-95');
        setTimeout(() => {
            dayModal.classList.add('hidden');
        }, 300);
    };

    // --- Listeners ---
    prevMonthBtn.addEventListener('click', () => {
        activeMonth--;
        if (activeMonth < 0) {
            activeMonth = 11;
            activeYear--;
        }
        loadMonthData(activeYear, activeMonth);
    });

    nextMonthBtn.addEventListener('click', () => {
        activeMonth++;
        if (activeMonth > 11) {
            activeMonth = 0;
            activeYear++;
        }
        loadMonthData(activeYear, activeMonth);
    });

    todayBtn.addEventListener('click', () => {
        const today = new Date();
        activeYear = today.getFullYear();
        activeMonth = today.getMonth();
        loadMonthData(activeYear, activeMonth);
    });
    
    closeModalBtn.addEventListener('click', closeDayModal);
    dayModal.addEventListener('click', (e) => {
        if (e.target === dayModal) closeDayModal();
    });

    init();
});
