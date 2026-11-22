/**
 * North Star Accountability & 20-Second Recon Widget (`004-north-star-accountability`).
 * Uses Porter semantic CSS design tokens and WCAG AA ARIA live feedback (`Palette` / `Jovol`).
 */

const escapeHtml = (value) => {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>'"]/g, (tag) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;',
    }[tag]));
};

const getFetchFn = () => (
    window.Auth && typeof window.Auth.fetchWithAuth === 'function'
        ? window.Auth.fetchWithAuth
        : fetch
);

const todayIsoDate = () => new Date().toISOString().slice(0, 10);

const STATUS_STYLE = {
    active: { bg: 'var(--status-success)', label: 'Active Streak' },
    paused_grace: { bg: 'var(--secondary-action)', label: 'Grace Paused' },
    at_risk: { bg: 'var(--status-warning)', label: 'In Progress' },
    broken: { bg: 'var(--text-muted)', label: 'Fresh Start' },
};

function renderPillarCard(pillar) {
    const pct = Math.min(100, Math.round((pillar.completion_ratio || 0) * 100));
    const badge = STATUS_STYLE[pillar.streak_status] || STATUS_STYLE.at_risk;
    const accent = pillar.is_restorative_life_pillar ? 'var(--status-success)' : 'var(--primary-action)';
    const kindTag = pillar.is_restorative_life_pillar ? 'Restorative Life Win' : pillar.category;

    return `
        <article class="rounded-xl p-4 shadow-sm transition"
            style="background: var(--surface-bg); border: 1px solid var(--border-subtle); border-left: 4px solid ${accent};">
            <div class="flex flex-wrap justify-between items-start gap-2 mb-2">
                <div>
                    <h4 class="font-bold text-sm" style="color: var(--text-main);">${escapeHtml(pillar.title)}</h4>
                    <span class="text-xs" style="color: var(--text-muted);">${escapeHtml(kindTag)}</span>
                </div>
                <span class="text-[11px] font-bold px-2.5 py-0.5 rounded-full"
                    style="background: ${badge.bg}; color: var(--text-on-primary);">
                    ${escapeHtml(badge.label)}
                </span>
            </div>
            <div class="w-full h-2 rounded-full overflow-hidden mb-2" style="background: var(--border-subtle);"
                role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"
                aria-label="${escapeHtml(pillar.title)} weekly progress">
                <div class="h-full rounded-full transition-all" style="width: ${pct}%; background: ${accent};"></div>
            </div>
            <div class="flex flex-wrap justify-between items-center gap-2 text-xs">
                <span style="color: var(--text-muted);">
                    <strong>${escapeHtml(pillar.completed_this_week)}/${escapeHtml(pillar.weekly_target_count)}</strong> this week
                    &middot; 🔥 ${escapeHtml(pillar.current_streak_weeks)}w (best ${escapeHtml(pillar.longest_streak_weeks)}w)
                </span>
                <button type="button" data-recon-pillar="${escapeHtml(pillar.pillar_id)}"
                    aria-label="Log 20-second win for ${escapeHtml(pillar.title)}"
                    class="px-3 py-1.5 rounded-lg text-xs font-bold shadow-sm transition cursor-pointer"
                    style="background: ${accent}; color: var(--text-on-primary);">
                    +1 Win
                </button>
            </div>
        </article>
    `;
}

