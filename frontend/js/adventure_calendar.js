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

    const currentYearDisplay = document.getElementById('current-year-display');
    const yearlyGridContainer = document.getElementById('yearly-grid-container');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    // Modal
    const dayModal = document.getElementById('day-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalDateTitle = document.getElementById('modal-date-title');
    const modalBody = document.getElementById('modal-body');

    let activeYear = new Date().getFullYear();
    let yearlyDataCache = {}; // Cache to prevent excessive fetching
    
    // --- Initial Setup ---
    const init = async () => {
        await loadYear(activeYear);
    };

    // --- Data Fetching ---
    const loadYear = async (year) => {
        activeYear = year;
        currentYearDisplay.textContent = year;
        yearlyGridContainer.innerHTML = '';
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
                    // Transform list of nested month objects into a keyed map by month_id
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
            renderYearlyGrid(year, yearlyDataCache[year]);
        } catch (e) {
            console.error('Error fetching yearly logs:', e);
            yearlyGridContainer.innerHTML = '<p class="text-red-500 font-bold p-6">Failed to load temporal grid.</p>';
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    };

    // --- Rendering Logic ---
    const renderYearlyGrid = (year, yearData) => {
        yearlyGridContainer.innerHTML = '';

        // Build 12 Monthly blocks
        for (let monthIndex = 0; monthIndex < 12; monthIndex++) {
            const monthStr = `${year}-${String(monthIndex + 1).padStart(2, '0')}`;
            const monthDoc = yearData[monthStr] || {};
            
            const monthWrapper = document.createElement('div');
            monthWrapper.className = 'bg-white p-4 rounded-xl border border-gray-200 shadow-sm';
            
            const monthTitle = document.createElement('h3');
            monthTitle.className = 'text-xl font-bold text-gray-800 mb-4 tracking-tight border-b pb-2';
            monthTitle.textContent = MONTH_NAMES[monthIndex];
            monthWrapper.appendChild(monthTitle);
            
            // Sub-grid for days
            const daysGrid = document.createElement('div');
            daysGrid.className = 'grid grid-cols-7 gap-1 text-center';
            
            // Add DOW headers
            const dow = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            dow.forEach(d => {
                const header = document.createElement('div');
                header.className = 'text-xs font-bold text-gray-400 mb-1';
                header.textContent = d;
                daysGrid.appendChild(header);
            });

            // Date math
            const firstDay = new Date(year, monthIndex, 1).getDay();
            const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();

            // Blank padding for start
            for (let i = 0; i < firstDay; i++) {
                daysGrid.appendChild(document.createElement('div'));
            }

            // Valid days
            for (let day = 1; day <= daysInMonth; day++) {
                const dateStr = `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const dayBtn = document.createElement('button');
                dayBtn.className = 'relative p-2 aspect-square rounded font-medium text-sm transition hover:scale-105 active:scale-95 flex flex-col justify-center items-center gap-1';
                
                // Determine if this day has data
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

                if (hasData) {
                    dayBtn.classList.add('bg-indigo-50', 'text-indigo-900', 'border', 'border-indigo-200', 'hover:bg-indigo-100', 'cursor-pointer');
                    dayBtn.innerHTML = `<span>${day}</span><div class="w-2 h-2 bg-indigo-500 rounded-full shadow-sm mt-0.5"></div>`;
                    
                    dayBtn.addEventListener('click', () => {
                        openDayModal(dateStr, dayData);
                    });
                } else {
                    dayBtn.classList.add('bg-gray-50', 'text-gray-500', 'border', 'border-transparent', 'hover:bg-gray-100');
                    dayBtn.textContent = day;
                }

                daysGrid.appendChild(dayBtn);
            }

            monthWrapper.appendChild(daysGrid);
            yearlyGridContainer.appendChild(monthWrapper);
        }
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
    document.getElementById('prev-year-btn').addEventListener('click', () => loadYear(activeYear - 1));
    document.getElementById('next-year-btn').addEventListener('click', () => loadYear(activeYear + 1));
    
    closeModalBtn.addEventListener('click', closeDayModal);
    dayModal.addEventListener('click', (e) => {
        if (e.target === dayModal) closeDayModal();
    });

    init();
});
