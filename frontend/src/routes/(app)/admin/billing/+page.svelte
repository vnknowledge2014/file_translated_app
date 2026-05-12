<script lang="ts">
	import { onMount } from 'svelte';
	import { adminGetRevenue, adminGetPayments } from '$lib/api';
	import * as m from '$lib/paraglide/messages';

	let revenue: any = null;
	let payments: any = null;
	let loading = true;
	let error = '';
	let period = '30d';

	async function load() {
		loading = true;
		try {
			const [r, p] = await Promise.all([adminGetRevenue(period), adminGetPayments()]);
			revenue = r;
			payments = p;
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	onMount(load);

	function changePeriod(p: string) {
		period = p;
		load();
	}

	function formatTime(iso: string): string {
		if (!iso) return '—';
		return new Date(iso).toLocaleDateString();
	}
</script>

<svelte:head>
	<title>Revenue Analytics — InfiTrans Admin</title>
</svelte:head>

<div class="billing-page">
	<div class="page-header">
		<h1>{m.admin_billing_title()}</h1>
		<p class="subtitle">{m.admin_billing_subtitle()}</p>
	</div>

	<div class="period-tabs">
		{#each [['7d', m.admin_billing_7d()], ['30d', m.admin_billing_30d()], ['90d', m.admin_billing_90d()], ['365d', m.admin_billing_365d()], ['all', m.admin_billing_all()]] as [val, label]}
			<button class="tab" class:active={period === val} on:click={() => changePeriod(val)}>{label}</button>
		{/each}
	</div>

	{#if loading}
		<div class="loading"><div class="spinner"></div></div>
	{:else if error}
		<div class="error-banner">⚠️ {error}</div>
	{:else}
		<!-- Revenue Summary -->
		<div class="revenue-grid">
			<div class="rev-card primary">
				<span class="rev-value">${revenue?.total_usdc ?? 0}</span>
				<span class="rev-label">{m.admin_billing_total_revenue()}</span>
			</div>
			<div class="rev-card">
				<span class="rev-value">{revenue?.total_payments ?? 0}</span>
				<span class="rev-label">{m.admin_billing_total_payments()}</span>
			</div>
		</div>

		<!-- Revenue by Plan -->
		{#if revenue?.by_plan?.length}
			<div class="panel">
				<div class="panel-header"><h2>{m.admin_billing_by_plan()}</h2></div>
				<div class="panel-body">
					<div class="plan-revenue">
						{#each revenue.by_plan as item}
							<div class="plan-row">
								<span class="plan-badge plan-{item.plan || 'unknown'}">{item.plan || 'unknown'}</span>
								<span class="plan-total">${item.total ?? 0} USDC</span>
								<span class="plan-count">{item.count ?? 0} {m.admin_billing_payments()}</span>
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}

		<!-- Users by Plan -->
		{#if revenue?.users_by_plan?.length}
			<div class="panel">
				<div class="panel-header"><h2>{m.admin_billing_user_dist()}</h2></div>
				<div class="panel-body">
					<div class="plan-dist">
						{#each revenue.users_by_plan as item}
							<div class="dist-item">
								<span class="dist-plan plan-badge plan-{item.plan || 'free'}">{item.plan || 'free'}</span>
								<span class="dist-count">{item.count ?? 0} {m.admin_billing_users()}</span>
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}

		<!-- Recent Payments -->
		{#if payments?.payments?.length}
			<div class="panel">
				<div class="panel-header"><h2>{m.admin_billing_recent_payments()}</h2></div>
				<div class="panel-body">
					<table class="payments-table">
						<thead>
							<tr>
								<th>{m.admin_billing_col_user()}</th>
								<th>{m.admin_billing_col_plan()}</th>
								<th>{m.admin_billing_col_amount()}</th>
								<th>{m.admin_billing_col_status()}</th>
								<th>{m.admin_billing_col_date()}</th>
							</tr>
						</thead>
						<tbody>
							{#each payments.payments as p}
								<tr>
									<td>{p.user_id || '—'}</td>
									<td><span class="plan-badge plan-{p.plan}">{p.plan}</span></td>
									<td class="amount">${p.amount_usdc ?? 0}</td>
									<td><span class="pay-status pay-{p.status}">{p.status}</span></td>
									<td class="time">{formatTime(p.verified_at || p.created_at)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{:else}
			<div class="panel">
				<div class="panel-body"><p class="empty">{m.admin_billing_no_payments()}</p></div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.billing-page { max-width: 900px; }
	.page-header { margin-bottom: 20px; }
	.page-header h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0; }
	.subtitle { color: var(--text-muted); font-size: 0.85rem; margin: 4px 0 0; }

	.period-tabs { display: flex; gap: 6px; margin-bottom: 20px; }
	.tab {
		padding: 6px 14px; border-radius: 6px;
		background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle);
		color: var(--text-muted); font-size: 0.78rem; font-weight: 500;
		cursor: pointer; transition: all 0.15s;
	}
	.tab:hover { background: rgba(255,255,255,0.08); }
	.tab.active { background: rgba(99,102,241,0.15); color: var(--accent); border-color: rgba(99,102,241,0.3); }

	.loading { display: flex; justify-content: center; padding: 40px; }
	.spinner { width: 24px; height: 24px; border: 3px solid var(--border-subtle); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }
	.error-banner { padding: 12px 16px; border-radius: 10px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); color: var(--danger); font-size: 0.85rem; }

	.revenue-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
	.rev-card {
		padding: 24px; border-radius: 14px;
		background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle);
		text-align: center;
	}
	.rev-card.primary { background: rgba(99,102,241,0.08); border-color: rgba(99,102,241,0.2); }
	.rev-value { display: block; font-size: 2rem; font-weight: 700; color: var(--text-primary); }
	.rev-label { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }

	.panel { border-radius: 14px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); overflow: hidden; margin-bottom: 16px; }
	.panel-header { padding: 14px 20px; border-bottom: 1px solid var(--border-subtle); }
	.panel-header h2 { font-size: 0.88rem; font-weight: 600; color: var(--text-primary); margin: 0; }
	.panel-body { padding: 16px 20px; }

	.plan-revenue { display: flex; flex-direction: column; gap: 10px; }
	.plan-row { display: flex; align-items: center; gap: 14px; }
	.plan-total { font-weight: 600; color: var(--text-primary); font-size: 0.88rem; }
	.plan-count { color: var(--text-muted); font-size: 0.78rem; }

	.plan-badge { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
	.plan-free { background: rgba(100,100,100,0.15); color: #9ca3af; }
	.plan-pro { background: rgba(99,102,241,0.15); color: #818cf8; }
	.plan-enterprise { background: rgba(16,185,129,0.15); color: #34d399; }

	.plan-dist { display: flex; gap: 16px; flex-wrap: wrap; }
	.dist-item { display: flex; align-items: center; gap: 8px; }
	.dist-count { font-size: 0.82rem; color: var(--text-secondary); font-weight: 500; }

	.payments-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
	.payments-table th { text-align: left; padding: 8px 12px; color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border-subtle); }
	.payments-table td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); color: var(--text-secondary); }
	.amount { font-weight: 600; color: var(--text-primary); }
	.time { font-size: 0.75rem; color: var(--text-muted); }
	.pay-status { font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; }
	.pay-confirmed { background: rgba(16,185,129,0.1); color: #34d399; }
	.pay-pending { background: rgba(245,158,11,0.1); color: #fbbf24; }
	.empty { text-align: center; color: var(--text-muted); font-size: 0.82rem; padding: 20px 0; }
</style>
