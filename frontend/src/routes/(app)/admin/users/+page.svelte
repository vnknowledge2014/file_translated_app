<script lang="ts">
	import { onMount } from 'svelte';
	import { adminListUsers, adminUpdateUser, adminDisableUser } from '$lib/api';
	import * as m from '$lib/paraglide/messages';
	import { showToast } from '$lib/stores/toast';

	let data: any = null;
	let loading = true;
	let error = '';
	let page = 1;
	let search = '';
	let filterPlan = '';
	let searchTimer: any;

	// Edit modal
	let editUser: any = null;
	let editRole = '';
	let editPlan = '';
	let editActive = true;
	let saving = false;

	async function loadUsers() {
		loading = true;
		try {
			data = await adminListUsers({ page, search: search || undefined, plan: filterPlan || undefined });
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	onMount(loadUsers);

	function onSearch() {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			page = 1;
			loadUsers();
		}, 300);
	}

	function onFilterPlan(plan: string) {
		filterPlan = filterPlan === plan ? '' : plan;
		page = 1;
		loadUsers();
	}

	function nextPage() { page++; loadUsers(); }
	function prevPage() { if (page > 1) { page--; loadUsers(); } }

	function openEdit(user: any) {
		editUser = user;
		editRole = user.role || 'user';
		editPlan = user.plan || 'free';
		editActive = user.is_active !== false;
	}

	async function saveEdit() {
		if (!editUser) return;
		saving = true;
		try {
			const userId = editUser.id.split(':')[1] || editUser.id;
			await adminUpdateUser(userId, { role: editRole, plan: editPlan });
			if (editActive !== (editUser.is_active !== false)) {
				await adminDisableUser(userId, editActive);
			}
			editUser = null;
			await loadUsers();
            showToast('User updated successfully', 'success');
		} catch (e: any) {
			showToast(e.message, 'error');
		} finally {
			saving = false;
		}
	}

	function shortAddr(addr: string): string {
		if (!addr) return '—';
		if (addr.length <= 12) return addr;
		return addr.slice(0, 6) + '…' + addr.slice(-4);
	}
</script>

<svelte:head>
	<title>User Management — InfiTrans Admin</title>
</svelte:head>

