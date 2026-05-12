<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { createEventDispatcher, onMount } from 'svelte';
    import { sourceLang, targetLang } from '$lib/stores/config';
    import { API_BASE } from '$lib/api';
    import { showToast } from '$lib/stores/toast';
    import IconEdit from '$lib/components/icons/IconEdit.svelte';
    import IconCheck from '$lib/components/icons/IconCheck.svelte';
    import IconCheckCircle from '$lib/components/icons/IconCheckCircle.svelte';
    import IconX from '$lib/components/icons/IconX.svelte';
    import IconSave from '$lib/components/icons/IconSave.svelte';
    import IconChart from '$lib/components/icons/IconChart.svelte';
    import IconFilter from '$lib/components/icons/IconFilter.svelte';
    import IconSpinner from '$lib/components/icons/IconSpinner.svelte';

    export let jobId: string | null = null;
    
    const dispatch = createEventDispatcher();
    
    let segments: any[] = [];
    let filteredSegments: any[] = [];
    let isSaving = false;
    let isReconstructing = false;
    let filterValue = '';
    let saveTimers: Record<number, any> = {};

    // Stats
    let statsHigh = 0;
    let statsMedium = 0;
    let statsLow = 0;
    let statsEdited = 0;
    let statsReview = 0;

    $: if (jobId) {
        loadSegments();
    }

    function computeStats() {
        statsHigh = segments.filter(s => (s.confidence_score ?? s.confidence ?? 0) >= 0.85).length;
        statsMedium = segments.filter(s => {
            const c = s.confidence_score ?? s.confidence ?? 0;
            return c >= 0.60 && c < 0.85;
        }).length;
        statsLow = segments.filter(s => (s.confidence_score ?? s.confidence ?? 0) < 0.60).length;
        statsEdited = segments.filter(s => s.status === 'edited').length;
        statsReview = segments.filter(s => s.status === 'pending' || !s.status).length;
    }

    function applyFilter() {
        if (!filterValue) {
            filteredSegments = segments;
        } else {
            const vals = filterValue.split(',');
            filteredSegments = segments.filter(s => vals.includes(s.status || 'pending'));
        }
    }

    async function loadSegments(filter?: string) {
        if (!jobId) return;
        try {
            const url = filter 
                ? `${API_BASE}/api/jobs/${jobId}/segments?filter=${filter}`
                : `${API_BASE}/api/jobs/${jobId}/segments`;
            const token = localStorage.getItem('access_token');
            const resp = await fetch(url, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            const data = await resp.json();
            segments = data.segments || data || [];
            computeStats();
            applyFilter();
        } catch (e) {
            console.error('Failed to load segments:', e);
        }
    }

    function close() {
        dispatch('close');
    }

    // Auto-save with debounce
    function debounceSave(index: number, value: string) {
        if (saveTimers[index]) clearTimeout(saveTimers[index]);
        saveTimers[index] = setTimeout(() => saveSegment(index, value), 400);
    }

    async function saveSegment(index: number, value: string) {
        if (!jobId) return;
        try {
            const token = localStorage.getItem('access_token');
            await fetch(`${API_BASE}/api/jobs/${jobId}/segments/${index}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ edited: value }),
            });
            const seg = segments.find(s => s.index === index);
            if (seg) { seg.edited = value; seg.status = 'edited'; }
            computeStats();
        } catch (e) {
            console.error('Save failed:', e);
        }
    }

    async function approveAllHigh() {
        if (!jobId) return;
        try {
            const token = localStorage.getItem('access_token');
            const resp = await fetch(`${API_BASE}/api/jobs/${jobId}/segments/approve-all`, {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            const data = await resp.json();
            showToast(`Approved ${data.approved || 0} HIGH confidence segments`, 'success');
            await loadSegments();
        } catch (e: any) {
            showToast('Error: ' + e.message, 'error');
        }
    }

    async function reconstructFromEditor() {
        if (!jobId) return;
        isReconstructing = true;
        try {
            const token = localStorage.getItem('access_token');
            const resp = await fetch(`${API_BASE}/api/jobs/${jobId}/segments/reconstruct`, {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (resp.ok) {
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const cd = resp.headers.get('content-disposition');
                const fn = cd ? cd.split('filename=')[1]?.replace(/"/g, '') : 'reviewed.docx';
                a.href = url;
                a.download = fn;
                a.click();
                URL.revokeObjectURL(url);
            } else {
                const data = await resp.json().catch(() => ({}));
                showToast(data.error || 'Reconstruct failed', 'error');
            }
        } catch (e: any) {
            showToast('Error: ' + e.message, 'error');
        } finally {
            isReconstructing = false;
        }
    }

    function handleFilterChange(e: Event) {
        filterValue = (e.target as HTMLSelectElement).value;
        applyFilter();
    }

    function getConfClass(score: number): string {
        if (score >= 0.85) return 'high';
        if (score >= 0.60) return 'medium';
        return 'low';
    }

    function autoGrow(el: HTMLTextAreaElement) {
        el.style.height = 'auto';
        el.style.height = el.scrollHeight + 'px';
    }
</script>

{#if jobId}
<div class="editor-overlay">
    <div class="editor-container">
        <!-- Top Bar -->
        <div class="editor-topbar">
            <div class="editor-topbar-title">
                <IconEdit size={18} color="var(--accent)" />
                <h2>Review & Edit</h2>
                <span class="job-id-badge">{jobId}</span>
            </div>
            <div class="editor-topbar-actions">
                <button class="editor-btn" on:click={approveAllHigh}>
                    <IconCheckCircle size={14} />
                    Approve all HIGH
                </button>
                <button 
                    class="editor-btn primary" 
                    on:click={reconstructFromEditor}
                    disabled={isReconstructing}
                >
                    {#if isReconstructing}
                        <IconSpinner size={14} color="#fff" />
                        Building...
                    {:else}
                        <IconSave size={14} />
                        Save & Export
                    {/if}
                </button>
                <button class="editor-btn close-btn" on:click={close} title="Close Editor">
                    <IconX size={16} />
                </button>
            </div>
        </div>

        <!-- Layout: Sidebar + Main -->
        <div class="editor-layout">
            <!-- Sidebar Stats -->
            <aside class="editor-sidebar">
                <div class="editor-stats">
                    <div class="stats-header">
                        <IconChart size={16} color="var(--text-muted)" />
                        <h4>Statistics</h4>
                    </div>
                    <div class="stat-row">
                        <span><span class="stat-dot high"></span>HIGH</span>
                        <span class="stat-val">{statsHigh}</span>
                    </div>
                    <div class="stat-row">
                        <span><span class="stat-dot medium"></span>MEDIUM</span>
                        <span class="stat-val">{statsMedium}</span>
                    </div>
                    <div class="stat-row">
                        <span><span class="stat-dot low"></span>LOW</span>
                        <span class="stat-val">{statsLow}</span>
                    </div>
                    <div class="stats-divider"></div>
                    <div class="stat-review">{statsReview} segments need review</div>
                    {#if statsEdited > 0}
                        <div class="stat-edited">{statsEdited} edited</div>
                    {/if}

                    <div class="filter-group">
                        <div class="filter-label">
                            <IconFilter size={12} color="var(--text-muted)" />
                            Filter
                        </div>
                        <select class="filter-select" on:change={handleFilterChange}>
                            <option value="">All segments</option>
                            <option value="pending">Needs review</option>
                            <option value="pending,edited">Pending + Edited</option>
                            <option value="edited">Edited</option>
                            <option value="approved">Approved</option>
                        </select>
                    </div>
                </div>
            </aside>

            <!-- Main Table -->
            <main class="editor-main">
                <table class="seg-table">
                    <thead>
                        <tr>
                            <th class="col-idx">#</th>
                            <th class="col-source">{$sourceLang === 'auto' ? 'SOURCE' : $sourceLang.toUpperCase()}</th>
                            <th class="col-target">{$targetLang.toUpperCase()} (Target)</th>
                            <th class="col-conf">Conf</th>
                            <th class="col-status">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each filteredSegments as seg, i}
                            {@const conf = seg.confidence_score ?? seg.confidence ?? 0}
                            {@const confClass = getConfClass(conf)}
                            <tr class="seg-row {seg.status === 'edited' ? 'edited' : `conf-${confClass}`}">
                                <td class="seg-idx">{(seg.index ?? i) + 1}</td>
                                <td class="seg-source">{seg.source_text || seg.source || ''}</td>
                                <td>
                                    <textarea 
                                        class="seg-edit"
                                        rows="1"
                                        on:focus={(e) => autoGrow(e.currentTarget)}
                                        on:input={(e) => {
                                            autoGrow(e.currentTarget);
                                            debounceSave(seg.index ?? i, e.currentTarget.value);
                                        }}
                                    >{seg.edited || seg.target_text || seg.target || ''}</textarea>
                                </td>
                                <td>
                                    <span class="conf-badge {confClass}">
                                        {Math.round(conf * 100)}%
                                    </span>
                                </td>
                                <td class="seg-status-cell">
                                    <span class="seg-status-badge status-{seg.status || 'pending'}">
                                        {seg.status || 'pending'}
                                    </span>
                                </td>
                            </tr>
                        {:else}
                            <tr>
                                <td colspan="5" class="empty-state">
                                    No segments found
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </main>
        </div>

        <!-- Footer -->
        <div class="editor-footer">
            <button class="editor-btn" on:click={close}>
                <IconX size={14} />
                Close Editor
            </button>
            <button class="editor-btn primary" on:click={reconstructFromEditor} disabled={isReconstructing}>
                {#if isReconstructing}
                    <IconSpinner size={14} color="#fff" /> Building...
                {:else}
                    <IconSave size={14} /> Save & Export File
                {/if}
            </button>
        </div>
    </div>
</div>
{/if}

<style>
    .editor-overlay {
        position: fixed;
        inset: 0;
        z-index: 1000;
        background: var(--bg-primary);
        overflow-y: auto;
    }

    .editor-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 24px;
        display: flex;
        flex-direction: column;
        min-height: 100vh;
    }

    /* ── Topbar ── */
    .editor-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 0;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 12px;
    }

    .editor-topbar-title {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .editor-topbar-title h2 {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0;
    }

    .job-id-badge {
        font-size: 0.7rem;
        padding: 3px 10px;
        background: var(--bg-elevated);
        border: 1px solid var(--border-subtle);
        border-radius: 100px;
        color: var(--text-muted);
        font-family: var(--font-mono);
    }

    .editor-topbar-actions {
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .editor-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 18px;
        border-radius: var(--radius-sm);
        border: 1px solid var(--border);
        background: var(--bg-card);
        color: var(--text-primary);
        font-size: 0.8rem;
        font-family: inherit;
        font-weight: 500;
        cursor: pointer;
        transition: all var(--transition-base);
    }

    .editor-btn:hover { border-color: var(--accent); color: var(--accent); }

    .editor-btn.primary {
        background: var(--accent);
        border: none;
        color: #fff;
        font-weight: 600;
    }

    .editor-btn.primary:hover {
        background: var(--accent-hover);
        transform: translateY(-1px);
        box-shadow: var(--accent-glow);
    }

    .editor-btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .close-btn {
        width: 36px;
        height: 36px;
        padding: 0;
        justify-content: center;
        border-radius: 50%;
    }

    .close-btn:hover {
        background: var(--danger-muted);
        border-color: rgba(239, 68, 68, 0.3);
        color: var(--danger);
    }

    /* ── Layout ── */
    .editor-layout {
        display: grid;
        grid-template-columns: 220px 1fr;
        gap: 20px;
        flex: 1;
    }

    /* ── Sidebar ── */
    .editor-sidebar {
        position: sticky;
        top: 24px;
        align-self: start;
    }

    .editor-stats {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius);
        padding: 20px;
    }

    .stats-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
    }

    .stats-header h4 {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0;
    }

    .stat-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    .stat-val {
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        color: var(--text-primary);
    }

    .stat-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }

    .stat-dot.high { background: var(--success); }
    .stat-dot.medium { background: var(--warning); }
    .stat-dot.low { background: var(--danger); }

    .stats-divider {
        border-top: 1px solid var(--border-subtle);
        margin: 14px 0;
    }

    .stat-review { font-size: 0.78rem; color: var(--accent); font-weight: 500; }
    .stat-edited { font-size: 0.72rem; color: var(--text-muted); margin-top: 4px; }

    .filter-group {
        margin-top: 16px;
    }

    .filter-label {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--text-muted);
        font-weight: 600;
        margin-bottom: 6px;
    }

    .filter-select {
        width: 100%;
        padding: 8px 10px;
        border-radius: var(--radius-sm);
        border: 1px solid var(--border);
        background: var(--bg-secondary);
        color: var(--text-primary);
        font-size: 0.8rem;
        font-family: inherit;
    }

    .filter-select:focus {
        outline: none;
        border-color: var(--accent);
        box-shadow: 0 0 0 3px var(--accent-muted);
    }

    /* ── Main Table ── */
    .editor-main { flex: 1; overflow-x: auto; }

    .seg-table { width: 100%; border-collapse: separate; border-spacing: 0; }

    .col-idx { width: 40px; }
    .col-source { width: 38%; }
    .col-target { width: 38%; }
    .col-conf { width: 60px; }
    .col-status { width: 80px; }

    .seg-table th {
        position: sticky;
        top: 0;
        background: var(--bg-secondary);
        padding: 10px 12px;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--text-muted);
        text-align: left;
        border-bottom: 1px solid var(--border-subtle);
        z-index: 2;
        font-weight: 600;
    }

    .seg-table td {
        padding: 10px 12px;
        border-bottom: 1px solid var(--border-subtle);
        font-size: 0.82rem;
        vertical-align: top;
    }

    .seg-row { transition: background var(--transition-base); }
    .seg-row:hover { background: var(--bg-elevated) !important; }
    .seg-row.conf-high { background: rgba(34, 197, 94, 0.04); }
    .seg-row.conf-medium { background: rgba(234, 179, 8, 0.05); }
    .seg-row.conf-low { background: rgba(239, 68, 68, 0.05); }
    .seg-row.edited { background: rgba(20, 184, 166, 0.06); }

    .seg-idx { color: var(--text-muted); font-size: 0.72rem; font-variant-numeric: tabular-nums; }
    .seg-source {
        color: var(--text-secondary);
        font-family: 'Noto Sans JP', 'Geist', sans-serif;
        line-height: 1.6;
    }

    .seg-edit {
        width: 100%;
        background: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        color: var(--text-primary);
        font-family: inherit;
        font-size: 0.82rem;
        padding: 6px 8px;
        resize: vertical;
        min-height: 28px;
        transition: border-color var(--transition-base), background var(--transition-base);
        line-height: 1.6;
    }

    .seg-edit:hover {
        border-color: var(--border);
    }

    .seg-edit:focus {
        border-color: var(--accent);
        outline: none;
        background: var(--accent-muted);
    }

    .conf-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 100px;
        font-size: 0.68rem;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
    }

    .conf-badge.high { background: var(--success-muted); color: var(--success); }
    .conf-badge.medium { background: var(--warning-muted); color: var(--warning); }
    .conf-badge.low { background: var(--danger-muted); color: var(--danger); }

    .seg-status-badge {
        font-size: 0.68rem;
        padding: 2px 8px;
        border-radius: 100px;
        font-weight: 500;
        text-transform: capitalize;
    }

    .status-pending { background: var(--warning-muted); color: var(--warning); }
    .status-edited { background: var(--accent-muted); color: var(--accent); }
    .status-approved { background: var(--success-muted); color: var(--success); }

    .empty-state {
        text-align: center;
        color: var(--text-muted);
        padding: 60px 20px !important;
        font-style: italic;
    }

    .editor-footer {
        display: flex;
        justify-content: center;
        padding: 24px 0;
        gap: 12px;
        border-top: 1px solid var(--border-subtle);
        margin-top: 20px;
    }

    @media (max-width: 768px) {
        .editor-layout { grid-template-columns: 1fr; }
        .editor-sidebar { position: static; }
    }
</style>
