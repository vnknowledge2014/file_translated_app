<script lang="ts">
	import { walletChallenge, walletVerify } from '$lib/api';
	import { isAuthenticated, user } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import * as m from '$lib/paraglide/messages';
	import IconLogo from '$lib/components/icons/IconLogo.svelte';
	import IconSpinner from '$lib/components/icons/IconSpinner.svelte';

	let error = '';
	let loading = false;
	let status = '';

	async function handlePhantom() {
		error = ''; loading = true; status = m.login_status_detecting();
		try {
			const phantom = (window as any).phantom?.solana;
			if (!phantom?.isPhantom) {
				window.open('https://phantom.app/', '_blank');
				throw new Error(m.login_phantom_not_found());
			}

			// Step 1: Connect
			status = m.login_status_connecting();
			const resp = await phantom.connect();
			const pubkey = resp.publicKey.toString();

			// Step 2: Get challenge nonce
			status = m.login_status_challenge();
			const challenge = await walletChallenge(pubkey);

			// Step 3: Sign message
			status = m.login_status_signing();
			const encoded = new TextEncoder().encode(challenge.message);
			const signed = await phantom.signMessage(encoded, 'utf8');

			// Step 4: Convert signature to hex
			const sigHex = Array.from(signed.signature as Uint8Array)
				.map((b: number) => b.toString(16).padStart(2, '0')).join('');

			// Step 5: Verify on backend
			status = m.login_status_verifying();
			const data = await walletVerify(pubkey, sigHex, challenge.nonce);
			isAuthenticated.set(true);
			user.set({ username: data.user?.username || pubkey.slice(0, 8), wallet_address: pubkey });
			goto('/translate');
		} catch (e: any) {
			if (e.code === 4001) {
				error = m.login_rejected();
			} else {
				error = e.message || m.login_failed();
			}
		} finally {
			loading = false;
			status = '';
		}
	}
</script>

<svelte:head>
	<title>Sign In | InfiTrans</title>
</svelte:head>

