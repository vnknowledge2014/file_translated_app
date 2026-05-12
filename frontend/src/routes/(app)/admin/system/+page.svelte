<script lang="ts">
	import { onMount } from 'svelte';
	import { adminGetHealth, adminGetConfig, adminUpdateConfig } from '$lib/api';
	import * as m from '$lib/paraglide/messages';

	let health: any = null;
	let config: any = null;
	let loading = true;
	let error = '';
	let saving = false;
	let saveMsg = '';

	// Editable config
	let regEnabled = true;
	let maxFileSizeMB = 50;
	let maxWorkers = 1;

	async function load() {
		loading = true;
		try {
			const [h, c] = await Promise.all([adminGetHealth(), adminGetConfig()]);
			health = h;
			config = c;
			regEnabled = c.security?.registration_enabled ?? true;
			maxFileSizeMB = c.security?.max_file_size_mb ?? 50;
			maxWorkers = c.workers?.max_workers ?? 1;
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	onMount(load);

	async function saveConfig() {
		saving = true;
		saveMsg = '';
		try {
			await adminUpdateConfig({
				registration_enabled: regEnabled,
				max_file_size: maxFileSizeMB * 1024 * 1024,
				max_workers: maxWorkers,
			});
			saveMsg = '✅ Config updated (runtime only)';
			setTimeout(() => saveMsg = '', 3000);
		} catch (e: any) {
			saveMsg = `❌ ${e.message}`;
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head>
	<title>System Health — InfiTrans Admin</title>
</svelte:head>

<div class="system-page">
	<div class="page-header">
		<h1>{m.admin_system_title()}</h1>
		<p class="subtitle">{m.admin_system_subtitle()}</p>
	</div>

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="error-banner">⚠️ {error}</div>
	{:else}
		<!-- Overall Status -->
		<div class="status-banner" class:healthy={health?.status === 'ok'} class:degraded={health?.status !== 'ok'}>
			<span class="status-text">{health?.status === 'ok' ? m.admin_system_all_ok() : m.admin_system_degraded()}</span>
		</div>

		<div class="two-col">
			<!-- Services Health -->
			<div class="panel">
				<div class="panel-header"><h2>{m.admin_system_services()}</h2></div>
				<div class="panel-body">
					<div class="service-list">
						<div class="service-item">
							<span class="svc-dot" class:ok={health?.llm?.status === 'connected'}></span>
							<div class="svc-info">
								<span class="svc-name">{m.admin_system_llm()}</span>
								<span class="svc-detail">{health?.llm?.backend} — {health?.llm?.model}</span>
								<span class="svc-url">{health?.llm?.url}</span>
							</div>
							<span class="svc-status">{health?.llm?.status}</span>
						</div>
						<div class="service-item">
							<span class="svc-dot" class:ok={health?.database?.status === 'connected'}></span>
							<div class="svc-info">
								<span class="svc-name">{m.admin_system_db()}</span>
								<span class="svc-url">{health?.database?.url}</span>
							</div>
							<span class="svc-status">{health?.database?.status}</span>
						</div>
						<div class="service-item">
							<span class="svc-dot" class:ok={health?.storage?.status === 'connected'}></span>
							<div class="svc-info">
								<span class="svc-name">{m.admin_system_storage()}</span>
								<span class="svc-url">{health?.storage?.url}</span>
							</div>
							<span class="svc-status">{health?.storage?.status}</span>
						</div>
					</div>
				</div>
			</div>

			<!-- Database Tables -->
			{#if health?.database?.tables}
				<div class="panel">
					<div class="panel-header"><h2>{m.admin_db_tables()}</h2></div>
					<div class="panel-body">
						<div class="table-grid">
							{#each Object.entries(health.database.tables) as [table, count]}
								<div class="table-item">
									<span class="t-count">{count}</span>
									<span class="t-name">{table}</span>
								</div>
							{/each}
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Platform Configuration -->
		{#if config}
			<div class="panel config-panel">
				<div class="panel-header">
					<h2>{m.admin_system_config_title()}</h2>
					<span class="config-note">{m.admin_system_config_note()}</span>
				</div>
				<div class="panel-body">
					<div class="config-grid">
						<!-- LLM -->
						<div class="config-section">
							<h3>{m.admin_system_llm_settings()}</h3>
							<div class="config-row"><span>{m.admin_backend()}</span><span class="cv">{config.llm?.backend}</span></div>
							<div class="config-row"><span>{m.admin_model()}</span><span class="cv">{config.llm?.model}</span></div>
							<div class="config-row"><span>{m.admin_system_temperature()}</span><span class="cv">{config.translation?.temperature}</span></div>
							<div class="config-row"><span>{m.admin_system_context_window()}</span><span class="cv">{config.translation?.num_ctx}</span></div>
							<div class="config-row"><span>{m.admin_system_max_retries()}</span><span class="cv">{config.translation?.max_retries}</span></div>
						</div>

						<!-- Security (editable) -->
						<div class="config-section">
							<h3>{m.admin_system_security()}</h3>
							<label class="config-edit-row">
								<span>{m.admin_system_reg_enabled()}</span>
								<input type="checkbox" bind:checked={regEnabled} />
							</label>
							<label class="config-edit-row">
								<span>{m.admin_system_max_file_size()}</span>
								<input type="number" bind:value={maxFileSizeMB} min={1} max={500} />
							</label>
							<label class="config-edit-row">
								<span>{m.admin_system_max_workers()}</span>
								<input type="number" bind:value={maxWorkers} min={1} max={16} />
							</label>
						</div>

						<!-- Extraction -->
						<div class="config-section">
							<h3>{m.admin_system_extraction()}</h3>
							<div class="config-row"><span>{m.admin_system_max_segment()}</span><span class="cv">{config.extraction?.max_segment_chars}</span></div>
							<div class="config-row"><span>{m.admin_system_batch_chars()}</span><span class="cv">{config.extraction?.batch_max_chars}</span></div>
							<div class="config-row"><span>{m.admin_system_batch_segments()}</span><span class="cv">{config.extraction?.batch_max_segments}</span></div>
						</div>

						<!-- Language -->
						<div class="config-section">
							<h3>{m.admin_system_lang_defaults()}</h3>
							<div class="config-row"><span>{m.admin_system_source_lang()}</span><span class="cv">{config.language?.source_lang}</span></div>
							<div class="config-row"><span>{m.admin_system_target_lang()}</span><span class="cv">{config.language?.target_lang}</span></div>
							<div class="config-row"><span>{m.admin_system_default_domain()}</span><span class="cv">{config.language?.default_domain}</span></div>
						</div>
					</div>

					<div class="config-actions">
						<button class="save-btn" on:click={saveConfig} disabled={saving}>
							{saving ? m.admin_system_saving() : m.admin_system_save()}
						</button>
						{#if saveMsg}
							<span class="save-msg">{saveMsg}</span>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.system-page { max-width: 1000px; }
	.page-header { margin-bottom: 20px; }
	.page-header h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0; }
	.subtitle { color: var(--text-muted); font-size: 0.85rem; margin: 4px 0 0; }

	.loading { display: flex; justify-content: center; padding: 40px; }
	.spinner { width: 24px; height: 24px; border: 3px solid var(--border-subtle); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }
	.error-banner { padding: 12px 16px; border-radius: 10px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); color: var(--danger); font-size: 0.85rem; }

	.status-banner {
		padding: 14px 20px; border-radius: 12px; margin-bottom: 20px;
		text-align: center; font-weight: 600; font-size: 0.9rem;
	}
	.status-banner.healthy { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2); color: #34d399; }
	.status-banner.degraded { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.2); color: #fbbf24; }

	.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }

	.panel { border-radius: 14px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); overflow: hidden; }
	.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-bottom: 1px solid var(--border-subtle); }
	.panel-header h2 { font-size: 0.88rem; font-weight: 600; color: var(--text-primary); margin: 0; }
	.panel-body { padding: 16px 20px; }
	.config-note { font-size: 0.7rem; color: var(--text-muted); }

	.service-list { display: flex; flex-direction: column; gap: 14px; }
	.service-item { display: flex; align-items: flex-start; gap: 10px; }
	.svc-dot { width: 10px; height: 10px; border-radius: 50%; background: #f87171; flex-shrink: 0; margin-top: 4px; }
	.svc-dot.ok { background: #34d399; box-shadow: 0 0 6px rgba(52,211,153,0.4); }
	.svc-info { display: flex; flex-direction: column; flex: 1; }
	.svc-name { font-size: 0.85rem; font-weight: 600; color: var(--text-primary); }
	.svc-detail { font-size: 0.75rem; color: var(--text-secondary); }
	.svc-url { font-size: 0.7rem; color: var(--text-muted); font-family: monospace; }
	.svc-status { font-size: 0.75rem; color: var(--text-muted); font-weight: 500; }

	.table-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
	.table-item { display: flex; flex-direction: column; align-items: center; padding: 12px; border-radius: 8px; background: rgba(255,255,255,0.03); }
	.t-count { font-size: 1.2rem; font-weight: 700; color: var(--text-primary); }
	.t-name { font-size: 0.72rem; color: var(--text-muted); margin-top: 2px; }

	.config-panel { margin-bottom: 16px; }
	.config-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
	.config-section h3 { font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 10px; font-weight: 500; }
	.config-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 0.8rem; color: var(--text-muted); }
	.cv { color: var(--text-secondary); font-weight: 500; }

	.config-edit-row {
		display: flex; justify-content: space-between; align-items: center;
		padding: 5px 0; font-size: 0.8rem; color: var(--text-muted); cursor: pointer;
	}
	.config-edit-row input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); }
	.config-edit-row input[type="number"] {
		width: 70px; padding: 4px 8px; border-radius: 6px;
		background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle);
		color: var(--text-primary); font-size: 0.8rem; text-align: right;
	}

	.config-actions { display: flex; align-items: center; gap: 12px; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border-subtle); }
	.save-btn {
		padding: 8px 20px; border-radius: 8px; background: var(--accent);
		border: none; color: white; font-size: 0.82rem; font-weight: 500; cursor: pointer;
	}
	.save-btn:hover { filter: brightness(1.1); }
	.save-btn:disabled { opacity: 0.5; }
	.save-msg { font-size: 0.8rem; color: var(--text-secondary); }

	@media (max-width: 768px) {
		.two-col { grid-template-columns: 1fr; }
		.config-grid { grid-template-columns: 1fr; }
	}
</style>
