<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { downloadJob, downloadXliff, uploadXliff } from '$lib/api';
    import { createEventDispatcher } from 'svelte';

    export let job: any;

    const dispatch = createEventDispatcher();

    // Map statuses to UI text and progress percent
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

    $: getProgress = () => {
        const s = job.status;
        if (s === 'queued') return 5;
        if (s === 'extracting') return 20;
        if (s === 'translating') return 20 + Math.floor((job.progress || 0) * 0.6);
        if (s === 'reconstructing') return 90;
        if (s === 'completed') return 100;
        if (s === 'failed') return 100;
        return 0;
    };

    let fileInput: HTMLInputElement;

    async function handleXliffUpload(e: Event) {
        const target = e.target as HTMLInputElement;
        if (!target.files?.length) return;
        try {
            await uploadXliff(job.id, target.files[0]);
            alert('XLIFF uploaded successfully. Reconstruction queued.');
        } catch (err: any) {
            alert('XLIFF upload failed: ' + err.message);
        } finally {
            target.value = '';
        }
    }
</script>

<div class="job-card" class:completed={job.status === 'completed'} class:failed={job.status === 'failed'}>
    <div class="job-header">
        <div style="display: flex; gap: 12px; align-items: center;">
            <div class="job-icon">
                {job.status === 'completed' ? '✅' : job.status === 'failed' ? '❌' : '⏳'}
            </div>
            <div>
                <div class="job-filename">{job.filename}</div>
                <div class="job-meta">
                    {job.source_lang.toUpperCase()} → {job.target_lang.toUpperCase()} | 
                    {new Date(job.created_at).toLocaleTimeString()}
                </div>
            </div>
        </div>
        <div class="job-status-badge">
            {getStatusText()}
        </div>
    </div>
    
    {#if job.status !== 'completed' && job.status !== 'failed'}
        <div class="progress-bar">
            <div class="progress-fill" style="width: {getProgress()}%"></div>
        </div>
    {/if}
    
    {#if job.error_message}
        <div class="job-error">
            {job.error_message}
        </div>
    {/if}
    
    <div class="job-actions">
        {#if job.status === 'completed'}
            <button class="btn btn-primary" on:click={() => downloadJob(job.id)}>
                📥 {m.job_download()}
            </button>
            <!-- Show Review if editor is supported (basic impl here) -->
            <button class="btn btn-secondary" on:click={() => dispatch('review', job.id)}>
                📝 {m.job_review()}
            </button>
        {/if}
        
        {#if job.has_xliff}
            <button class="btn btn-xliff" on:click={() => downloadXliff(job.id)}>
                📥 {m.job_download_xliff()}
            </button>
            <button class="btn btn-xliff" on:click={() => fileInput.click()}>
                📤 {m.job_upload_xliff()}
            </button>
            <input type="file" bind:this={fileInput} on:change={handleXliffUpload} accept=".xlf,.xliff" style="display:none;">
        {/if}
    </div>
</div>

<style>
    .job-card {
        background: var(--bg-card);
        border: 1px solid var(--border-glass);
        border-radius: var(--radius);
        padding: 24px;
        margin-bottom: 16px;
        backdrop-filter: blur(12px);
        transition: all 0.3s;
    }

    .job-card.completed {
        border-color: rgba(16, 185, 129, 0.3);
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.8), rgba(16, 185, 129, 0.02));
    }

    .job-card.failed {
        border-color: rgba(244, 63, 94, 0.3);
    }

    .job-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .job-icon {
        font-size: 1.5rem;
        background: var(--bg-glass);
        width: 40px; height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .job-filename {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 4px;
        word-break: break-all;
    }

    .job-meta {
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    .job-status-badge {
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 100px;
        background: var(--bg-glass);
        color: var(--text-secondary);
        font-weight: 500;
    }

    .progress-bar {
        height: 6px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 100px;
        overflow: hidden;
        margin-bottom: 16px;
    }

    .progress-fill {
        height: 100%;
        background: var(--gradient-primary);
        transition: width 0.5s ease;
    }

    .job-error {
        margin-bottom: 16px;
        padding: 12px;
        background: rgba(244, 63, 94, 0.1);
        color: var(--accent-rose);
        border-radius: var(--radius-sm);
        font-size: 0.9rem;
    }

    .job-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }

    .btn {
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        border: none;
        transition: all 0.2s;
    }

    .btn-primary {
        background: var(--accent-emerald);
        color: #fff;
    }

    .btn-primary:hover {
        background: #059669;
    }

    .btn-secondary {
        background: var(--bg-glass);
        color: var(--text-primary);
        border: 1px solid var(--border-glass);
    }

    .btn-secondary:hover {
        background: rgba(255, 255, 255, 0.1);
    }

    .btn-xliff {
        background: rgba(139, 92, 246, 0.1);
        color: var(--accent-purple);
        border: 1px solid rgba(139, 92, 246, 0.2);
    }

    .btn-xliff:hover {
        background: rgba(139, 92, 246, 0.2);
    }
</style>
