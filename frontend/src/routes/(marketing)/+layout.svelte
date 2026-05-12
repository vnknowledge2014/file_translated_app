<script lang="ts">
	import * as m from '$lib/paraglide/messages';
	import IconLogo from '$lib/components/icons/IconLogo.svelte';
	import IconChevronRight from '$lib/components/icons/IconChevronRight.svelte';
	import { isAuthenticated } from '$lib/stores/auth';
</script>

<div class="marketing-layout">
	<nav class="navbar">
		<div class="navbar-inner">
			<a href="/" class="nav-brand">
				<IconLogo size={28} color="var(--accent)" />
				<span class="brand-name">InfiTrans</span>
			</a>
			<div class="nav-links">
				<a href="/#features" class="nav-link">{m.nav_features()}</a>
				<a href="/pricing" class="nav-link">{m.nav_pricing()}</a>
				<a href="/api-docs" class="nav-link">{m.nav_api_docs()}</a>
			</div>
			{#if $isAuthenticated}
				<a href="/translate" class="nav-cta">
					Dashboard
					<IconChevronRight size={16} />
				</a>
			{:else}
				<a href="/login" class="nav-cta">
					{m.nav_start_translating()}
					<IconChevronRight size={16} />
				</a>
			{/if}
		</div>
	</nav>

	<main>
		<slot />
	</main>

	<footer class="footer">
		<div class="footer-inner">
			<div class="footer-brand">
				<IconLogo size={22} color="var(--text-muted)" />
				<span>InfiTrans</span>
			</div>
			<p class="footer-copy">{m.footer_built_by()} <strong>Infinite Agent Lab</strong> &middot; &copy; 2026</p>
			<div class="footer-links">
				<a href="/pricing">{m.nav_pricing()}</a>
				<a href="/api-docs">{m.nav_api_docs()}</a>
				{#if $isAuthenticated}
					<a href="/translate">Dashboard</a>
				{:else}
					<a href="/login">{m.nav_sign_in()}</a>
				{/if}
			</div>
		</div>
	</footer>
</div>

<style>
	:global(html) {
		scroll-padding-top: 80px;
	}

	.marketing-layout {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	/* ── Navbar ── */
	.navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 100;
		background: rgba(9, 9, 11, 0.85);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border-subtle);
	}

	.navbar-inner {
		max-width: var(--max-width);
		margin: 0 auto;
		padding: 0 24px;
		height: 64px;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 10px;
		text-decoration: none;
		color: var(--text-primary);
	}

	.brand-name {
		font-size: 1.2rem;
		font-weight: 700;
		letter-spacing: -0.02em;
	}

	.nav-links {
		display: flex;
		gap: 32px;
	}

	.nav-link {
		color: var(--text-secondary);
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 500;
		transition: color var(--transition-base);
	}

	.nav-link:hover {
		color: var(--text-primary);
	}

	.nav-cta {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 8px 20px;
		background: var(--accent);
		color: #fff;
		border-radius: var(--radius-sm);
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 600;
		transition: all var(--transition-base);
	}

	.nav-cta:hover {
		background: var(--accent-hover);
		transform: translateY(-1px);
	}

	/* ── Footer ── */
	.footer {
		margin-top: auto;
		border-top: 1px solid var(--border-subtle);
		padding: 40px 0;
	}

	.footer-inner {
		max-width: var(--max-width);
		margin: 0 auto;
		padding: 0 24px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 16px;
	}

	.footer-brand {
		display: flex;
		align-items: center;
		gap: 8px;
		color: var(--text-muted);
		font-weight: 600;
		font-size: 0.9rem;
	}

	.footer-copy {
		font-size: 0.8rem;
		color: var(--text-muted);
	}

	.footer-copy strong {
		color: var(--text-secondary);
	}

	.footer-links {
		display: flex;
		gap: 24px;
	}

	.footer-links a {
		color: var(--text-muted);
		text-decoration: none;
		font-size: 0.8rem;
		transition: color var(--transition-base);
	}

	.footer-links a:hover {
		color: var(--accent);
	}

	main {
		padding-top: 64px;
		flex: 1;
	}

	@media (max-width: 768px) {
		.nav-links { display: none; }
		.footer-inner { flex-direction: column; text-align: center; }
	}
</style>
