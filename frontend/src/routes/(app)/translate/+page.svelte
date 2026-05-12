<script lang="ts">
	import * as m from '$lib/paraglide/messages';
	import { onMount, onDestroy } from 'svelte';
	import LanguageBar from '$lib/components/LanguageBar.svelte';
	import UploadZone from '$lib/components/UploadZone.svelte';
	import JobCard from '$lib/components/JobCard.svelte';
	import GlossaryTable from '$lib/components/GlossaryTable.svelte';
	import XliffImport from '$lib/components/XliffImport.svelte';
	import BilingualEditor from '$lib/components/BilingualEditor.svelte';
	import IconFile from '$lib/components/icons/IconFile.svelte';
	import IconClock from '$lib/components/icons/IconClock.svelte';
	import IconCheckCircle from '$lib/components/icons/IconCheckCircle.svelte';
	
	import { loadConfig } from '$lib/stores/config';
	import { fetchJobs, subscribeJobEvents } from '$lib/api';

	let jobs: any[] = [];
	let pollingInterval: any;
	let unsubscribeSSE: (() => void) | null = null;
	let editingJobId: string | null = null;
	let showAdvanced = false;
	let advancedTab: 'glossary' | 'xliff' = 'glossary';

	// Stats
	$: totalJobs = jobs.length;
	$: completedJobs = jobs.filter(j => j.status === 'completed').length;
	$: activeJobs = jobs.filter(j => !['completed', 'failed'].includes(j.status)).length;

	onMount(async () => {
		await loadConfig();
		await loadJobs(); // Initial load to ensure we have the list immediately

		// The reconnect wrapper in api.ts is robust and handles reconnections natively,
		// so no need for periodic polling fallbacks here.
		unsubscribeSSE = subscribeJobEvents({
			onInit: (data) => { jobs = data; },
			onProgress: updateJobInList,
			onCompleted: updateJobInList,
			onFailed: updateJobInList,
			onQueued: updateJobInList,
		});
	});

	onDestroy(() => {
		if (unsubscribeSSE) unsubscribeSSE();
	});

	function updateJobInList(eventData: any) {
		const exists = jobs.some(j => j.id === eventData.job_id);
		if (exists) {
			jobs = jobs.map(j => 
				j.id === eventData.job_id 
					? { ...j, ...eventData } 
					: j
			);
		} else {
			// Prepend new jobs to the list
			jobs = [eventData, ...jobs];
		}
	}

	async function loadJobs() {
		try {
			const data = await fetchJobs();
			jobs = Array.isArray(data) ? data : (data.jobs || []);
		} catch (e) {
			console.error('Polling failed', e);
		}
	}

	function handleUploadSuccess() {
		loadJobs();
	}
</script>

<svelte:head>
	<title>Translate | InfiTrans</title>
</svelte:head>

