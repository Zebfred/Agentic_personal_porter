// auth.js is loaded globally via a separate script tag in the HTML

document.addEventListener("DOMContentLoaded", () => {
    // XSS prevention: escape all dynamic values before innerHTML insertion
    const escapeHTML = (str) => {
        if (!str) return '';
        return String(str).replace(/[&<>'"]/g,
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag])
        );
    };

    const container = document.getElementById('network-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const detailsPanel = document.getElementById('node-details');
    const refreshBtn = document.getElementById('refresh-graph-btn');
    const filterCheckboxes = document.querySelectorAll('#graph-filters input[type="checkbox"]');
    
    let network = null;
    let fullNodes = new vis.DataSet();
    let fullEdges = new vis.DataSet();
    
    // Group styling configurations
    const groupStyles = {
        'Intention': { color: { background: '#93C5FD', border: '#2563EB' }, shape: 'box' },
        'Actual': { color: { background: '#86EFAC', border: '#16A34A' }, shape: 'box' },
        'TimeChunk': { color: { background: '#FDE047', border: '#CA8A04' }, shape: 'ellipse' },
        'Day': { color: { background: '#F3E8FF', border: '#9333EA' }, shape: 'circle' },
        'Hero': { color: { background: '#FCA5A5', border: '#DC2626' }, shape: 'star', size: 30 },
        'Goal': { color: { background: '#FDA4AF', border: '#E11D48' }, shape: 'diamond' },
    };

    const options = {
        nodes: {
            borderWidth: 2,
            font: { color: '#1F2937', size: 14, face: 'Inter, sans-serif' },
            shadow: true,
            margin: 10
        },
        edges: {
            width: 2,
            color: { color: '#9CA3AF', highlight: '#3B82F6' },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
            smooth: { type: 'continuous' }
        },
        physics: {
            forceAtlas2Based: {
                gravitationalConstant: -50,
                centralGravity: 0.01,
                springLength: 100,
                springConstant: 0.08
            },
            maxVelocity: 50,
            solver: 'forceAtlas2Based',
            timestep: 0.35,
            stabilization: { iterations: 150 }
        },
        interaction: { hover: true, tooltipDelay: 200 }
    };

    /**
     * Initializes or updates the vis-network
     */
    function renderNetwork() {
        if (network) {
            network.destroy();
        }
        
        // Filter nodes based on checkboxes
        const allowedGroups = Array.from(filterCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
            
        // Always include Hero/Goal if they exist even if no filter matches exactly (or add implicit filters)
        allowedGroups.push('Hero', 'Goal', 'Achievement', 'State', 'Context');
        
        const filteredNodesArray = fullNodes.get().filter(n => allowedGroups.includes(n.group) || allowedGroups.includes(n.label));
        const filteredNodeIds = new Set(filteredNodesArray.map(n => n.id));
        
        const filteredEdgesArray = fullEdges.get().filter(e => filteredNodeIds.has(e.from) && filteredNodeIds.has(e.to));

        const data = {
            nodes: new vis.DataSet(filteredNodesArray),
            edges: new vis.DataSet(filteredEdgesArray)
        };

        network = new vis.Network(container, data, options);
        
        // Add click listener
        network.on("click", function (params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const nodeData = fullNodes.get(nodeId);
                displayNodeDetails(nodeData);
            } else if (params.edges.length > 0) {
                // Could display edge details if wanted
                const edgeId = params.edges[0];
                const edgeData = fullEdges.get(edgeId);
                detailsPanel.innerHTML = `<p class="font-bold">Relationship: ${escapeHTML(edgeData.label || 'N/A')}</p>`;
            } else {
                detailsPanel.innerHTML = `<p class="text-gray-500 italic">Click on any node in the graph to view its details.</p>`;
            }
        });
    }

    function displayNodeDetails(node) {
        let html = `<h4 class="font-bold text-lg text-blue-800 mb-2">${escapeHTML(node.title || 'Unknown Node')}</h4>`;
        html += `<div class="bg-gray-100 px-2 py-1 rounded inline-block text-xs font-semibold mb-3">${escapeHTML(node.group || node.label)}</div>`;
        html += `<dl class="space-y-2">`;
        
        // Render properties gracefully
        if (node.title !== node.title) {
           html += `<div><dt class="text-xs text-gray-500 font-bold uppercase">Name/Desc</dt><dd class="text-sm">${escapeHTML(node.title)}</dd></div>`; 
        }
        html += `</dl>`;
        
        detailsPanel.innerHTML = html;
    }

    async function loadGraphData() {
        loadingIndicator.classList.remove('hidden');
        
        try {
            const token = window.Auth ? window.Auth.getToken() : null;
            if (!token) {
                throw new Error("No authentication token found. Please log in.");
            }
            const headers = { 'Authorization': `Bearer ${token}` };

            const res = await fetch('/api/graph_data?limit=500', { headers: headers });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.error || `HTTP error ${res.status}`);
            }

            const data = await res.json();
            
            // Map styling
            data.nodes.forEach(n => {
                const style = groupStyles[n.group] || { color: { background: '#E5E7EB', border: '#9CA3AF' }, shape: 'ellipse' };
                n.color = style.color;
                n.shape = style.shape;
                if (style.size) n.size = style.size;
            });
            
            fullNodes.clear();
            fullEdges.clear();
            fullNodes.add(data.nodes);
            fullEdges.add(data.edges);

            renderNetwork();
        } catch (error) {
            console.error(error);
            detailsPanel.innerHTML = `<p class="text-red-600 font-bold">Error loading graph: ${escapeHTML(error.message)}</p>`;
        } finally {
            loadingIndicator.classList.add('hidden');
        }
    }

    // Bind events
    refreshBtn.addEventListener('click', loadGraphData);
    filterCheckboxes.forEach(cb => {
        cb.addEventListener('change', renderNetwork);
    });

    // Initial Load
    loadGraphData();
});
