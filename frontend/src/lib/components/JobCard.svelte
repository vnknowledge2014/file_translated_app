<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { showToast } from '$lib/stores/toast';
    import { downloadJob, downloadXliff, uploadXliff, retryJob, deleteJob } from '$lib/api';
    import { createEventDispatcher } from 'svelte';
    import IconCheck from '$lib/components/icons/IconCheck.svelte';
    import IconX from '$lib/components/icons/IconX.svelte';
    import IconSpinner from '$lib/components/icons/IconSpinner.svelte';
    import IconDownload from '$lib/components/icons/IconDownload.svelte';
    import IconEdit from '$lib/components/icons/IconEdit.svelte';
    import IconFileText from '$lib/components/icons/IconFileText.svelte';
    import IconUpload from '$lib/components/icons/IconUpload.svelte';
    import IconCheckCircle from '$lib/components/icons/IconCheckCircle.svelte';
    import IconAlertTriangle from '$lib/components/icons/IconAlertTriangle.svelte';
    import IconFile from '$lib/components/icons/IconFile.svelte';

    export let job: any;

    const dispatch = createEventDispatcher();

    // ── Phases pipeline ──
    const PHASES = ['queued', 'extracting', 'translating', 'reconstructing', 'completed'];

    $: getStatusText = () => {
        const s = job.status;
        if (s === 'queued') return m.job_queued();
        if (s === 'extracting') return m.job_extracting();
        if (s === 'translating') return m.job_translating();
        if (s === 'reconstructing') return m.job_reconstructing();
        if (s === 'completed') return m.job_completed();
        if (s === 'failed') return m.job_failed();
        return s;
    };

    $: progressPercent = (() => {
        const s = job.status;
        if (s === 'queued') return 5;
        if (s === 'extracting') return 25;
        if (s === 'translating') return 30 + Math.floor((job.progress || 0) * 55);
        if (s === 'reconstructing') return 90;
        if (s === 'completed') return 100;
        if (s === 'failed') return 100;
        return 0;
    })();

    $: currentPhaseIndex = PHASES.indexOf(job.status === 'failed' ? 'queued' : job.status);

    $: completionInfo = (() => {
        if (job.status !== 'completed') return '';
        const segs = job.segments_count || 0;
        const dur = job.duration_seconds ? job.duration_seconds.toFixed(1) : '0';
        return `${segs} segments, ${dur}s`;
    })();

    $: progressMessage = (() => {
        if (job.status === 'completed') return completionInfo;
        if (job.status === 'failed') return job.error_message || 'Error';
        return job.progress_message || `${job.status}...`;
    })();

    $: canRetry = ['failed', 'completed', 'extracting', 'translating', 'reconstructing'].includes(job.status);
    $: hasMainActions = job.status === 'completed';
    $: hasXliff = job.xliff_path || job.has_xliff;

    let fileInput: HTMLInputElement;

    // ── Retry state ──
    let retrying = false;

    async function handleRetry() {
        if (retrying) return; // Prevent double-click spam
        retrying = true;
        try {
            await retryJob(job.id);
            dispatch('retry', job.id);
        } catch (err: any) {
            showToast('Retry failed: ' + err.message, 'error');
        } finally {
            retrying = false;
        }
    }

    // ── Remove state (2-step confirmation) ──
    let removeStep: 0 | 1 | 2 = 0;
    let removing = false;

    function startRemove() { removeStep = 1; }
    function cancelRemove() { removeStep = 0; }
    function confirmStep2() { removeStep = 2; }

    async function handleRemoveConfirmed() {
        if (removing) return; // Prevent double-click spam
        removing = true;
        try {
            await deleteJob(job.id);
            dispatch('remove', job.id);
        } catch (err: any) {
            showToast('Delete failed: ' + err.message, 'error');
            removeStep = 0;
        } finally {
            removing = false;
        }
    }

    async function handleXliffUpload(e: Event) {
        const target = e.target as HTMLInputElement;
        if (!target.files?.length) return;
        try {
            await uploadXliff(job.id, target.files[0]);
            showToast('XLIFF uploaded successfully. Reconstruction queued.', 'success');
        } catch (err: any) {
            showToast('XLIFF upload failed: ' + err.message, 'error');
        } finally {
            target.value = '';
        }
    }