<div class="workspace">
	<!-- Primary Card: Configure & Upload -->
	<div class="primary-card">
		<div class="card-inner">
			<!-- Step 1: Language Config -->
			<div class="step">
				<div class="step-indicator">
					<span class="step-num">1</span>
					<span class="step-label">{m.step_configure()}</span>
				</div>
				<LanguageBar />
			</div>

			<div class="step-divider"></div>

			<!-- Step 2: Upload -->
			<div class="step">
				<div class="step-indicator">
					<span class="step-num">2</span>
					<span class="step-label">{m.step_upload()}</span>
				</div>
				<UploadZone on:uploaded={handleUploadSuccess} />
			</div>
		</div>

		<!-- Advanced Tools Toggle -->
		<button class="advanced-toggle" on:click={() => showAdvanced = !showAdvanced}>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="12" cy="12" r="3"/>
				<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
			</svg>
			{showAdvanced ? m.advanced_hide() : m.advanced_show()}
			<svg class="chevron" class:open={showAdvanced} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M6 9l6 6 6-6"/>
			</svg>
		</button>

		<!-- Advanced Tools Panel -->
		{#if showAdvanced}
			<div class="advanced-panel">
				<div class="advanced-tabs">
					<button 
						class="adv-tab" 
						class:active={advancedTab === 'glossary'} 
						on:click={() => advancedTab = 'glossary'}
					>{ m.tab_glossary() }</button>
					<button 
						class="adv-tab" 
						class:active={advancedTab === 'xliff'} 
						on:click={() => advancedTab = 'xliff'}
					>{ m.tab_xliff_import() }</button>
				</div>
				<div class="advanced-content">
					{#if advancedTab === 'glossary'}
						<GlossaryTable />
					{:else}
						<XliffImport />
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<!-- Jobs Section -->
	{#if jobs.length > 0}
		<div class="jobs-section">
			<div class="jobs-header">
				<div class="jobs-title">
					<IconFile size={18} color="var(--accent)" />
					<h2>{m.jobs_title()}</h2>
				</div>
				<div class="stats-pills">
					{#if activeJobs > 0}
						<span class="pill pill-active">
							<IconClock size={12} color="currentColor" />
							{activeJobs} {m.jobs_active()}
						</span>
					{/if}
					{#if completedJobs > 0}
						<span class="pill pill-done">
							<IconCheckCircle size={12} color="currentColor" />
							{completedJobs} {m.jobs_done()}
						</span>
					{/if}
					<span class="pill pill-total">{totalJobs}</span>
				</div>
			</div>

			<div class="jobs-list">
				{#each jobs as job (job.id)}
					<JobCard {job} on:review={(e) => editingJobId = e.detail} on:retry={loadJobs} on:remove={loadJobs} />
				{/each}
			</div>
		</div>
	{/if}
</div>

<!-- Bilingual Editor Overlay -->
{#if editingJobId}
	<BilingualEditor jobId={editingJobId} on:close={() => editingJobId = null} />
{/if}

<style>
	.workspace {
		display: flex;
		flex-direction: column;
		gap: 28px;
		max-width: 880px;
		margin: 0 auto;
		padding: 0 0 80px;
	}

	/* ── Primary Card ── */
	.primary-card {
		background: var(--bg-secondary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
		overflow: hidden;
	}

	.card-inner {
		padding: 32px 32px 28px;
	}

	/* ── Steps ── */
	.step {
		animation: fadeIn 0.35s ease-out;
	}

	.step-indicator {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-bottom: 16px;
	}

	.step-num {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: var(--accent);
		color: #fff;
		font-size: 0.7rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.step-label {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text-muted);
	}

	.step-divider {
		height: 1px;
		background: var(--border-subtle);
		margin: 24px 0;
	}

	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(8px); }
		to { opacity: 1; transform: translateY(0); }
	}

	/* ── Advanced Toggle ── */
	.advanced-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		width: 100%;
		padding: 12px;
		background: var(--bg-elevated);
		border: none;
		border-top: 1px solid var(--border-subtle);
		color: var(--text-muted);
		font-size: 0.78rem;
		font-weight: 500;
		font-family: inherit;
		cursor: pointer;
		transition: all var(--transition-base);
	}

	.advanced-toggle:hover {
		color: var(--accent);
		background: rgba(20, 184, 166, 0.04);
	}

	.chevron {
		transition: transform 0.25s ease;
	}

	.chevron.open {
		transform: rotate(180deg);
	}

	/* ── Advanced Panel ── */
	.advanced-panel {
		border-top: 1px solid var(--border-subtle);
		animation: slideDown 0.25s ease-out;
	}

	@keyframes slideDown {
		from { opacity: 0; max-height: 0; }
		to { opacity: 1; max-height: 600px; }
	}

	.advanced-tabs {
		display: flex;
		border-bottom: 1px solid var(--border-subtle);
	}

	.adv-tab {
		flex: 1;
		padding: 10px 16px;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-muted);
		font-size: 0.8rem;
		font-weight: 500;
		font-family: inherit;
		cursor: pointer;
		transition: all var(--transition-base);
	}

	.adv-tab:hover {
		color: var(--text-secondary);
	}

	.adv-tab.active {
		color: var(--accent);
		border-bottom-color: var(--accent);
	}

	.advanced-content {
		padding: 0;
	}

	.advanced-content :global(.glossary-section),
	.advanced-content :global(.xliff-section) {
		margin-top: 0;
		border: none;
		border-radius: 0;
	}

	/* ── Jobs Section ── */
	.jobs-section {
		animation: fadeIn 0.4s ease-out;
	}

	.jobs-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 14px;
		flex-wrap: wrap;
		gap: 10px;
	}

	.jobs-title {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.jobs-title h2 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0;
	}

	/* ── Stats Pills ── */
	.stats-pills {
		display: flex;
		gap: 6px;
		align-items: center;
	}

	.pill {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 3px 10px;
		border-radius: 100px;
		font-size: 0.7rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.pill-active {
		background: rgba(251, 191, 36, 0.12);
		color: #fbbf24;
		border: 1px solid rgba(251, 191, 36, 0.25);
	}

	.pill-done {
		background: rgba(34, 197, 94, 0.12);
		color: #22c55e;
		border: 1px solid rgba(34, 197, 94, 0.25);
	}

	.pill-total {
		background: var(--bg-elevated);
		color: var(--text-muted);
		border: 1px solid var(--border-subtle);
		min-width: 24px;
		justify-content: center;
	}

	/* ── Jobs List ── */
	.jobs-list {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	@media (max-width: 640px) {
		.card-inner {
			padding: 20px 16px;
		}
	}
</style>
