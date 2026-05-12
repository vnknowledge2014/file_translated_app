<script lang="ts">
	import { user } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import * as m from '$lib/paraglide/messages';

	onMount(() => {
		if ($user?.role !== 'superadmin') {
			goto('/translate');
		}
	});

	$: navItems = [
		{ href: '/admin', label: m.admin_nav_overview(), icon: 'grid' },
		{ href: '/admin/users', label: m.admin_nav_users(), icon: 'users' },
		{ href: '/admin/jobs', label: m.admin_nav_jobs(), icon: 'activity' },
		{ href: '/admin/billing', label: m.admin_nav_revenue(), icon: 'dollar' },
		{ href: '/admin/system', label: m.admin_nav_system(), icon: 'cpu' },
	];

	function isActive(href: string, currentPath: string) {
		if (href === '/admin') return currentPath === '/admin';
		return currentPath.startsWith(href);
	}
</script>

{#if $user?.role === 'superadmin'}
<div class="admin-layout">
	<aside class="admin-sidebar">
		<div class="sidebar-header">
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2">
				<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
			</svg>
			<span>{m.admin_nav_panel()}</span>
		</div>
		<nav class="sidebar-nav">
			{#each navItems as item}
				<a
					href={item.href}
					class="sidebar-link"
					class:active={isActive(item.href, $page.url.pathname)}
				>
					{#if item.icon === 'grid'}
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
					{:else if item.icon === 'users'}
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
					{:else if item.icon === 'activity'}
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
					{:else if item.icon === 'dollar'}
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
					{:else if item.icon === 'cpu'}
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>
					{/if}
					<span>{item.label}</span>
				</a>
			{/each}
		</nav>
		<div class="sidebar-footer">
			<a href="/translate" class="sidebar-link back-link">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
				<span>{m.admin_nav_back()}</span>
			</a>
		</div>
	</aside>
	<main class="admin-main">
		<slot />
	</main>
</div>
{/if}

<style>
	.admin-layout {
		display: flex;
		min-height: calc(100vh - 56px);
	}

	.admin-sidebar {
		width: 220px;
		flex-shrink: 0;
		background: rgba(255, 255, 255, 0.02);
		border-right: 1px solid var(--border-subtle);
		display: flex;
		flex-direction: column;
		padding: 16px 0;
	}

	.sidebar-header {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 0 16px 16px;
		border-bottom: 1px solid var(--border-subtle);
		margin-bottom: 8px;
		font-size: 0.85rem;
		font-weight: 700;
		color: var(--text-primary);
		letter-spacing: 0.02em;
	}

	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 8px;
		flex: 1;
	}

	.sidebar-link {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 12px;
		border-radius: 8px;
		color: var(--text-muted);
		text-decoration: none;
		font-size: 0.82rem;
		font-weight: 500;
		transition: all 0.15s ease;
	}

	.sidebar-link:hover {
		background: rgba(255, 255, 255, 0.06);
		color: var(--text-primary);
	}

	.sidebar-link.active {
		background: rgba(99, 102, 241, 0.12);
		color: var(--accent);
	}

	.sidebar-link.active svg {
		stroke: var(--accent);
	}

	.sidebar-footer {
		border-top: 1px solid var(--border-subtle);
		padding: 8px;
		margin-top: auto;
	}

	.back-link {
		color: var(--text-muted);
		opacity: 0.7;
	}

	.back-link:hover {
		opacity: 1;
		color: var(--text-primary);
	}

	.admin-main {
		flex: 1;
		padding: 28px 32px;
		overflow-y: auto;
	}

	@media (max-width: 768px) {
		.admin-layout {
			flex-direction: column;
		}
		.admin-sidebar {
			width: 100%;
			flex-direction: row;
			border-right: none;
			border-bottom: 1px solid var(--border-subtle);
			padding: 0;
			overflow-x: auto;
		}
		.sidebar-header {
			display: none;
		}
		.sidebar-nav {
			flex-direction: row;
			padding: 8px;
			gap: 4px;
		}
		.sidebar-footer {
			display: none;
		}
		.sidebar-link span {
			display: none;
		}
		.admin-main {
			padding: 16px;
		}
	}
</style>