export function initNorthStarAccountability() {
    const section = document.getElementById('north-star-accountability-section');
    if (!section) return;

    const gridEl = document.getElementById('acct-pillars-grid');
    const feedbackEl = document.getElementById('acct-feedback');
    const weekBadge = document.getElementById('acct-iso-week-badge');
    const harmonyBadge = document.getElementById('acct-life-harmony-badge');
    const graceBtn = document.getElementById('btn-acct-grace-toggle');
    const exportBtn = document.getElementById('btn-acct-export-md');
    const drawerEl = document.getElementById('acct-markdown-drawer');
    const drawerPre = document.getElementById('acct-markdown-content');
    const minutesInput = document.getElementById('acct-duration-mins');
    const noteInput = document.getElementById('acct-win-note');

    let currentIsoWeek = '';
    let graceActive = false;
    let starterTemplates = [];

    const setFeedback = (msg) => {
        if (feedbackEl) feedbackEl.textContent = msg;
    };

    const loadDashboard = async () => {
        const fetchFn = getFetchFn();
        try {
            const [pillarsRes, streaksRes] = await Promise.all([
                fetchFn('/api/accountability/pillars'),
                fetchFn('/api/accountability/streaks'),
            ]);
            if (!pillarsRes.ok || !streaksRes.ok) {
                setFeedback('Accountability API unavailable (sign in to load streaks).');
                return;
            }
            const pillarsData = await pillarsRes.json();
            const dash = await streaksRes.json();
            starterTemplates = pillarsData.starter_templates || [];
            currentIsoWeek = dash.iso_week || '';
            graceActive = Boolean(dash.grace_mode_active);

            if (weekBadge) weekBadge.textContent = `Week: ${currentIsoWeek}`;
            if (harmonyBadge) {
                const pct = Math.round((dash.life_harmony_ratio || 0) * 100);
                harmonyBadge.textContent = `Life Harmony: ${pct}%`;
            }
            if (graceBtn) {
                graceBtn.setAttribute('aria-pressed', String(graceActive));
                graceBtn.textContent = graceActive ? '🌴 Grace Mode: ON' : '🌴 Grace Mode: OFF';
            }

            if (!gridEl) return;
            if (!dash.pillars || dash.pillars.length === 0) {
                gridEl.innerHTML = `
                    <div class="rounded-xl p-4 text-center" style="background: var(--surface-bg); border: 1px dashed var(--border-subtle);">
                        <p class="text-sm font-semibold mb-2" style="color: var(--text-main);">No North Star Pillars configured yet.</p>
                        <p class="text-xs mb-3" style="color: var(--text-muted);">Activate the 4 starter pillars (Career, Business/FinOps, Joy Fuel, Protected Life Time) in one click.</p>
                        <button type="button" id="btn-acct-seed-starters"
                            aria-label="Activate 4 Starter North Star Pillars"
                            class="px-4 py-2 rounded-lg text-xs font-bold shadow transition cursor-pointer"
                            style="background: var(--primary-action); color: var(--text-on-primary);">
                            ⚡ Activate 4 Starter Pillars
                        </button>
                    </div>
                `;
                const seedBtn = document.getElementById('btn-acct-seed-starters');
                if (seedBtn) seedBtn.addEventListener('click', () => seedStarterPillars(seedBtn));
                return;
            }

            gridEl.innerHTML = dash.pillars.map(renderPillarCard).join('');
            gridEl.querySelectorAll('[data-recon-pillar]').forEach((btn) => {
                btn.addEventListener('click', () => logQuickWin(btn.getAttribute('data-recon-pillar'), btn));
            });
        } catch (_err) {
            setFeedback('Could not load North Star Accountability right now.');
        }
    };

    const seedStarterPillars = async (btn) => {
        if (!starterTemplates.length) return;
        const orig = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Activating...';
        try {
            const res = await getFetchFn()('/api/accountability/pillars', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pillars: starterTemplates }),
            });
            setFeedback(res.ok ? '✅ Starter pillars activated!' : '❌ Failed to activate pillars.');
            await loadDashboard();
        } finally {
            btn.disabled = false;
            btn.textContent = orig;
        }
    };

    const logQuickWin = async (pillarId, btn) => {
        const orig = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Saving...';
        const mins = Math.max(1, Math.min(1440, parseInt((minutesInput && minutesInput.value) || '25', 10) || 25));
        const note = ((noteInput && noteInput.value) || '').trim();
        const key = `${todayIsoDate()}-${pillarId}-${Date.now()}`;
        try {
            const res = await getFetchFn()('/api/accountability/recon-checkin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pillar_id: pillarId,
                    iso_date: todayIsoDate(),
                    minutes_spent: mins,
                    win_note: note,
                    idempotency_key: key,
                    source: 'hub_recon',
                }),
            });
            if (res.ok) {
                if (noteInput) noteInput.value = '';
                setFeedback(`✅ Logged ${mins}m win for ${pillarId}!`);
                await loadDashboard();
            } else {
                const err = await res.json().catch(() => ({}));
                setFeedback(`❌ ${err.error || 'Could not log win.'}`);
            }
        } finally {
            btn.disabled = false;
            btn.textContent = orig;
        }
    };

    if (graceBtn) {
        graceBtn.addEventListener('click', async () => {
            if (!currentIsoWeek) return;
            const orig = graceBtn.textContent;
            graceBtn.disabled = true;
            graceBtn.textContent = 'Updating...';
            try {
                const nextState = !graceActive;
                const res = await getFetchFn()('/api/accountability/grace-window', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        iso_week: currentIsoWeek,
                        enabled: nextState,
                        reason: nextState ? 'Planned vacation or restorative time' : 'Resumed standard week',
                    }),
                });
                if (res.ok) {
                    setFeedback(nextState ? '🌴 Grace Mode ON — career streaks paused safely.' : '▶️ Grace Mode OFF.');
                    await loadDashboard();
                }
            } finally {
                graceBtn.disabled = false;
                if (graceBtn.textContent === 'Updating...') graceBtn.textContent = orig;
            }
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            const orig = exportBtn.textContent;
            exportBtn.disabled = true;
            exportBtn.textContent = 'Exporting...';
            try {
                const query = currentIsoWeek ? `?iso_week=${encodeURIComponent(currentIsoWeek)}` : '';
                const res = await getFetchFn()(`/api/accountability/export-markdown${query}`);
                if (res.ok) {
                    const md = await res.text();
                    if (drawerEl && drawerPre) {
                        drawerPre.textContent = md;
                        drawerEl.classList.remove('hidden');
                    }
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(md).catch(() => {});
                    }
                    setFeedback('📋 Markdown snapshot ready (copied to clipboard).');
                }
            } finally {
                exportBtn.disabled = false;
                exportBtn.textContent = orig;
            }
        });
    }

    loadDashboard();
}
