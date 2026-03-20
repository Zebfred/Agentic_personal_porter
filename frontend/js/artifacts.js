document.addEventListener('DOMContentLoaded', () => {
    const getApiKey = () => {
        let key = localStorage.getItem('porterApiKey');
        if (!key) {
            key = prompt("Please enter the API Key to access Porter backend:");
            if (key) localStorage.setItem('porterApiKey', key);
        }
        return key || '';
    };

    const tabOrigin = document.getElementById('tab-origin');
    const tabAmbition = document.getElementById('tab-ambition');
    const formContainer = document.getElementById('form-container');
    const saveBtn = document.getElementById('save-btn');
    const loadingEl = document.getElementById('loading');
    const errorMsg = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const successMsg = document.getElementById('success-message');
    const successText = document.getElementById('success-text');

    let currentArtifactName = 'hero_origin.json';
    let currentData = null;

    const showError = (msg) => {
        errorText.textContent = msg;
        errorMsg.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => errorMsg.classList.add('hidden'), 5000);
    };

    const showSuccess = (msg) => {
        successText.textContent = msg;
        successMsg.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => successMsg.classList.add('hidden'), 5000);
    };

    const loadArtifact = async (artifactName) => {
        formContainer.innerHTML = '';
        saveBtn.classList.add('hidden');
        loadingEl.classList.remove('hidden');
        currentArtifactName = artifactName;

        try {
            const response = await fetch(`http://localhost:5090/api/artifacts/${artifactName}`, {
                headers: { 'Authorization': `Bearer ${getApiKey()}` }
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            currentData = await response.json();
            buildForm(currentData, formContainer, currentData);
            saveBtn.classList.remove('hidden');
        } catch (error) {
            console.error("Failed to load artifact:", error);
            showError("Failed to fetch artifact from local API.");
        } finally {
            loadingEl.classList.add('hidden');
        }
    };

    const saveArtifact = async () => {
        if (!currentData) return;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<div class="inline-block animate-spin h-5 w-5 border-2 border-white rounded-full border-t-transparent mr-2"></div> Saving...';
        
        try {
            const response = await fetch(`http://localhost:5090/api/artifacts/${currentArtifactName}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getApiKey()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(currentData)
            });
            
            if (!response.ok) throw new Error("Failed to save.");
            showSuccess(`Artifact ${currentArtifactName.replace('.json', '')} securely logged to the backend.`);
        } catch (error) {
            console.error("Save error:", error);
            showError("Failed to save artifact changes.");
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg> COMMIT CHANGES';
        }
    };

    // Recursive UI Builder
    const buildForm = (obj, parentContent, rootRef) => {
        if (typeof obj === 'object' && obj !== null) {
            if (Array.isArray(obj)) {
                const listContainer = document.createElement('div');
                listContainer.className = 'flex flex-col space-y-4 w-full mt-2';
                obj.forEach((item, index) => {
                    const itemWrapper = document.createElement('div');
                    itemWrapper.className = 'p-5 border border-gray-100 rounded-xl bg-gray-50/80 shadow-sm relative group hover:border-indigo-100 transition-colors';
                    
                    const header = document.createElement('div');
                    header.className = 'font-bold text-indigo-700/70 mb-4 border-b border-indigo-100 pb-2 text-xs uppercase tracking-widest flex justify-between items-center';
                    header.textContent = `Entry ${index + 1}`;
                    itemWrapper.appendChild(header);

                    buildForm(item, itemWrapper, rootRef);
                    listContainer.appendChild(itemWrapper);
                });
                parentContent.appendChild(listContainer);
            } else {
                for (const key in obj) {
                    const val = obj[key];
                    const fieldWrapper = document.createElement('div');
                    fieldWrapper.className = 'mb-6 w-full';
                    
                    const label = document.createElement('label');
                    label.className = 'block text-sm font-bold text-gray-700 mb-2 capitalize tracking-wide';
                    label.textContent = key.replace(/_/g, ' ');
                    fieldWrapper.appendChild(label);

                    if (typeof val === 'string' || typeof val === 'number') {
                        let input;
                        if (typeof val === 'string' && val.length > 60) {
                            input = document.createElement('textarea');
                            input.rows = 4;
                            input.className = 'w-full p-4 border border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all resize-y shadow-inner text-gray-800 bg-white leading-relaxed';
                            input.value = val;
                            input.addEventListener('input', (e) => { obj[key] = e.target.value; });
                        } else {
                            input = document.createElement('input');
                            input.type = typeof val === 'number' ? 'number' : 'text';
                            input.className = 'w-full p-4 border border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-inner text-gray-800 bg-white font-medium';
                            input.value = val;
                            input.addEventListener('input', (e) => {
                                obj[key] = input.type === 'number' ? Number(e.target.value) : e.target.value;
                            });
                        }
                        fieldWrapper.appendChild(input);
                    } else if (typeof val === 'object' && val !== null) {
                        const nestedContent = document.createElement('div');
                        nestedContent.className = 'pl-6 border-l-4 border-indigo-100 ml-2 py-2 mt-2';
                        buildForm(val, nestedContent, rootRef);
                        fieldWrapper.appendChild(nestedContent);
                    }
                    parentContent.appendChild(fieldWrapper);
                }
            }
        }
    };

    const activateTab = (activeTab, inactiveTab) => {
        activeTab.className = "px-8 py-3 rounded-full font-bold text-lg bg-indigo-600 text-white shadow-lg shadow-indigo-500/30 transform hover:-translate-y-1 transition-all focus:outline-none focus:ring-4 focus:ring-indigo-300";
        inactiveTab.className = "px-8 py-3 rounded-full font-bold text-lg bg-white text-gray-700 border-2 border-transparent shadow-md hover:bg-gray-50 hover:shadow-lg hover:-translate-y-1 transform transition-all focus:outline-none focus:ring-4 focus:ring-gray-300";
    };

    tabOrigin.addEventListener('click', () => {
        activateTab(tabOrigin, tabAmbition);
        loadArtifact('hero_origin.json');
    });

    tabAmbition.addEventListener('click', () => {
        activateTab(tabAmbition, tabOrigin);
        loadArtifact('hero_ambition.json');
    });

    saveBtn.addEventListener('click', saveArtifact);

    // Initial load
    loadArtifact('hero_origin.json');
});