</script>

<div class="job-card" class:completed={job.status === 'completed'} class:failed={job.status === 'failed'}>
    <!-- Header: Filename + Status Badge -->
    <div class="job-header">
        <div class="job-header-left">
            <div class="job-icon" class:icon-done={job.status === 'completed'} class:icon-fail={job.status === 'failed'}>
                {#if job.status === 'completed'}
                    <IconCheckCircle size={22} color="var(--success)" />
                {:else if job.status === 'failed'}
                    <IconAlertTriangle size={22} color="var(--danger)" />
                {:else}
                    <IconFile size={22} color="var(--accent)" />
                {/if}
            </div>
            <div>
                <div class="job-filename">{job.filename}</div>
                <div class="job-meta">
                    {(job.source_lang || 'auto').toUpperCase()} → {(job.target_lang || 'en').toUpperCase()} | 
                    {job.created_at ? new Date(job.created_at).toLocaleTimeString() : ''}
                </div>
            </div>
        </div>
        <div class="status-badge status-{job.status}">
            {getStatusText()}
        </div>
    </div>

    <!-- Phase Steps Pipeline -->
    {#if job.status !== 'failed'}
        <div class="phase-steps">
            {#each PHASES as phase, i}
                <div
                    class="phase-step"
                    class:done={i < currentPhaseIndex}
                    class:active={i === currentPhaseIndex}
                ></div>
            {/each}
        </div>
        <div class="phase-labels">
            {#each PHASES as phase, i}
                <span
                    class:done={i < currentPhaseIndex}
                    class:active={i === currentPhaseIndex}
                >{phase}</span>
            {/each}
        </div>
    {/if}

    <!-- Progress Bar with % -->
    {#if job.status !== 'completed' && job.status !== 'failed'}
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" style="width: {progressPercent}%"></div>
            </div>
            <div class="progress-info">
                <span class="progress-message">{progressMessage}</span>
                <span class="progress-pct">{progressPercent}%</span>
            </div>
        </div>
    {/if}

    <!-- Completion Info -->
    {#if job.status === 'completed' && completionInfo}
        <div class="completion-info">
            <IconCheckCircle size={16} color="var(--success)" />
            {completionInfo}
        </div>
    {/if}

    <!-- Error Message -->
    {#if job.error_message && job.status === 'failed'}
        <div class="job-error">
            <IconAlertTriangle size={16} /> {job.error_message}
        </div>
    {/if}
    
    <!-- ═══ Primary Action Buttons ═══ -->
    {#if hasMainActions || hasXliff}
        <div class="job-actions-primary">
            {#if hasMainActions}
                <button class="btn btn-download" on:click={() => downloadJob(job.id)}>
                    <IconDownload size={16} /> {m.job_download()}
                </button>
                <button class="btn btn-review" on:click={() => dispatch('review', job.id)}>
                    <IconEdit size={16} /> {m.job_review()}
                </button>
            {/if}
            
            {#if hasXliff}
                <button class="btn btn-xliff" on:click={() => downloadXliff(job.id)}>
                    <IconFileText size={16} /> {m.job_download_xliff()}
                </button>
                <button class="btn btn-xliff" on:click={() => fileInput.click()}>
                    <IconUpload size={16} /> {m.job_upload_xliff()}
                </button>
                <input type="file" bind:this={fileInput} on:change={handleXliffUpload} accept=".xlf,.xliff" style="display:none;">
            {/if}
        </div>
    {/if}

    <!-- ═══ Secondary Actions (Retry / Remove) — always at bottom ═══ -->
    {#if removeStep === 0}
        <div class="job-actions-secondary">
            {#if canRetry}
                <button class="btn-secondary btn-sec-retry" on:click={handleRetry} disabled={retrying}>
                    {#if retrying}
                        <IconSpinner size={14} /> {m.job_retrying()}
                    {:else}
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="23 4 23 10 17 10"></polyline>
                            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                        </svg>
                        {m.job_retry()}
                    {/if}
                </button>
            {/if}
            <button class="btn-secondary btn-sec-remove" on:click={startRemove}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
                {m.job_remove()}
            </button>
        </div>
    {/if}

    <!-- ═══ Remove Confirmation (2-step) ═══ -->
    {#if removeStep >= 1}
        <div class="remove-confirm-panel" class:step-final={removeStep === 2}>
            {#if removeStep === 1}
                <div class="remove-warning">
                    <IconAlertTriangle size={16} />
                    <span>{m.job_remove_warn()}</span>
                </div>
                <div class="remove-actions">
                    <button class="btn-secondary" on:click={cancelRemove}>
                        {m.job_remove_cancel()}
                    </button>
                    <button class="btn-secondary btn-sec-continue" on:click={confirmStep2}>
                        {m.job_remove_continue()}
                    </button>
                </div>
            {:else}
                <div class="remove-actions">
                    <button class="btn-secondary" on:click={cancelRemove}>
                        {m.job_remove_cancel()}
                    </button>
                    <button class="btn btn-danger-confirm" on:click={handleRemoveConfirmed} disabled={removing}>
                        {#if removing}
                            <IconSpinner size={14} /> {m.job_removing()}
                        {:else}
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                            {m.job_remove_confirm()}
                        {/if}
                    </button>
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    /* ── Card Container ── */
    .job-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius);
        padding: 20px 24px;
        margin-bottom: 12px;
        transition: all var(--transition-slow);
        animation: slideIn 0.4s ease-out;
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .job-card.completed { border-color: rgba(34, 197, 94, 0.3); }
    .job-card.failed { border-color: rgba(239, 68, 68, 0.3); }

    /* ── Header ── */
    .job-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
    }

    .job-header-left {
        display: flex;
        gap: 12px;
        align-items: center;
        min-width: 0;
    }

    .job-icon {
        background: var(--bg-elevated);
        width: 40px; height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .job-icon.icon-done { background: var(--success-muted); }
    .job-icon.icon-fail { background: var(--danger-muted); }

    .job-filename {
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 2px;
        word-break: break-all;
    }

    .job-meta {
        font-size: 0.72rem;
        color: var(--text-muted);
        font-variant-numeric: tabular-nums;
    }

    /* ── Status Badge ── */
    .status-badge {
        padding: 4px 14px;
        border-radius: 100px;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        flex-shrink: 0;
        white-space: nowrap;
    }

    .status-queued { background: var(--warning-muted); color: var(--warning); }
    .status-extracting { background: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
    .status-translating { background: var(--accent-muted); color: var(--accent); }
    .status-reconstructing { background: var(--warning-muted); color: var(--warning); }
    .status-completed { background: var(--success-muted); color: var(--success); }
    .status-failed { background: var(--danger-muted); color: var(--danger); }

    /* ── Phase Steps Pipeline ── */
    .phase-steps {
        display: flex;
        gap: 4px;
        margin: 10px 0 4px;
    }

    .phase-step {
        flex: 1;
        height: 3px;
        border-radius: 100px;
        background: var(--bg-elevated);
        transition: all 0.4s ease;
    }

    .phase-step.active {
        background: var(--accent);
        box-shadow: 0 0 8px var(--accent-muted);
    }

    .phase-step.done { background: var(--success); }

    .phase-labels {
        display: flex;
        justify-content: space-between;
        font-size: 0.58rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    .phase-labels span.active { color: var(--accent); }
    .phase-labels span.done { color: var(--success); }

    /* ── Progress Bar ── */
    .progress-container { margin: 6px 0 12px; }

    .progress-bar {
        height: 5px;
        background: var(--bg-elevated);
        border-radius: 100px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--accent), var(--accent-hover));
        border-radius: 100px;
        transition: width 0.5s ease;
        position: relative;
    }

    .progress-fill::after {
        content: '';
        position: absolute;
        right: 0; top: 0;
        width: 30px; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3));
        animation: shimmer 1.5s infinite;
    }

    @keyframes shimmer {
        0% { opacity: 0; }
        50% { opacity: 1; }
        100% { opacity: 0; }
    }

    .progress-info {
        display: flex;
        justify-content: space-between;
        margin-top: 6px;
        font-size: 0.78rem;
        color: var(--text-muted);
    }

    .progress-pct {
        font-weight: 600;
        color: var(--accent);
        font-variant-numeric: tabular-nums;
    }

    /* ── Completion Info ── */
    .completion-info {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        margin-bottom: 12px;
        border-radius: var(--radius-sm);
        background: var(--success-muted);
        color: var(--success);
        font-size: 0.82rem;
        font-weight: 500;
    }

    /* ── Error ── */
    .job-error {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        padding: 10px 14px;
        background: var(--danger-muted);
        color: var(--danger);
        border-radius: var(--radius-sm);
        font-size: 0.82rem;
    }

    /* ════════════════════════════════════════
       Primary Action Buttons (Download/Review/XLIFF)
       ════════════════════════════════════════ */
    .job-actions-primary {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 0;
    }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: var(--radius-sm);
        font-size: 0.78rem;
        font-weight: 600;
        font-family: inherit;
        cursor: pointer;
        border: none;
        transition: all var(--transition-base);
        text-decoration: none;
    }

    .btn:active { transform: scale(0.98); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }

    .btn-download {
        background: var(--accent);
        color: #fff;
    }

    .btn-download:hover {
        background: var(--accent-hover);
        transform: translateY(-1px);
        box-shadow: var(--accent-glow);
    }

    .btn-review {
        background: var(--success);
        color: #fff;
    }

    .btn-review:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
    }

    .btn-xliff {
        background: var(--bg-elevated);
        color: var(--text-secondary);
        border: 1px solid var(--border);
    }

    .btn-xliff:hover {
        color: var(--text-primary);
        border-color: var(--accent);
    }

    /* ════════════════════════════════════════
       Secondary Actions (Retry / Remove) — subtle, right-aligned
       ════════════════════════════════════════ */
    .job-actions-secondary {
        display: flex;
        gap: 6px;
        justify-content: flex-end;
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid var(--border-subtle);
    }

    .btn-secondary {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 5px 12px;
        border-radius: var(--radius-sm);
        font-size: 0.72rem;
        font-weight: 500;
        font-family: inherit;
        cursor: pointer;
        border: 1px solid var(--border-subtle);
        background: transparent;
        color: var(--text-muted);
        transition: all var(--transition-base);
    }

    .btn-secondary:hover {
        color: var(--text-secondary);
        border-color: var(--border);
    }

    .btn-secondary:active { transform: scale(0.97); }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-sec-retry:hover {
        color: #fbbf24;
        border-color: rgba(251, 191, 36, 0.35);
        background: rgba(251, 191, 36, 0.06);
    }

    .btn-sec-remove:hover {
        color: var(--danger);
        border-color: rgba(239, 68, 68, 0.35);
        background: rgba(239, 68, 68, 0.06);
    }

    .btn-sec-continue {
        color: #fbbf24;
        border-color: rgba(251, 191, 36, 0.3);
    }

    .btn-sec-continue:hover {
        background: rgba(251, 191, 36, 0.08);
    }

    /* ════════════════════════════════════════
       Remove Confirmation Panel
       ════════════════════════════════════════ */
    .remove-confirm-panel {
        margin-top: 10px;
        padding: 12px 14px;
        border-radius: var(--radius-sm);
        background: rgba(239, 68, 68, 0.05);
        border: 1px solid rgba(239, 68, 68, 0.15);
        animation: fadeSlide 0.2s ease-out;
    }

    .remove-confirm-panel.step-final {
        background: rgba(239, 68, 68, 0.08);
        border-color: rgba(239, 68, 68, 0.3);
    }

    @keyframes fadeSlide {
        from { opacity: 0; transform: translateY(-6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .remove-warning {
        display: flex;
        gap: 8px;
        align-items: flex-start;
        margin-bottom: 10px;
        color: var(--danger);
    }

    .remove-warning span {
        font-size: 0.8rem;
        line-height: 1.45;
    }

    .remove-actions {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
    }

    .btn-danger-confirm {
        background: #ef4444;
        color: #fff;
        border: 1px solid #ef4444;
        padding: 6px 14px;
        font-size: 0.75rem;
    }

    .btn-danger-confirm:hover:not(:disabled) {
        background: #dc2626;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
    }
</style>
