<script lang="ts">
	import { isAuthenticated, user, logout, shortWallet } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { uiLang } from '$lib/stores/i18n';
	import * as m from '$lib/paraglide/messages';
	import IconLogo from '$lib/components/icons/IconLogo.svelte';
	import IconUser from '$lib/components/icons/IconUser.svelte';
	import IconLogout from '$lib/components/icons/IconLogout.svelte';
	import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';

	onMount(() => {
		if (!$isAuthenticated) {
			goto('/login');
		}
	});

	function handleLogout() {
		logout();
		goto('/login');
	}
</script>

{#key $uiLang}
{#if $isAuthenticated}
<div class="app-layout">
	<div class="bg-gradient"></div>
	<header class="topbar">
		<div class="topbar-inner">
			<a href="/translate" class="topbar-brand">
				<IconLogo size={24} color="var(--accent)" />
				<span class="topbar-name">InfiTrans</span>
			</a>
			<div class="topbar-right">
				<LanguageSwitcher />
				{#if $user?.role === 'superadmin'}
					<a href="/admin" class="nav-link admin-link" title="{m.admin_nav_link()}">
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
						</svg>
						<span class="nav-label">{m.admin_nav_link()}</span>
					</a>
				{/if}
				<a href="/api-docs" class="nav-link" title="{m.nav_api_docs()}">
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
						<polyline points="14 2 14 8 20 8"/>
						<line x1="16" y1="13" x2="8" y2="13"/>
						<line x1="16" y1="17" x2="8" y2="17"/>
					</svg>
					<span class="nav-label">{m.nav_api()}</span>
				</a>
				<a href="/settings" class="settings-link" title="{m.nav_settings()}">
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<circle cx="12" cy="12" r="3"/>
						<path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
					</svg>
				</a>
				{#if $user}
					<div class="user-info">
						<IconUser size={16} color="var(--text-muted)" />
						<span>{$user.username || shortWallet($user.wallet_address)}</span>
					</div>
				{/if}
				<button class="logout-btn" on:click={handleLogout} title="{m.nav_sign_out()}">
					<IconLogout size={16} />
				</button>
			</div>
		</div>
	</header>
	<main class="app-main">
		<div class="container">
			<slot />
		</div>
	</main>
</div>
{/if}
{/key}

<style>
	.app-layout {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	.topbar {
		position: sticky;
		top: 0;
		z-index: 50;
		background: rgba(9, 9, 11, 0.9);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border-subtle);
	}

	.topbar-inner {
		max-width: var(--max-width);
		margin: 0 auto;
		padding: 0 24px;
		height: 56px;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.topbar-brand {
		display: flex;
		align-items: center;
		gap: 8px;
		text-decoration: none;
		color: var(--text-primary);
	}

	.topbar-name {
		font-size: 1rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}

	.topbar-right {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	.user-info {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.8rem;
		color: var(--text-secondary);
		font-weight: 500;
	}

	.logout-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 34px;
		height: 34px;
		border-radius: var(--radius-sm);
		background: transparent;
		border: 1px solid var(--border-subtle);
		color: var(--text-muted);
		cursor: pointer;
		transition: all var(--transition-base);
	}

	.logout-btn:hover {
		background: var(--danger-muted);
		border-color: rgba(239, 68, 68, 0.3);
		color: var(--danger);
	}

	.app-main {
		flex: 1;
		padding-top: 24px;
		padding-bottom: 40px;
	}

	.settings-link, .nav-link {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 5px;
		height: 34px;
		padding: 0 10px;
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		text-decoration: none;
		transition: all var(--transition-base);
		font-size: 0.78rem;
		font-weight: 600;
	}

	.settings-link {
		width: 34px;
		padding: 0;
	}

	.nav-label {
		letter-spacing: 0.03em;
	}

	.settings-link:hover, .nav-link:hover {
		background: rgba(255, 255, 255, 0.06);
		color: var(--text-primary);
	}
</style>