<div class="auth-page">
	<div class="bg-gradient"></div>
	<div class="auth-container">
		<div class="auth-header">
			<div class="auth-logo">
				<IconLogo size={36} color="var(--accent)" />
			</div>
			<h1>{m.login_title()}</h1>
			<p class="subtitle">{m.login_subtitle()}</p>
		</div>

		{#if error}
			<div class="message error">{error}</div>
		{/if}

		<button class="phantom-btn" on:click={handlePhantom} disabled={loading}>
			{#if loading}
				<IconSpinner size={20} color="#fff" />
				<span>{status}</span>
			{:else}
				<svg width="24" height="24" viewBox="0 0 128 128" fill="none">
					<defs><linearGradient id="pg" x1="0" y1="0" x2="128" y2="128"><stop stop-color="#534bb1"/><stop offset="1" stop-color="#551bf9"/></linearGradient></defs>
					<rect width="128" height="128" rx="26" fill="url(#pg)"/>
					<path d="M110.584 64.914H99.142c0-23.456-19.015-42.471-42.47-42.471C34.82 22.443 16.59 39.863 14.46 61.87h-.008c-.18 1.87-.011 16.442 13.97 28.027 8.403 6.96 18.39 8.36 22.472 8.63a5.483 5.483 0 005.807-5.148 5.482 5.482 0 00-5.148-5.808c-2.882-.19-9.546-1.177-15.056-5.74-8.418-6.97-8.812-16.143-8.71-19.737 1.66-15.39 14.815-27.237 30.885-27.237 17.4 0 31.504 14.103 31.504 31.504v5.967c0 5.452 4.42 9.871 9.871 9.871h10.537c5.452 0 9.871-4.42 9.871-9.871v-5.967a11.534 11.534 0 00-9.871-11.447z" fill="white"/>
					<circle cx="80" cy="60" r="5" fill="white"/><circle cx="96" cy="60" r="5" fill="white"/>
				</svg>
				<span>{m.login_connect_phantom()}</span>
			{/if}
		</button>

		<div class="info-section">
			<h3>{m.login_how_it_works()}</h3>
			<ol>
				<li><span class="step-num">1</span> {m.login_step1()}</li>
				<li><span class="step-num">2</span> {m.login_step2()}</li>
				<li><span class="step-num">3</span> {m.login_step3()}</li>
				<li><span class="step-num">4</span> {m.login_step4()}</li>
			</ol>
		</div>

		<div class="no-wallet">
			<p>{m.login_no_wallet()}
				<a href="https://phantom.app/" target="_blank" rel="noopener">{m.login_download()}</a>
			</p>
		</div>

		<div class="back-home">
			<a href="/">{m.login_back_home()}</a>
		</div>
	</div>
</div>

<style>
	.auth-page {
		position: relative;
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 24px;
		overflow: hidden;
	}

	.bg-gradient {
		position: fixed;
		inset: 0;
		background:
			radial-gradient(ellipse 50% 50% at 20% 20%, rgba(20, 184, 166, 0.06) 0%, transparent 100%),
			radial-gradient(ellipse 40% 60% at 80% 80%, rgba(85, 27, 249, 0.04) 0%, transparent 100%),
			var(--bg-primary);
		z-index: 0;
	}

	.auth-container {
		position: relative;
		z-index: 1;
		width: 100%;
		max-width: 440px;
		background: var(--bg-secondary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
		padding: 48px 36px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
	}

	.auth-header {
		text-align: center;
		margin-bottom: 32px;
	}

	.auth-logo {
		display: inline-flex;
		margin-bottom: 16px;
	}

	h1 {
		font-size: 1.6rem;
		font-weight: 700;
		letter-spacing: -0.03em;
		color: var(--text-primary);
		margin: 0 0 8px;
	}

	.subtitle {
		font-size: 0.9rem;
		color: var(--text-muted);
		margin: 0;
	}

	.message.error {
		padding: 12px;
		border-radius: var(--radius-sm);
		font-size: 0.85rem;
		text-align: center;
		margin-bottom: 20px;
		color: var(--danger);
		background: var(--danger-muted);
		border: 1px solid rgba(239, 68, 68, 0.3);
	}

	.phantom-btn {
		width: 100%;
		padding: 16px;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12px;
		background: linear-gradient(135deg, #534bb1, #551bf9);
		color: #fff;
		border: none;
		border-radius: var(--radius);
		font-weight: 600;
		font-size: 1rem;
		font-family: inherit;
		cursor: pointer;
		transition: all 0.25s ease;
	}

	.phantom-btn:hover:not(:disabled) {
		filter: brightness(1.1);
		transform: translateY(-2px);
		box-shadow: 0 6px 24px rgba(85, 27, 249, 0.35);
	}

	.phantom-btn:active:not(:disabled) {
		transform: translateY(0);
	}

	.phantom-btn:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.info-section {
		margin-top: 32px;
		padding: 20px;
		background: rgba(20, 184, 166, 0.04);
		border: 1px solid rgba(20, 184, 166, 0.1);
		border-radius: var(--radius);
	}

	.info-section h3 {
		font-size: 0.8rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--accent);
		margin: 0 0 14px;
	}

	.info-section ol {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.info-section li {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 0.85rem;
		color: var(--text-secondary);
	}

	.step-num {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: var(--border-subtle);
		color: var(--text-muted);
		font-size: 0.72rem;
		font-weight: 700;
		flex-shrink: 0;
	}

	.no-wallet {
		text-align: center;
		margin-top: 24px;
	}

	.no-wallet p {
		font-size: 0.82rem;
		color: var(--text-muted);
		margin: 0;
	}

	.no-wallet a {
		color: var(--accent);
		text-decoration: none;
		font-weight: 500;
	}

	.no-wallet a:hover {
		text-decoration: underline;
	}

	.back-home {
		text-align: center;
		margin-top: 20px;
	}

	.back-home a {
		font-size: 0.82rem;
		color: var(--text-muted);
		text-decoration: none;
	}

	.back-home a:hover {
		color: var(--accent);
	}
</style>
