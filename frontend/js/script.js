document.addEventListener('DOMContentLoaded', async () => {
    const getApiKey = () => {
        let key = localStorage.getItem('porterApiKey');
        if (!key) {
            key = prompt("Please enter the API Key to access Porter backend:");
            if (key) localStorage.setItem('porterApiKey', key);
        }
        return key || '';
    };

    const ui = {
        inventory: document.getElementById('valuable-detours-list'),
        quests: document.getElementById('quests-list'),
        skills: document.getElementById('skills-list'),
        equipment: document.getElementById('equipment-list'),
        stats: document.getElementById('stats-list'),
        finances: document.getElementById('finances-list')
    };

    const emptyState = (msg, colorClass) => `<p class="text-${colorClass}-500 font-medium italic text-center py-6 bg-${colorClass}-50 rounded-lg border border-${colorClass}-100 w-full">${msg}</p>`;

    const renderInventory = (data) => {
        // Render Detours
        ui.inventory.innerHTML = '';
        if (!data.valuable_detours || data.valuable_detours.length === 0) {
            ui.inventory.innerHTML = emptyState("No valuable detours logged yet.", "indigo");
        } else {
            data.valuable_detours.forEach(detour => {
                const el = document.createElement('div');
                el.className = 'bg-white/80 backdrop-blur-sm p-4 rounded-xl border border-indigo-50 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group';
                el.innerHTML = `
                    <div class="absolute w-1 h-full bg-indigo-500 left-0 top-0 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <p class="font-bold text-gray-800 text-lg leading-tight mb-1">${detour.inventoryNote}</p>
                    <p class="text-sm font-medium text-indigo-600 mb-2">${detour.title}</p>
                    <div class="flex items-center text-xs text-gray-400 gap-1 mt-2">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        ${new Date(detour.timestamp).toLocaleString()}
                    </div>
                `;
                ui.inventory.appendChild(el);
            });
        }

        // Render Quests
        ui.quests.innerHTML = '';
        if (!data.quests || data.quests.length === 0) {
            ui.quests.innerHTML = emptyState("No active quests currently tracked. Await further signals from the backend mapping.", "rose");
        }

        // Render Skills
        ui.skills.innerHTML = '';
        if (!data.skills || data.skills.length === 0) {
            ui.skills.innerHTML = emptyState("Skill logs empty. Neo4j achievement integration pending.", "emerald");
        }

        // Render Equipment
        ui.equipment.innerHTML = '';
        if (!data.equipment || data.equipment.length === 0) {
            ui.equipment.innerHTML = emptyState("Satchel is empty. Future repository items will appear here.", "amber");
        }

        // Render Stats
        if (data.stats) {
            ui.stats.innerHTML = Object.entries(data.stats).map(([k, v]) => `
                <div class="flex justify-between items-center bg-white/10 rounded-lg px-4 py-2 border border-white/20">
                    <span class="font-semibold capitalize text-indigo-100">${k}</span>
                    <span class="font-black text-xl text-white">${v}</span>
                </div>
            `).join('');
        }

        // Render Finances
        if (data.finances) {
            ui.finances.innerHTML = Object.entries(data.finances).map(([k, v]) => `
                <div class="bg-white/10 rounded-xl p-4 text-center border border-white/20 shadow-inner">
                    <p class="text-xs uppercase tracking-wider font-semibold text-amber-200 mb-1">${k.replace('_', ' ')}</p>
                    <p class="text-2xl font-black text-white">${v}</p>
                </div>
            `).join('');
        }
    };

    try {
        const response = await fetch('http://localhost:5090/api/inventory', {
            headers: { 'Authorization': `Bearer ${getApiKey()}` }
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        renderInventory(data);
    } catch (error) {
        console.error("Failed to load inventory from the database:", error);
        Object.values(ui).forEach(el => {
            if (el) el.innerHTML = `<p class="text-red-500 font-bold bg-red-100 p-3 rounded-lg text-center shadow-inner text-sm">Offline: Failed to connect to identity graph.</p>`;
        });
    }
});
