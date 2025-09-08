document.addEventListener('DOMContentLoaded', () => {
    const intentionForm = document.getElementById('intention-form');
    const actualForm = document.getElementById('actual-form');
    const intentionsList = document.getElementById('intentions-list');
    const actualsList = document.getElementById('actuals-list');
    const loader = document.getElementById('loader');
    const aiOutputContainer = document.getElementById('ai-output-container');

    const getFromStorage = (key) => JSON.parse(localStorage.getItem(key)) || [];
    const saveToStorage = (key, data) => localStorage.setItem(key, JSON.stringify(data));

    let intentions = getFromStorage('intentions');
    let actuals = getFromStorage('actuals');

    const renderIntentions = () => {
        intentionsList.innerHTML = '';
        if (intentions.length === 0) {
            intentionsList.innerHTML = '<p class="text-gray-500">No intentions logged yet.</p>';
            return;
        }
        intentions.forEach(intention => {
            const intentionEl = document.createElement('div');
            intentionEl.className = 'bg-gray-200 p-4 rounded-lg mb-2';
            intentionEl.innerHTML = `
                <p class="font-bold">${intention.title}</p>
                <p class="text-sm text-gray-600">${intention.category} | ${intention.startTime} - ${intention.endTime}</p>
            `;
            intentionsList.appendChild(intentionEl);
        });
    };

    const renderActuals = () => {
        actualsList.innerHTML = '';
        if (actuals.length === 0) {
            actualsList.innerHTML = '<p class="text-gray-500">No actuals logged yet.</p>';
            return;
        }
        actuals.forEach(actual => {
            const feelingColor = {
                happy: 'bg-green-200',
                neutral: 'bg-yellow-200',
                sad: 'bg-red-200'
            };
            const actualEl = document.createElement('div');
            actualEl.className = `${feelingColor[actual.feeling] || 'bg-gray-200'} p-4 rounded-lg mb-2`;
            actualEl.innerHTML = `
                <p class="font-bold">${actual.title} ${actual.feeling === 'happy' ? '😊' : actual.feeling === 'neutral' ? '😐' : '😔'}</p>
                <p class="text-sm text-gray-600">${actual.timeSpent} minutes</p>
                ${actual.valuableDetour ? `<p class="text-sm text-blue-600 mt-2">Valuable Detour: ${actual.inventoryNote}</p>` : ''}
            `;
            actualsList.appendChild(actualEl);
        });
    };

    intentionForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData(intentionForm);
        const newIntention = {
            title: formData.get('intention-title'),
            category: formData.get('intention-category'),
            startTime: formData.get('start-time'),
            endTime: formData.get('end-time'),
        };
        intentions.push(newIntention);
        saveToStorage('intentions', intentions);
        renderIntentions();
        intentionForm.reset();
    });

    actualForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(actualForm);

        const newActual = {
            title: formData.get('actual-title'),
            timeSpent: formData.get('time-spent'),
            feeling: formData.get('feeling'),
            valuableDetour: formData.get('valuable-detour') === 'on',
            inventoryNote: formData.get('inventory-note'),
        };

        // Save and render the new "actual" locally first
        actuals.push(newActual);
        saveToStorage('actuals', actuals);
        renderActuals();

        // --- New Logic for AI Processing ---

        // 1. Show loader and clear previous output
        loader.classList.remove('hidden');
        aiOutputContainer.innerHTML = '';

        // 2. Create the journal entry string
        let journalEntry = `Activity: ${newActual.title}, Time Spent: ${newActual.timeSpent} minutes. Feeling: ${newActual.feeling}.`;
        if (newActual.valuableDetour && newActual.inventoryNote) {
            journalEntry += ` Note: ${newActual.inventoryNote}`;
        }

        try {
            // 3. Make the fetch request
            const response = await fetch('http://localhost:5000/process_journal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ journal_entry: journalEntry }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // 4. Display the result
            aiOutputContainer.innerHTML = `<p>${data.result.replace(/\n/g, '<br>')}</p>`;

        } catch (error) {
            console.error('Error processing journal entry:', error);
            aiOutputContainer.innerHTML = `<p class="text-red-500">Error processing your entry. Please try again later.</p>`;
        } finally {
            // 5. Hide loader
            loader.classList.add('hidden');
        }

        // Reset form and UI elements
        actualForm.reset();
        document.getElementById('inventory-note-container').classList.add('hidden');
    });

    // Initial render
    renderIntentions();
    renderActuals();
});
