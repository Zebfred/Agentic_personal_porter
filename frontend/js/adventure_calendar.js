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
                const response = await Auth.fetchWithAuth(`/api/logs/year?year=${year}`);
                
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
            
            let hasReflection = false;
            if (monthDoc.reflections && monthDoc.reflections.includes(dateStr)) {
                hasReflection = true;
            }
            
            const cell = createDayCell(dateStr, day, false, hasData, dayData, hasReflection);
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

    const createDayCell = (dateStr, dayNum, isPadding, hasData = false, dayData = null, hasReflection = false) => {
        const cell = document.createElement('div');
        cell.className = 'day-cell bg-surface hover:bg-surface-hover flex flex-col p-2 transition group rounded-xl shadow-sm border border-border min-h-[120px]';
        
        if (isPadding) {
            cell.classList.add('bg-background', 'text-muted');
            cell.classList.remove('bg-surface', 'hover:bg-surface-hover');
            cell.innerHTML = `<span class="text-sm font-medium self-end opacity-50">${dayNum}</span>`;
            return cell;
        }

        // Highlight today
        const today = new Date();
        const isToday = (today.getFullYear() === activeYear && today.getMonth() === activeMonth && today.getDate() === dayNum);
        
        const headerContainer = document.createElement('div');
        headerContainer.className = 'flex justify-between items-start mb-1';
        
        // Left side badge
        const badgeSpan = document.createElement('span');
        if (hasReflection) {
            badgeSpan.className = 'text-green-500 font-bold text-lg leading-none';
            badgeSpan.innerHTML = '✅';
            badgeSpan.title = "Sovereign Report Generated";
        } else {
            badgeSpan.className = 'w-4 h-4'; // spacer
        }
        
        // Right side date number
        const dateEl = document.createElement('span');
        dateEl.className = 'text-sm font-medium z-10 ' + (isToday ? 'bg-primary text-on-primary rounded-full w-6 h-6 flex items-center justify-center shadow-md' : 'text-main');
        dateEl.textContent = dayNum;
        
        headerContainer.appendChild(badgeSpan);
        headerContainer.appendChild(dateEl);
        cell.appendChild(headerContainer);

        if (hasData || hasReflection) {
            cell.classList.add('cursor-pointer');
            cell.addEventListener('click', () => {
                openDayModal(dateStr, dayData || {chunks: {}});
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
    const openDayModal = async (dateStr, dayData) => {
        modalDateTitle.textContent = new Date(dateStr).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        modalBody.innerHTML = '';
        
        // 1. Render Sovereign Reflection if exists
        const reflectionContainer = document.createElement('div');
        reflectionContainer.id = "modal-reflection-container";
        reflectionContainer.className = "mb-6 hidden bg-indigo-50 border border-indigo-100 rounded-xl p-4";
        reflectionContainer.innerHTML = `
            <h4 class="text-indigo-900 font-bold mb-2 flex items-center gap-2">
                <span>👑</span> Sovereign Daily Report
            </h4>
            <div id="modal-reflection-content" class="text-sm text-indigo-800 whitespace-pre-wrap">Loading...</div>
        `;
        modalBody.appendChild(reflectionContainer);
        
        // Fetch reflection
        try {
            const res = await Auth.fetchWithAuth(`/api/journal/reflection?date=${dateStr}`);
            if (res.ok) {
                const data = await res.json();
                if (data.data && data.data.reflection_text) {
                    let textHtml = escapeHTML(data.data.reflection_text).replace(/\\n/g, '<br>');
                    if (data.data.correlation_id) {
                        textHtml += `<div class="mt-3 text-right"><span class="text-xs font-mono bg-indigo-200 text-indigo-800 px-2 py-1 rounded">🔗 ${data.data.correlation_id.substring(0,12)}...</span></div>`;
                    }
                    reflectionContainer.querySelector('#modal-reflection-content').innerHTML = textHtml;
                    reflectionContainer.classList.remove('hidden');
                }
            }
        } catch (e) {
            console.error("Failed to load reflection for modal", e);
        }

        // 2. Render Freeform Journal if exists
        const freeformContainer = document.createElement('div');
        freeformContainer.id = "modal-freeform-container";
        freeformContainer.className = "mb-6 hidden bg-blue-50 border border-blue-100 rounded-xl p-4";
        freeformContainer.innerHTML = `
            <h4 class="text-blue-900 font-bold mb-2 flex items-center gap-2">
                <span>📝</span> Journal Log
            </h4>
            <div id="modal-freeform-content" class="text-sm text-blue-800 whitespace-pre-wrap">Loading...</div>
        `;
        modalBody.appendChild(freeformContainer);
        
        try {
            const res = await Auth.fetchWithAuth(`/api/journal/freeform?date=${dateStr}`);
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'success' && data.data && data.data.text) {
                    let textHtml = escapeHTML(data.data.text).replace(/\\n/g, '<br>');
                    if (data.data.correlation_id) {
                        textHtml += `<div class="mt-3 text-right"><span class="text-xs font-mono bg-blue-200 text-blue-800 px-2 py-1 rounded">🔗 ${data.data.correlation_id.substring(0,12)}...</span></div>`;
                    }
                    freeformContainer.querySelector('#modal-freeform-content').innerHTML = textHtml;
                    freeformContainer.classList.remove('hidden');
                }
            }
        } catch (e) {
            console.error("Failed to load freeform journal for modal", e);
        }

        // 3. Render Time Chunks
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

        let foundAny = Object.keys(chunks).length > 0;
        
        timeOrdered.forEach(chunkId => {
            const chunk = chunks[chunkId];
            if (chunk) {
                const activityVal = chunk.activityTitle || chunk.actual || "No actual recorded";
                
                const card = document.createElement('div');
                card.className = "bg-gray-50 p-4 rounded-lg border border-gray-200 mb-4 relative";
                
                let highlightClass = "";
                if (chunk.isValuableDetour) highlightClass = "border-l-4 border-l-yellow-400";
                else if (chunk.isDetrimentalDetour) highlightClass = "border-l-4 border-l-red-500";
                else highlightClass = "border-l-4 border-l-green-400";
                
                card.classList.add(...highlightClass.split(' '));

                card.innerHTML = `
                    <div class="flex justify-between items-center mb-2">
                        <strong class="text-sm text-gray-700 tracking-wider uppercase">${chunkLabels[chunkId]}</strong>
                        <div class="flex items-center gap-2">
                            <span class="text-xs bg-white border px-2 py-1 rounded shadow-sm text-gray-600 font-bold">FOG: ${chunk.brainFog || 0}%</span>
                            <button class="edit-chunk-btn text-xs text-blue-600 hover:text-blue-800 bg-blue-50 px-2 py-1 rounded border border-blue-200 shadow-sm transition">Edit</button>
                        </div>
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
                
                // Add Edit Form (Hidden by default)
                const editForm = document.createElement('div');
                editForm.className = "hidden mt-4 pt-4 border-t border-gray-200";
                editForm.innerHTML = `
                    <div class="space-y-3">
                        <div>
                            <label class="block text-xs font-bold text-gray-700 uppercase">Intention</label>
                            <input type="text" class="w-full border p-1.5 rounded text-sm" value="${escapeHTML(chunk.intention || '')}" data-field="intention">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-700 uppercase">Actual</label>
                            <input type="text" class="w-full border p-1.5 rounded text-sm" value="${escapeHTML(chunk.actual || '')}" data-field="actual">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-700 uppercase">Brain Fog (0-100)</label>
                            <input type="number" class="w-full border p-1.5 rounded text-sm" value="${chunk.brainFog || 0}" data-field="brainFog">
                        </div>
                        <div class="flex gap-4 text-sm">
                            <label class="flex items-center gap-1"><input type="checkbox" data-field="isValuableDetour" ${chunk.isValuableDetour ? 'checked' : ''}> Valuable Detour</label>
                            <label class="flex items-center gap-1"><input type="checkbox" data-field="isDetrimentalDetour" ${chunk.isDetrimentalDetour ? 'checked' : ''}> Detrimental Detour</label>
                        </div>
                        <div class="flex justify-end gap-2">
                            <button class="cancel-edit-btn bg-gray-200 hover:bg-gray-300 text-gray-800 px-3 py-1.5 rounded text-sm font-bold">Cancel</button>
                            <button class="save-edit-btn bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm font-bold">Save Changes</button>
                        </div>
                    </div>
                `;
                card.appendChild(editForm);
                
                // Edit Listeners
                card.querySelector('.edit-chunk-btn').addEventListener('click', () => {
                    editForm.classList.remove('hidden');
                });
                card.querySelector('.cancel-edit-btn').addEventListener('click', () => {
                    editForm.classList.add('hidden');
                });
                card.querySelector('.save-edit-btn').addEventListener('click', async () => {
                    const btn = card.querySelector('.save-edit-btn');
                    btn.textContent = "Saving...";
                    btn.disabled = true;
                    
                    const payload = {
                        day: dateStr,
                        timeChunk: chunkId,
                        intention: editForm.querySelector('[data-field="intention"]').value,
                        actual: editForm.querySelector('[data-field="actual"]').value,
                        brainFog: parseInt(editForm.querySelector('[data-field="brainFog"]').value) || 0,
                        isValuableDetour: editForm.querySelector('[data-field="isValuableDetour"]').checked,
                        isDetrimentalDetour: editForm.querySelector('[data-field="isDetrimentalDetour"]').checked,
                        // Preserve correlation id if it was there
                        correlation_id: chunk.correlation_id || null
                    };
                    
                    try {
                        const response = await Auth.fetchWithAuth('/api/save_log', {
                            method: 'POST',
                            body: JSON.stringify(payload)
                        });
                        if (response.ok) {
                            // Reload grid
                            yearlyDataCache = {};
                            loadMonthData(activeYear, activeMonth);
                            closeDayModal();
                        } else {
                            alert("Failed to save changes.");
                        }
                    } catch (err) {
                        console.error(err);
                        alert("Error saving chunk.");
                    } finally {
                        btn.textContent = "Save Changes";
                        btn.disabled = false;
                    }
                });

                modalBody.appendChild(card);
            }
        });

        if (!foundAny && (!reflectionContainer.classList.contains('hidden') || !freeformContainer.classList.contains('hidden'))) {
            // we have reflection or journal but no chunks, it's fine.
        } else if (!foundAny) {
            modalBody.innerHTML += '<p class="text-gray-500 italic mt-4">No chunks logged for this day.</p>';
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
