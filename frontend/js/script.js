document.addEventListener('DOMContentLoaded', () => {
    const inventoryList = document.getElementById('valuable-detours-list');
    const getFromStorage = (key) => JSON.parse(localStorage.getItem(key)) || [];

    const actuals = getFromStorage('actuals');
    const valuableDetours = actuals.filter(actual => actual.valuableDetour);

    const renderInventory = () => {
        inventoryList.innerHTML = '';
        if (valuableDetours.length === 0) {
            inventoryList.innerHTML = '<p class="text-gray-500">No valuable detours logged yet.</p>';
            return;
        }
        valuableDetours.forEach(detour => {
            const detourEl = document.createElement('div');
            detourEl.className = 'bg-white p-4 rounded-lg shadow-md';
            detourEl.innerHTML = `
                <p class="font-bold">${detour.inventoryNote}</p>
                <p class="text-sm text-gray-600">From "${detour.title}"</p>
            `;
            inventoryList.appendChild(detourEl);
        });
    };

    renderInventory();
});
