<script lang="ts">
	import { onMount } from 'svelte';
	import { adminGetStats, adminGetHealth } from '$lib/api';
	import * as m from '$lib/paraglide/messages';

	let stats: any = null;
	let health: any = null;
	let loading = true;
	let error = '';

	onMount(async () => {
		try {
			const [s, h] = await Promise.all([adminGetStats(), adminGetHealth()]);
			stats = s;
			health = h;
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	});

	function formatBytes(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
	}

	function formatTime(iso: string): string {
		if (!iso) return '—';
		const d = new Date(iso);
		const now = new Date();
		const diff = now.getTime() - d.getTime();
		if (diff < 60000) return 'just now';
		if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
		if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
		return d.toLocaleDateString();
	}

	function statusEmoji(status: string): string {
		if (status === 'completed') return '✅';
		if (status === 'failed') return '❌';
		if (status === 'translating' || status === 'extracting') return '🔄';
		if (status === 'queued' || status === 'pending') return '⏳';
		return '❓';
	}

	$: jobTotal = stats?.jobs?.by_status
		? Object.values(stats.jobs.by_status).reduce((a: number, b: any) => Number(a) + Number(b), 0)
		: 0;
</script>

<svelte:head>
	<title>Admin Dashboard — InfiTrans</title>
</svelte:head>

<div class="admin-overview">
	<div class="page-header">
		<h1>{m.admin_overview_title()}</h1>
		<p class="subtitle">{m.admin_overview_subtitle()}</p>
	</div>

	{#if loading}
		<div class="loading-state">
			<div class="spinner"></div>
			<p>{m.admin_loading()}</p>
		</div>
	{:else if error}
		<div class="error-banner">
			<span>⚠️</span>
			<p>{error}</p>
		</div>
	{:else}
		<!-- Stat Cards -->
		<div class="stat-grid">
			<div class="stat-card">
				<div class="stat-icon users">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
				</div>
				<div class="stat-content">
					<span class="stat-value">{stats?.users?.total ?? 0}</span>
					<span class="stat-label">{m.admin_stat_total_users()}</span>
					<span class="stat-sub">{stats?.users?.active ?? 0} {m.admin_stat_active()}</span>
				</div>
			</div>
			<div class="stat-card">
				<div class="stat-icon jobs">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
				</div>
				<div class="stat-content">
					<span class="stat-value">{stats?.jobs?.total ?? 0}</span>
					<span class="stat-label">{m.admin_stat_total_jobs()}</span>
					<span class="stat-sub">{stats?.jobs?.by_status?.completed ?? 0} {m.admin_stat_completed()}</span>
				</div>
			</div>
			<div class="stat-card">
				<div class="stat-icon revenue">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
				</div>
				<div class="stat-content">
					<span class="stat-value">${stats?.revenue?.total_usdc ?? 0}</span>
					<span class="stat-label">{m.admin_stat_total_revenue()}</span>
					<span class="stat-sub">${stats?.revenue?.this_month_usdc ?? 0} {m.admin_stat_this_month()}</span>
				</div>
			</div>
			<div class="stat-card">
				<div class="stat-icon storage">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
				</div>
				<div class="stat-content">
					<span class="stat-value">{formatBytes(stats?.storage?.total_bytes ?? 0)}</span>
					<span class="stat-label">{m.admin_stat_storage()}</span>
					<span class="stat-sub">{(stats?.storage?.uploads_count ?? 0) + (stats?.storage?.outputs_count ?? 0)} {m.admin_stat_files()}</span>
				</div>
			</div>
		</div>

		<!-- Two-column layout -->
		<div class="two-col">
			<!-- Recent Jobs -->
			<div class="panel">
				<div class="panel-header">
					<h2>{m.admin_recent_jobs()}</h2>
					<a href="/admin/jobs" class="panel-link">{m.admin_view_all()}</a>
				</div>
				<div class="panel-body">
					{#if stats?.recent_jobs?.length}
						<table class="mini-table">
							<thead>
								<tr>
									<th>{m.admin_col_file()}</th>
									<th>{m.admin_col_status()}</th>
									<th>{m.admin_col_lang()}</th>
									<th>{m.admin_col_time()}</th>
								</tr>
							</thead>
							<tbody>
								{#each stats.recent_jobs as job}
									<tr>
										<td class="filename">{job.filename}</td>
										<td>
											<span class="status-badge status-{job.status}">
												{statusEmoji(job.status)} {job.status}
											</span>
										</td>
										<td class="lang">{job.source_lang}→{job.target_lang}</td>
										<td class="time">{formatTime(job.created_at)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<p class="empty">{m.admin_no_jobs()}</p>
					{/if}
				</div>
			</div>

			<!-- System Health -->
			<div class="panel">
				<div class="panel-header">
					<h2>{m.admin_system_health()}</h2>
					<a href="/admin/system" class="panel-link">{m.admin_details()}</a>
				</div>
				<div class="panel-body">
					{#if health}
						<div class="health-grid">
							<div class="health-item">
								<span class="health-dot" class:ok={health.llm?.status === 'connected'}></span>
								<span class="health-label">LLM</span>
								<span class="health-value">{health.llm?.status}</span>
							</div>
							<div class="health-item">
								<span class="health-dot" class:ok={health.database?.status === 'connected'}></span>
								<span class="health-label">Database</span>
								<span class="health-value">{health.database?.status}</span>
							</div>
							<div class="health-item">
								<span class="health-dot" class:ok={health.storage?.status === 'connected'}></span>
								<span class="health-label">Storage</span>
								<span class="health-value">{health.storage?.status}</span>
							</div>
						</div>
						<div class="health-meta">
							<div class="meta-row">
								<span>{m.admin_model()}</span>
								<span class="meta-value">{health.llm?.model ?? '—'}</span>
							</div>
							<div class="meta-row">
								<span>{m.admin_backend()}</span>
								<span class="meta-value">{health.llm?.backend ?? '—'}</span>
							</div>
							<div class="meta-row">
								<span>{m.admin_workers()}</span>
								<span class="meta-value">{health.config?.max_workers ?? '—'}</span>
							</div>
							<div class="meta-row">
								<span>{m.admin_status_label()}</span>
								<span class="meta-value overall-{health.status}">{health.status === 'ok' ? m.admin_healthy() : m.admin_degraded()}</span>
							</div>
						</div>

						{#if health.database?.tables}
							<div class="table-counts">
								<h3>{m.admin_db_tables()}</h3>
								<div class="table-count-grid">
									{#each Object.entries(health.database.tables) as [table, count]}
										<div class="tc-item">
											<span class="tc-count">{count}</span>
											<span class="tc-name">{table}</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					{/if}
				</div>
			</div>
		</div>

		<!-- Job Status Breakdown -->
		{#if stats?.jobs?.by_status && Object.keys(stats.jobs.by_status).length}
			<div class="panel full-width">
				<div class="panel-header">
					<h2>{m.admin_job_status_dist()}</h2>
				</div>
				<div class="panel-body">
					<div class="status-bars">
						{#each Object.entries(stats.jobs.by_status) as [status, count]}
							<div class="status-bar-item">
								<div class="bar-label">
									<span>{statusEmoji(status)} {status}</span>
									<span class="bar-count">{count}</span>
								</div>
								<div class="bar-track">
									<div class="bar-fill bar-{status}" style="width: {jobTotal > 0 ? (Number(count) / Number(jobTotal) * 100) : 0}%"></div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.admin-overview {
		max-width: 1100px;
	}

	.page-header {
		margin-bottom: 28px;
	}

	.page-header h1 {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0;
	}

	.subtitle {
		color: var(--text-muted);
		font-size: 0.85rem;
		margin: 4px 0 0;
	}

	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
		padding: 60px 0;
		color: var(--text-muted);
	}

	.spinner {
		width: 28px;
		height: 28px;
		border: 3px solid var(--border-subtle);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error-banner {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 16px;
		border-radius: 10px;
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.2);
		color: var(--danger);
		font-size: 0.85rem;
	}

	/* Stat Cards */
	.stat-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 16px;
		margin-bottom: 24px;
	}

	.stat-card {
		display: flex;
		align-items: flex-start;
		gap: 14px;
		padding: 20px;
		border-radius: 14px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--border-subtle);
		transition: all 0.2s ease;
	}

	.stat-card:hover {
		background: rgba(255, 255, 255, 0.05);
		border-color: rgba(255, 255, 255, 0.12);
	}

	.stat-icon {
		width: 42px;
		height: 42px;
		border-radius: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.stat-icon.users { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
	.stat-icon.jobs { background: rgba(16, 185, 129, 0.15); color: #34d399; }
	.stat-icon.revenue { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
	.stat-icon.storage { background: rgba(139, 92, 246, 0.15); color: #a78bfa; }

	.stat-content {
		display: flex;
		flex-direction: column;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1.1;
	}

	.stat-label {
		font-size: 0.78rem;
		color: var(--text-muted);
		margin-top: 4px;
		font-weight: 500;
	}

	.stat-sub {
		font-size: 0.72rem;
		color: var(--text-muted);
		opacity: 0.7;
		margin-top: 2px;
	}

	/* Two Column */
	.two-col {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		margin-bottom: 16px;
	}

	/* Panel */
	.panel {
		border-radius: 14px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--border-subtle);
		overflow: hidden;
	}

	.panel.full-width {
		margin-bottom: 16px;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid var(--border-subtle);
	}

	.panel-header h2 {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.panel-link {
		font-size: 0.75rem;
		color: var(--accent);
		text-decoration: none;
		font-weight: 500;
	}

	.panel-link:hover {
		text-decoration: underline;
	}

	.panel-body {
		padding: 16px 20px;
	}

	/* Mini Table */
	.mini-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.78rem;
	}

	.mini-table th {
		text-align: left;
		color: var(--text-muted);
		font-weight: 500;
		padding: 6px 8px;
		border-bottom: 1px solid var(--border-subtle);
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.mini-table td {
		padding: 8px;
		color: var(--text-secondary);
		border-bottom: 1px solid rgba(255, 255, 255, 0.03);
	}

	.filename {
		max-width: 140px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--text-primary) !important;
		font-weight: 500;
	}

	.lang { font-family: monospace; font-size: 0.72rem; }
	.time { font-size: 0.72rem; color: var(--text-muted) !important; }

	.status-badge {
		font-size: 0.72rem;
		padding: 2px 6px;
		border-radius: 4px;
		white-space: nowrap;
	}

	.status-completed { background: rgba(16, 185, 129, 0.1); color: #34d399; }
	.status-failed { background: rgba(239, 68, 68, 0.1); color: #f87171; }
	.status-translating, .status-extracting { background: rgba(99, 102, 241, 0.1); color: #818cf8; }
	.status-queued, .status-pending { background: rgba(245, 158, 11, 0.1); color: #fbbf24; }

	.empty {
		text-align: center;
		color: var(--text-muted);
		font-size: 0.82rem;
		padding: 20px 0;
	}

	/* Health */
	.health-grid {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin-bottom: 16px;
	}

	.health-item {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.health-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #f87171;
		flex-shrink: 0;
	}

	.health-dot.ok {
		background: #34d399;
		box-shadow: 0 0 6px rgba(52, 211, 153, 0.4);
	}

	.health-label {
		font-size: 0.8rem;
		color: var(--text-secondary);
		font-weight: 500;
		width: 70px;
	}

	.health-value {
		font-size: 0.78rem;
		color: var(--text-muted);
	}

	.health-meta {
		border-top: 1px solid var(--border-subtle);
		padding-top: 12px;
		margin-bottom: 16px;
	}

	.meta-row {
		display: flex;
		justify-content: space-between;
		padding: 4px 0;
		font-size: 0.78rem;
		color: var(--text-muted);
	}

	.meta-value {
		color: var(--text-secondary);
		font-weight: 500;
	}

	.table-counts h3 {
		font-size: 0.78rem;
		color: var(--text-muted);
		font-weight: 500;
		margin: 0 0 8px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.table-count-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 6px;
	}

	.tc-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 8px;
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.03);
	}

	.tc-count {
		font-size: 1rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.tc-name {
		font-size: 0.68rem;
		color: var(--text-muted);
	}

	/* Status Bars */
	.status-bars {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.status-bar-item {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.bar-label {
		display: flex;
		justify-content: space-between;
		font-size: 0.78rem;
		color: var(--text-secondary);
	}

	.bar-count {
		color: var(--text-muted);
		font-weight: 600;
	}

	.bar-track {
		height: 8px;
		border-radius: 4px;
		background: rgba(255, 255, 255, 0.06);
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		border-radius: 4px;
		transition: width 0.6s ease;
	}

	.bar-completed { background: linear-gradient(90deg, #10b981, #34d399); }
	.bar-failed { background: linear-gradient(90deg, #ef4444, #f87171); }
	.bar-translating, .bar-extracting { background: linear-gradient(90deg, #6366f1, #818cf8); }
	.bar-queued, .bar-pending { background: linear-gradient(90deg, #f59e0b, #fbbf24); }

	@media (max-width: 900px) {
		.stat-grid { grid-template-columns: repeat(2, 1fr); }
		.two-col { grid-template-columns: 1fr; }
	}

	@media (max-width: 500px) {
		.stat-grid { grid-template-columns: 1fr; }
	}
</style>