<div class="users-page">
	<div class="page-header">
		<h1>{m.admin_users_title()}</h1>
		<p class="subtitle">{m.admin_users_subtitle()}</p>
	</div>

	<div class="toolbar">
		<div class="search-box">
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
			<input type="text" bind:value={search} on:input={onSearch} placeholder="{m.admin_users_search()}" />
		</div>
		<div class="plan-filters">
			{#each ['free', 'pro', 'enterprise'] as plan}
				<button class="filter-btn" class:active={filterPlan === plan} on:click={() => onFilterPlan(plan)}>
					{plan}
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
						<th>{m.admin_users_col_username()}</th>
						<th>{m.admin_users_col_wallet()}</th>
						<th>{m.admin_users_col_role()}</th>
						<th>{m.admin_users_col_plan()}</th>
						<th>{m.admin_users_col_usage()}</th>
						<th>{m.admin_users_col_status()}</th>
						<th>{m.admin_users_col_actions()}</th>
					</tr>
				</thead>
				<tbody>
					{#each data.users as u}
						<tr>
							<td class="username">{u.username || '—'}</td>
							<td class="wallet"><code>{shortAddr(u.wallet_address)}</code></td>
							<td><span class="role-badge role-{u.role || 'user'}">{u.role || 'user'}</span></td>
							<td><span class="plan-badge plan-{u.plan || 'free'}">{u.plan || 'free'}</span></td>
							<td class="usage">{u.pages_used_month ?? 0} / {u.pages_limit ?? 100}</td>
							<td>
								{#if u.is_active !== false}
									<span class="active-dot active"></span>
								{:else}
									<span class="active-dot inactive"></span>
								{/if}
							</td>
							<td>
								<button class="action-btn" on:click={() => openEdit(u)}>{m.admin_users_edit()}</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<div class="pagination">
			<button disabled={page <= 1} on:click={prevPage}>{m.admin_prev()}</button>
			<span>{m.admin_users_page()} {page} {m.admin_users_of()} {data.pages || 1} ({data.total} {m.admin_users_count()})</span>
			<button disabled={page >= (data.pages || 1)} on:click={nextPage}>{m.admin_next()}</button>
		</div>
	{/if}
</div>

<!-- Edit Modal -->
{#if editUser}
	<div class="modal-overlay" on:click={() => editUser = null}>
		<div class="modal" on:click|stopPropagation>
			<h2>{m.admin_users_edit_title()}</h2>
			<p class="modal-sub">{editUser.username || editUser.wallet_address}</p>

			<label>
				{m.admin_users_role()}
				<select bind:value={editRole}>
					<option value="user">User</option>
					<option value="admin">Admin</option>
					<option value="superadmin">Superadmin</option>
				</select>
			</label>

			<label>
				{m.admin_users_plan()}
				<select bind:value={editPlan}>
					<option value="free">Free</option>
					<option value="pro">Pro</option>
					<option value="enterprise">Enterprise</option>
				</select>
			</label>

			<label class="checkbox-row">
				<input type="checkbox" bind:checked={editActive} />
				<span>{m.admin_users_account_active()}</span>
			</label>

			<div class="modal-actions">
				<button class="btn-cancel" on:click={() => editUser = null}>{m.admin_users_cancel()}</button>
				<button class="btn-save" on:click={saveEdit} disabled={saving}>
					{saving ? m.admin_users_saving() : m.admin_users_save()}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.users-page { max-width: 1100px; }
	.page-header { margin-bottom: 20px; }
	.page-header h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0; }
	.subtitle { color: var(--text-muted); font-size: 0.85rem; margin: 4px 0 0; }

	.toolbar {
		display: flex;
		gap: 12px;
		align-items: center;
		margin-bottom: 16px;
		flex-wrap: wrap;
	}

	.search-box {
		display: flex;
		align-items: center;
		gap: 8px;
		background: rgba(255,255,255,0.04);
		border: 1px solid var(--border-subtle);
		border-radius: 8px;
		padding: 0 12px;
		flex: 1;
		min-width: 200px;
	}

	.search-box input {
		background: none;
		border: none;
		color: var(--text-primary);
		padding: 10px 0;
		font-size: 0.82rem;
		outline: none;
		width: 100%;
	}

	.search-box svg { color: var(--text-muted); flex-shrink: 0; }

	.plan-filters { display: flex; gap: 6px; }

	.filter-btn {
		padding: 6px 14px;
		border-radius: 6px;
		background: rgba(255,255,255,0.04);
		border: 1px solid var(--border-subtle);
		color: var(--text-muted);
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		text-transform: capitalize;
		transition: all 0.15s;
	}

	.filter-btn:hover { background: rgba(255,255,255,0.08); color: var(--text-primary); }
	.filter-btn.active { background: rgba(99,102,241,0.15); color: var(--accent); border-color: rgba(99,102,241,0.3); }

	.loading { display: flex; justify-content: center; padding: 40px; }
	.spinner { width: 24px; height: 24px; border: 3px solid var(--border-subtle); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }

	.error-banner { padding: 12px 16px; border-radius: 10px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); color: var(--danger); font-size: 0.85rem; }

	.table-container {
		border-radius: 14px;
		border: 1px solid var(--border-subtle);
		overflow: hidden;
		background: rgba(255,255,255,0.02);
	}

	table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }

	th {
		text-align: left;
		padding: 12px 16px;
		color: var(--text-muted);
		font-weight: 500;
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid var(--border-subtle);
		background: rgba(255,255,255,0.02);
	}

	td {
		padding: 12px 16px;
		color: var(--text-secondary);
		border-bottom: 1px solid rgba(255,255,255,0.03);
	}

	tr:hover td { background: rgba(255,255,255,0.02); }
	.username { color: var(--text-primary); font-weight: 600; }
	.wallet code { font-size: 0.72rem; color: var(--text-muted); background: rgba(255,255,255,0.04); padding: 2px 6px; border-radius: 4px; }
	.usage { font-family: monospace; font-size: 0.75rem; }

	.role-badge, .plan-badge {
		font-size: 0.7rem;
		padding: 2px 8px;
		border-radius: 4px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.role-user { background: rgba(100,100,100,0.15); color: #9ca3af; }
	.role-admin { background: rgba(245,158,11,0.15); color: #fbbf24; }
	.role-superadmin { background: rgba(239,68,68,0.15); color: #f87171; }

	.plan-free { background: rgba(100,100,100,0.15); color: #9ca3af; }
	.plan-pro { background: rgba(99,102,241,0.15); color: #818cf8; }
	.plan-enterprise { background: rgba(16,185,129,0.15); color: #34d399; }

	.active-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
	.active-dot.active { background: #34d399; }
	.active-dot.inactive { background: #f87171; }

	.action-btn {
		padding: 4px 12px;
		border-radius: 6px;
		background: rgba(99,102,241,0.1);
		border: 1px solid rgba(99,102,241,0.2);
		color: var(--accent);
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.action-btn:hover { background: rgba(99,102,241,0.2); }

	.pagination {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 16px;
		padding: 16px;
		font-size: 0.8rem;
		color: var(--text-muted);
	}

	.pagination button {
		padding: 6px 14px;
		border-radius: 6px;
		background: rgba(255,255,255,0.04);
		border: 1px solid var(--border-subtle);
		color: var(--text-secondary);
		font-size: 0.78rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.pagination button:hover:not(:disabled) { background: rgba(255,255,255,0.08); }
	.pagination button:disabled { opacity: 0.3; cursor: not-allowed; }

	/* Modal */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0,0,0,0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		backdrop-filter: blur(4px);
	}

	.modal {
		background: var(--bg-primary, #18181b);
		border: 1px solid var(--border-subtle);
		border-radius: 16px;
		padding: 28px;
		width: 380px;
		max-width: 90vw;
	}

	.modal h2 { margin: 0 0 4px; font-size: 1.1rem; color: var(--text-primary); }
	.modal-sub { margin: 0 0 20px; font-size: 0.82rem; color: var(--text-muted); }

	.modal label {
		display: flex;
		flex-direction: column;
		gap: 6px;
		margin-bottom: 16px;
		font-size: 0.8rem;
		color: var(--text-secondary);
		font-weight: 500;
	}

	.modal select {
		padding: 8px 12px;
		border-radius: 8px;
		background: rgba(255,255,255,0.04);
		border: 1px solid var(--border-subtle);
		color: var(--text-primary);
		font-size: 0.82rem;
	}

	.checkbox-row {
		flex-direction: row !important;
		align-items: center;
		gap: 8px !important;
	}

	.checkbox-row input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); }

	.modal-actions {
		display: flex;
		gap: 10px;
		justify-content: flex-end;
		margin-top: 20px;
	}

	.btn-cancel, .btn-save {
		padding: 8px 18px;
		border-radius: 8px;
		font-size: 0.82rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.btn-cancel {
		background: rgba(255,255,255,0.04);
		border: 1px solid var(--border-subtle);
		color: var(--text-muted);
	}

	.btn-save {
		background: var(--accent);
		border: none;
		color: white;
	}

	.btn-save:hover { filter: brightness(1.1); }
	.btn-save:disabled { opacity: 0.5; }
</style>
