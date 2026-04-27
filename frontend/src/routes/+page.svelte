<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { onMount, onDestroy } from 'svelte';
    import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
    import LanguageBar from '$lib/components/LanguageBar.svelte';
    import UploadZone from '$lib/components/UploadZone.svelte';
    import JobCard from '$lib/components/JobCard.svelte';
    import GlossaryTable from '$lib/components/GlossaryTable.svelte';
    import BilingualEditor from '$lib/components/BilingualEditor.svelte';
    
    import { loadConfig } from '$lib/stores/config';
    import { fetchJobs } from '$lib/api';

    let jobs: any[] = [];
    let pollingInterval: any;
    let editingJobId: string | null = null;

    onMount(async () => {
        await loadConfig();
        await loadJobs();
        pollingInterval = setInterval(loadJobs, 2000);
    });

    onDestroy(() => {
        if (pollingInterval) clearInterval(pollingInterval);
    });

    async function loadJobs() {
        try {
            const data = await fetchJobs();
            // In a real app we'd merge cleanly. For now, just replace.
            jobs = data.jobs || [];
        } catch (e) {
            console.error('Polling failed', e);
        }
    }

    function handleUploadSuccess() {
        loadJobs();
    }
</script>

<LanguageSwitcher />

<header class="header">
    <div class="header-badge">
        <span class="dot"></span>
        {m.header_badge()}
    </div>
    <h1 id="lang-header">{m.header_title()}</h1>
    <p id="lang-subheader">{m.header_subtitle()}</p>
</header>

<LanguageBar />

<UploadZone on:uploaded={handleUploadSuccess} />

<div class="jobs-list" style="margin-top: 32px;">
    {#each jobs as job (job.id)}
        <JobCard {job} on:review={(e) => editingJobId = e.detail} />
    {/each}
</div>

<GlossaryTable />

{#if editingJobId}
    <BilingualEditor jobId={editingJobId} on:close={() => editingJobId = null} />
{/if}

<style>
    .header {
        text-align: center;
        margin-bottom: 48px;
    }

    .header-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 16px;
        border-radius: 100px;
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        font-size: 12px;
        color: var(--accent-cyan);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 20px;
    }

    .header-badge .dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: var(--accent-emerald);
        animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
    }

    h1 {
        font-size: 3rem;
        font-weight: 700;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 12px;
        letter-spacing: -0.02em;
    }

    .header p {
        color: var(--text-secondary);
        font-size: 1.1rem;
        font-weight: 300;
    }
</style>
