document.addEventListener('DOMContentLoaded', async () => {
    const inventoryList = document.getElementById('valuable-detours-list');

    const renderInventory = (valuableDetours) => {
        inventoryList.innerHTML = '';
        if (!valuableDetours || valuableDetours.length === 0) {
            inventoryList.innerHTML = '<p class="text-gray-500">No valuable detours logged yet.</p>';
            return;
        }
        valuableDetours.forEach(detour => {
            const detourEl = document.createElement('div');
            detourEl.className = 'bg-white p-4 rounded-lg shadow-md';
            detourEl.innerHTML = `
                <p class="font-bold">${detour.inventoryNote}</p>
                <p class="text-sm text-gray-600">From "${detour.title}"</p>
                <p class="text-xs text-gray-400 mt-2">${new Date(detour.timestamp).toLocaleString()}</p>
            `;
            inventoryList.appendChild(detourEl);
        });
    };

    inventoryList.innerHTML = '<p class="text-gray-500">Loading your Origin Story from the Graph...</p>';

    try {
        const response = await fetch('http://localhost:5090/api/inventory');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        renderInventory(data.valuable_detours);
    } catch (error) {
        console.error("Failed to load inventory from the database:", error);
        inventoryList.innerHTML = '<p class="text-red-500">Failed to connect to the Identity Graph.</p>';
    }
});
