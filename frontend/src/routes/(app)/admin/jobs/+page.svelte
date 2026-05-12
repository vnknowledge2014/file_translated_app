<script lang="ts">
	import { onMount } from 'svelte';
	import { adminListJobs, adminDeleteJob } from '$lib/api';
	import * as m from '$lib/paraglide/messages';
	import { showToast } from '$lib/stores/toast';

	let data: any = null;
	let loading = true;
	let error = '';
	let page = 1;
	let filterStatus = '';

	async function loadJobs() {
		loading = true;
		try {
			data = await adminListJobs({ page, status: filterStatus || undefined });
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	onMount(loadJobs);

	function onFilterStatus(status: string) {
		filterStatus = filterStatus === status ? '' : status;
		page = 1;
		loadJobs();
	}

	function nextPage() { page++; loadJobs(); }
	function prevPage() { if (page > 1) { page--; loadJobs(); } }

	async function deleteJob(jobId: string) {
		if (!confirm(`Delete job ${jobId}? This cannot be undone.`)) return;
		try {
			await adminDeleteJob(jobId);
			await loadJobs();
			showToast('Job deleted successfully', 'success');
		} catch (e: any) {
			showToast(e.message, 'error');
		}
	}

	function formatTime(iso: string): string {
		if (!iso) return '—';
		return new Date(iso).toLocaleString();
	}

	function statusEmoji(s: string): string {
		if (s === 'completed') return '✅';
		if (s === 'failed') return '❌';
		if (s === 'translating' || s === 'extracting') return '🔄';
		if (s === 'queued' || s === 'pending') return '⏳';
		return '❓';
	}
</script>

<svelte:head>
	<title>Job Monitor — InfiTrans Admin</title>
</svelte:head>

<div class="jobs-page">
	<div class="page-header">
		<h1>{m.admin_jobs_title()}</h1>
		<p class="subtitle">{m.admin_jobs_subtitle()}</p>
	</div>

	<div class="toolbar">
		<div class="status-filters">
			{#each ['pending', 'queued', 'extracting', 'translating', 'completed', 'failed'] as status}
				<button class="filter-btn" class:active={filterStatus === status} on:click={() => onFilterStatus(status)}>
					{statusEmoji(status)} {status}
				</button>
			{/each}
		</div>
	</div>

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="error-banner">⚠️ {error}</div>
	{:else if data}
		<div class="table-container">
			<table>
				<thead>
					<tr>
						<th>{m.admin_jobs_col_id()}</th>
						<th>{m.admin_jobs_col_file()}</th>
						<th>{m.admin_jobs_col_status()}</th>
						<th>{m.admin_jobs_col_progress()}</th>
						<th>{m.admin_jobs_col_lang()}</th>
						<th>{m.admin_jobs_col_duration()}</th>
						<th>{m.admin_jobs_col_created()}</th>
						<th>{m.admin_jobs_col_actions()}</th>
					</tr>
				</thead>
				<tbody>
					{#each data.jobs as job}
						<tr>
							<td class="id"><code>{(job.id || '').split(':')[1]?.slice(0, 8) || job.id}</code></td>
							<td class="filename">{job.filename || '—'}</td>
							<td>
								<span class="status-badge status-{job.status}">
									{statusEmoji(job.status)} {job.status}
								</span>
							</td>
							<td class="progress-cell">
								<div class="progress-bar">
									<div class="progress-fill" style="width: {(job.progress || 0) * 100}%"></div>
								</div>
								<span class="progress-text">{Math.round((job.progress || 0) * 100)}%</span>
							</td>
							<td class="lang">{job.source_lang}→{job.target_lang}</td>
							<td class="duration">{job.duration_seconds ? `${job.duration_seconds.toFixed(1)}s` : '—'}</td>
							<td class="time">{formatTime(job.created_at)}</td>
							<td>
								<button class="delete-btn" on:click={() => deleteJob(job.id)} title="Delete job">
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<div class="pagination">
			<button disabled={page <= 1} on:click={prevPage}>{m.admin_prev()}</button>
			<span>{m.admin_users_page()} {page} {m.admin_users_of()} {data.pages || 1} ({data.total} {m.admin_jobs_count()})</span>
			<button disabled={page >= (data.pages || 1)} on:click={nextPage}>{m.admin_next()}</button>
		</div>
	{/if}
</div>

<style>
	.jobs-page { max-width: 1200px; }
	.page-header { margin-bottom: 20px; }
	.page-header h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0; }
	.subtitle { color: var(--text-muted); font-size: 0.85rem; margin: 4px 0 0; }

	.toolbar { margin-bottom: 16px; }
	.status-filters { display: flex; gap: 6px; flex-wrap: wrap; }

	.filter-btn {
		padding: 6px 12px; border-radius: 6px;
		background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle);
		color: var(--text-muted); font-size: 0.73rem; font-weight: 500;
		cursor: pointer; text-transform: capitalize; transition: all 0.15s;
	}
	.filter-btn:hover { background: rgba(255,255,255,0.08); color: var(--text-primary); }
	.filter-btn.active { background: rgba(99,102,241,0.15); color: var(--accent); border-color: rgba(99,102,241,0.3); }

	.loading { display: flex; justify-content: center; padding: 40px; }
	.spinner { width: 24px; height: 24px; border: 3px solid var(--border-subtle); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }
	.error-banner { padding: 12px 16px; border-radius: 10px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); color: var(--danger); font-size: 0.85rem; }

	.table-container {
		border-radius: 14px; border: 1px solid var(--border-subtle);
		overflow: hidden; background: rgba(255,255,255,0.02);
	}

	table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
	th {
		text-align: left; padding: 12px 14px; color: var(--text-muted);
		font-weight: 500; font-size: 0.7rem; text-transform: uppercase;
		letter-spacing: 0.05em; border-bottom: 1px solid var(--border-subtle);
		background: rgba(255,255,255,0.02);
	}
	td { padding: 10px 14px; color: var(--text-secondary); border-bottom: 1px solid rgba(255,255,255,0.03); }
	tr:hover td { background: rgba(255,255,255,0.02); }
	.id code { font-size: 0.7rem; color: var(--text-muted); background: rgba(255,255,255,0.04); padding: 2px 6px; border-radius: 4px; }
	.filename { color: var(--text-primary); font-weight: 500; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.lang { font-family: monospace; font-size: 0.72rem; }
	.duration, .time { font-size: 0.72rem; color: var(--text-muted); }

	.status-badge { font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }
	.status-completed { background: rgba(16,185,129,0.1); color: #34d399; }
	.status-failed { background: rgba(239,68,68,0.1); color: #f87171; }
	.status-translating, .status-extracting { background: rgba(99,102,241,0.1); color: #818cf8; }
	.status-queued, .status-pending { background: rgba(245,158,11,0.1); color: #fbbf24; }

	.progress-cell { display: flex; align-items: center; gap: 8px; }
	.progress-bar { width: 60px; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
	.progress-fill { height: 100%; background: var(--accent); border-radius: 3px; transition: width 0.3s; }
	.progress-text { font-size: 0.7rem; color: var(--text-muted); font-family: monospace; }

	.delete-btn {
		padding: 4px 8px; border-radius: 6px; background: rgba(239,68,68,0.1);
		border: 1px solid rgba(239,68,68,0.2); color: #f87171; cursor: pointer;
		transition: all 0.15s; display: flex; align-items: center;
	}
	.delete-btn:hover { background: rgba(239,68,68,0.2); }

	.pagination {
		display: flex; justify-content: center; align-items: center;
		gap: 16px; padding: 16px; font-size: 0.8rem; color: var(--text-muted);
	}
	.pagination button {
		padding: 6px 14px; border-radius: 6px;
		background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle);
		color: var(--text-secondary); font-size: 0.78rem; cursor: pointer;
	}
	.pagination button:hover:not(:disabled) { background: rgba(255,255,255,0.08); }
	.pagination button:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
