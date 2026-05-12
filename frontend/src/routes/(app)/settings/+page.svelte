<script lang="ts">
    import { onMount } from 'svelte';
    import { listApiKeys, createApiKey, deleteApiKey, fetchMe, updateUsername, getBillingStatus, createPayment, confirmPayment } from '$lib/api';
    import type { ApiKeyInfo, CreateKeyResponse } from '$lib/api';
    import { shortWallet } from '$lib/stores/auth';
    import { sendUsdcPayment } from '$lib/solana-pay';
    import * as m from '$lib/paraglide/messages';

    // API Keys state
    let keys: ApiKeyInfo[] = [];
    let loading = true;
    let error = '';
    let showCreateModal = false;
    let newKeyName = '';
    let newKeyScope = 'translate';
    let creating = false;
    let createdKey: CreateKeyResponse | null = null;
    let copied = false;

    // Account state
    let userInfo: any = null;
    let billing: any = null;

    // Billing
    let upgrading = '';
    let upgradeStep = '';  // '', 'creating', 'signing', 'confirming', 'done'
    let billingError = '';
    let billingSuccess = '';

    // Username editing
    let editingUsername = false;
    let editUsername = '';
    let savingUsername = false;
    let usernameError = '';

    async function handleSaveUsername() {
        if (!editUsername.trim()) return;
        savingUsername = true;
        usernameError = '';
        try {
            await updateUsername(editUsername.trim());
            userInfo = { ...userInfo, username: editUsername.trim() };
            editingUsername = false;
        } catch (e: any) {
            usernameError = e.message;
        } finally {
            savingUsername = false;
        }
    }

    const plans = [
        { id: 'free',       name: 'Free',       price: '$0',  period: 'forever',  pages: '100',       keys: '1',         active: false },
        { id: 'pro',        name: 'Pro',        price: '$29', period: '/month',   pages: '5,000',     keys: '10',        active: false },
        { id: 'enterprise', name: 'Enterprise', price: '$99', period: '/month',   pages: 'Unlimited', keys: 'Unlimited', active: false },
    ];

    onMount(async () => {
        await Promise.all([loadKeys(), loadAccountInfo()]);
    });

    async function loadAccountInfo() {
        try {
            [userInfo, billing] = await Promise.all([fetchMe(), getBillingStatus()]);
        } catch (e) {}
    }

    async function loadKeys() {
        loading = true; error = '';
        try { keys = await listApiKeys(); }
        catch (e: any) { error = e.message; }
        finally { loading = false; }
    }

    async function handleCreate() {
        if (!newKeyName.trim()) return;
        creating = true;
        try { createdKey = await createApiKey(newKeyName.trim(), newKeyScope); await loadKeys(); newKeyName = ''; }
        catch (e: any) { error = e.message; }
        finally { creating = false; }
    }

    async function handleRevoke(id: string, name: string) {
        if (!confirm(`Revoke key "${name}"?`)) return;
        try { await deleteApiKey(id); await loadKeys(); }
        catch (e: any) { error = e.message; }
    }

    async function handleUpgrade(planId: string) {
        if (planId === 'free' || planId === currentPlan) return;
        upgrading = planId;
        upgradeStep = 'creating';
        billingError = '';
        billingSuccess = '';

        try {
            // Step 1: Create payment reference on backend
            const payment = await createPayment(planId);
            upgradeStep = 'signing';

            // Step 2: Build & sign SPL transfer via Phantom
            const txSignature = await sendUsdcPayment(
                payment.recipient,
                payment.amount_usdc,
                payment.token_mint,
                payment.rpc_url,
            );
            upgradeStep = 'confirming';

            // Step 3: Backend verifies TX on-chain and upgrades plan
            const result = await confirmPayment(payment.reference, txSignature);
            upgradeStep = 'done';
            billingSuccess = `🎉 Upgraded to ${result.plan.toUpperCase()}! TX: ${txSignature.slice(0, 12)}...`;

            // Refresh account info
            await loadAccountInfo();
        } catch (e: any) {
            if (e.code === 4001 || e.message?.includes('rejected')) {
                billingError = 'Transaction cancelled. You were not charged.';
            } else {
                billingError = e.message || 'Payment failed';
            }
        } finally {
            upgrading = '';
            upgradeStep = '';
        }
    }

    function copyToClipboard(text: string) {
        navigator.clipboard.writeText(text);
        copied = true; setTimeout(() => copied = false, 2000);
    }
    function closeCreatedModal() { createdKey = null; showCreateModal = false; }
    function scopeColor(s: string) { return s === 'admin' ? 'var(--danger)' : s === 'translate' ? 'var(--accent)' : 'var(--text-muted)'; }
    function timeAgo(d: string | null) {
        if (!d) return m.settings_never();
        const ms = Date.now() - new Date(d).getTime();
        const m_val = Math.floor(ms / 60000);
        if (m_val < 60) return `${m_val}m ago`;
        const h = Math.floor(m_val / 60);
        return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`;
    }

    $: currentPlan = billing?.plan || userInfo?.plan || 'free';
    $: usagePercent = billing ? Math.min(100, Math.round((billing.pages_used / (billing.pages_limit || 100)) * 100)) : 0;
</script>

<svelte:head><title>{m.settings_title()} — InfiTrans</title></svelte:head>

<div class="settings-page">
    <div class="page-header">
        <h1>{m.settings_title()}</h1>
        <p class="subtitle">{m.settings_subtitle()}</p>
    </div>

    <!-- Account Overview -->
    {#if userInfo}
    <section class="section account-section">
        <h2>{m.settings_account()}</h2>
        <div class="account-grid">
            <div class="account-item">
                <span class="label">{m.settings_username()}</span>
                <div class="wallet-row">
                    {#if editingUsername}
                        <input
                            type="text"
                            class="username-input"
                            bind:value={editUsername}
                            placeholder="Enter username"
                            maxlength="32"
                            on:keydown={(e) => e.key === 'Enter' && handleSaveUsername()}
                        />
                        <button class="btn-copy-sm" on:click={handleSaveUsername} disabled={savingUsername}>
                            {savingUsername ? '...' : 'Save'}
                        </button>
                        <button class="btn-copy-sm" on:click={() => { editingUsername = false; usernameError = ''; }}>
                            Cancel
                        </button>
                    {:else}
                        <code class="wallet-addr">{userInfo.username}</code>
                        <button class="btn-copy-sm" on:click={() => { editingUsername = true; editUsername = userInfo.username; }}>
                            Edit
                        </button>
                    {/if}
                </div>
                {#if usernameError}<div class="field-error">{usernameError}</div>{/if}
            </div>
            <div class="account-item full-width">
                <span class="label">Wallet Address</span>
                <div class="wallet-row">
                    <code class="wallet-addr">{userInfo.wallet_address || m.settings_not_connected()}</code>
                    {#if userInfo.wallet_address}
                        <button class="btn-copy-sm" on:click={() => copyToClipboard(userInfo.wallet_address)}>
                            {copied ? m.settings_copied() : m.settings_copy()}
                        </button>
                    {/if}
                </div>
            </div>
        </div>
    </section>
    {/if}

    <!-- Billing & Plan -->
    <section class="section">
        <div class="billing-header">
            <h2>{m.settings_billing_title()}</h2>
            {#if billing?.solana_network === 'devnet'}
                <span class="network-badge devnet">⚠ DEVNET</span>
            {:else}
                <span class="network-badge mainnet">MAINNET</span>
            {/if}
        </div>
        <p class="section-desc">
            {m.settings_billing_desc()}
            {#if billing?.solana_network === 'devnet'}
                <strong style="color:#f59e0b">{m.settings_billing_testmode()}</strong>
            {/if}
        </p>

        {#if billingError}<div class="error-banner">{billingError}</div>{/if}
        {#if billingSuccess}<div class="success-banner">{billingSuccess}</div>{/if}

        <!-- Current Usage -->
        <div class="usage-card">
            <div class="usage-header">
                <span class="current-plan-label">{m.settings_current_plan()}</span>
                <span class="current-plan-name" class:plan-free={currentPlan === 'free'} class:plan-pro={currentPlan === 'pro'} class:plan-ent={currentPlan === 'enterprise'}>
                    {currentPlan.toUpperCase()}
                </span>
            </div>
            <div class="usage-bar-wrap">
                <div class="usage-info">
                    <span>{billing?.pages_used ?? 0} of {billing?.pages_limit === null ? '∞' : (billing?.pages_limit ?? 100)} pages used</span>
                    <span class="usage-pct">{billing?.pages_limit === null ? '' : `${usagePercent}%`}</span>
                </div>
                {#if billing?.pages_limit !== null}
                <div class="usage-bar">
                    <div class="usage-fill" style="width:{usagePercent}%" class:danger={usagePercent > 90} class:warning={usagePercent > 70 && usagePercent <= 90}></div>
                </div>
                {/if}
            </div>
            {#if billing?.plan_expires_at}
                <div class="plan-expiry">{m.settings_renews()}: {new Date(billing.plan_expires_at).toLocaleDateString()}</div>
            {/if}
        </div>

        <!-- Plan Cards -->
        <div class="plans-grid">
            {#each plans as plan}
                <div class="plan-card" class:active={currentPlan === plan.id} class:highlight={plan.id === 'pro'}>
                    <div class="plan-top">
                        <h3>{plan.name}</h3>
                        <div class="plan-price">{plan.price}<span class="plan-period">{plan.period}</span></div>
                    </div>
                    <ul class="plan-features">
                        <li>📄 {plan.pages} pages/mo</li>
                        <li>🔑 {plan.keys} API keys</li>
                    </ul>
                    {#if currentPlan === plan.id}
                        <button class="btn-plan current" disabled>{m.settings_current_plan_btn()}</button>
                    {:else if plan.id === 'free'}
                        <button class="btn-plan" disabled>{m.settings_free_tier()}</button>
                    {:else}
                        <button class="btn-plan upgrade" on:click={() => handleUpgrade(plan.id)} disabled={!!upgrading}>
                            {#if upgrading === plan.id}
                                {#if upgradeStep === 'creating'}{m.settings_preparing()}
                                {:else if upgradeStep === 'signing'}{m.settings_approve_phantom()}
                                {:else if upgradeStep === 'confirming'}{m.settings_verifying_chain()}
                                {:else}{m.settings_processing()}{/if}
                            {:else}
                                {m.settings_upgrade_to()} {plan.name}
                            {/if}
                        </button>
                    {/if}
                </div>
            {/each}
        </div>
    </section>

    <!-- API Keys -->
    <section class="section">
        <div class="section-header">
            <div><h2>{m.settings_api_keys_title()}</h2><p class="section-desc">{m.settings_api_keys_desc()}</p></div>
            <button class="btn-primary" on:click={() => { showCreateModal = true; createdKey = null; }}>{m.settings_create_key()}</button>
        </div>
        {#if error}<div class="error-banner">{error}</div>{/if}
        {#if loading}<div class="loading">{m.settings_loading()}</div>
        {:else if keys.length === 0}<div class="empty-state"><p>{m.settings_no_keys()}</p></div>
        {:else}
            <div class="keys-table">
                <div class="table-header">
                    <span class="col-name">{m.settings_col_name()}</span><span class="col-key">{m.settings_col_key()}</span>
                    <span class="col-scope">{m.settings_col_scope()}</span><span class="col-usage">{m.settings_col_requests()}</span>
                    <span class="col-used">{m.settings_col_last_used()}</span><span class="col-action"></span>
                </div>
                {#each keys as key}
                    <div class="table-row" class:inactive={!key.is_active}>
                        <span class="col-name">{key.name}</span>
                        <span class="col-key"><code>{key.key_prefix}...</code></span>
                        <span class="col-scope"><span class="scope-badge" style="color:{scopeColor(key.scope)}">{key.scope}</span></span>
                        <span class="col-usage">{key.requests_count.toLocaleString()}{#if key.requests_limit}<span class="limit">/ {key.requests_limit.toLocaleString()}</span>{/if}</span>
                        <span class="col-used">{timeAgo(key.last_used)}</span>
                        <span class="col-action">{#if key.is_active}<button class="btn-revoke" on:click={() => handleRevoke(key.id, key.name)}>{m.settings_revoke()}</button>{:else}<span class="revoked-badge">{m.settings_revoked()}</span>{/if}</span>
                    </div>
                {/each}
            </div>
        {/if}
    </section>
</div>

{#if showCreateModal}
<div class="modal-overlay" on:click|self={closeCreatedModal}><div class="modal">
    {#if createdKey}
        <h3>{m.settings_key_created()}</h3>
        <div class="warning-banner">{m.settings_copy_warning()}</div>
        <div class="key-display"><code>{createdKey.key}</code>
            <button class="btn-copy" on:click={() => copyToClipboard(createdKey?.key || '')}>{copied ? m.settings_copied() : m.settings_copy()}</button></div>
        <button class="btn-primary full" on:click={closeCreatedModal}>{m.settings_done()}</button>
    {:else}
        <h3>{m.settings_create_key_title()}</h3>
        <div class="form-group"><label for="key-name">{m.settings_key_name()}</label>
            <input id="key-name" type="text" bind:value={newKeyName} placeholder="{m.settings_key_placeholder()}" maxlength="64" /></div>
        <div class="form-group"><label for="key-scope">{m.settings_key_scope()}</label>
            <select id="key-scope" bind:value={newKeyScope}>
                <option value="read">{m.settings_scope_read()}</option>
                <option value="translate">{m.settings_scope_translate()}</option>
                <option value="admin">{m.settings_scope_admin()}</option>
            </select></div>
        <div class="modal-actions">
            <button class="btn-ghost" on:click={closeCreatedModal}>{m.settings_cancel()}</button>
            <button class="btn-primary" on:click={handleCreate} disabled={creating || !newKeyName.trim()}>{creating ? m.settings_creating() : m.settings_create_key()}</button>
        </div>
    {/if}
</div></div>
{/if}

<style>
    .settings-page { max-width: 900px; margin: 0 auto; padding: 0 24px; }
    .page-header { margin-bottom: 24px; }
    .page-header h1 { font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin: 0 0 4px; }
    .subtitle { color: var(--text-muted); font-size: 0.9rem; margin: 0; }

    .billing-header { display: flex; align-items: center; gap: 10px; }
    .network-badge { font-size: 0.68rem; font-weight: 800; letter-spacing: 0.06em; padding: 3px 8px; border-radius: 4px; }
    .network-badge.devnet { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
    .network-badge.mainnet { background: rgba(34,197,94,0.15); color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }

    .section { background: var(--surface-2); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 24px; margin-bottom: 24px; }
    .section h2 { font-size: 1.15rem; font-weight: 600; color: var(--text-primary); margin: 0 0 8px; }
    .section-desc { color: var(--text-muted); font-size: 0.85rem; margin: 0 0 16px; }
    .section-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }

    /* Account section */
    .account-grid { display: grid; gap: 16px; margin-top: 16px; }
    .account-item { display: flex; flex-direction: column; gap: 4px; }
    .account-item .label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
    .full-width { grid-column: 1 / -1; }
    .wallet-row { display: flex; gap: 8px; align-items: center; }
    .wallet-addr { font-size: 0.82rem; background: rgba(255,255,255,0.05); padding: 6px 10px; border-radius: 6px; color: var(--accent); word-break: break-all; flex: 1; }
    .btn-copy-sm { padding: 4px 10px; background: transparent; border: 1px solid var(--border-subtle); color: var(--text-muted); border-radius: var(--radius-sm); font-size: 0.75rem; cursor: pointer; white-space: nowrap; }
    .btn-copy-sm:hover { color: var(--accent); border-color: var(--accent); }

    /* Usage card */
    .usage-card { padding: 20px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; margin-bottom: 20px; }
    .usage-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
    .current-plan-label { font-size: 0.82rem; color: var(--text-muted); font-weight: 500; }
    .current-plan-name { font-size: 0.88rem; font-weight: 800; letter-spacing: 0.06em; }
    .plan-free { color: var(--text-muted); }
    .plan-pro { color: var(--accent); }
    .plan-ent { color: #a78bfa; }
    .usage-info { display: flex; justify-content: space-between; font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 8px; }
    .usage-pct { font-weight: 600; color: var(--text-muted); }
    .usage-bar { height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
    .usage-fill { height: 100%; background: var(--accent); border-radius: 3px; transition: width 0.5s ease; }
    .usage-fill.warning { background: #f59e0b; }
    .usage-fill.danger { background: var(--danger); }
    .plan-expiry { margin-top: 10px; font-size: 0.78rem; color: var(--text-muted); }

    /* Plan cards */
    .plans-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .plan-card { padding: 18px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; display: flex; flex-direction: column; transition: border-color 0.2s; }
    .plan-card.active { border-color: var(--accent); background: rgba(20,184,166,0.04); }
    .plan-card.highlight { border-color: rgba(20,184,166,0.3); }
    .plan-top { margin-bottom: 12px; }
    .plan-card h3 { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin: 0 0 4px; }
    .plan-price { font-size: 1.3rem; font-weight: 800; color: var(--text-primary); }
    .plan-period { font-size: 0.75rem; font-weight: 400; color: var(--text-muted); margin-left: 2px; }
    .plan-features { list-style: none; padding: 0; margin: 0 0 14px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
    .plan-features li { font-size: 0.8rem; color: var(--text-secondary); }
    .btn-plan { width: 100%; padding: 8px; border-radius: var(--radius-sm); font-size: 0.82rem; font-weight: 600; cursor: pointer; border: 1px solid var(--border-subtle); background: transparent; color: var(--text-muted); transition: all 0.15s; }
    .btn-plan.current { background: rgba(20,184,166,0.1); border-color: var(--accent); color: var(--accent); cursor: default; }
    .btn-plan.upgrade { background: var(--accent); color: #fff; border-color: var(--accent); }
    .btn-plan.upgrade:hover:not(:disabled) { opacity: 0.9; }
    .btn-plan:disabled { opacity: 0.6; cursor: not-allowed; }

    /* Buttons */
    .btn-primary { padding: 8px 16px; background: var(--accent); color: #fff; border: none; border-radius: var(--radius-sm); font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; white-space: nowrap; }
    .btn-primary:hover { opacity: 0.9; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary.full { width: 100%; margin-top: 12px; }
    .btn-ghost { padding: 8px 16px; background: transparent; color: var(--text-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 0.85rem; cursor: pointer; }
    .btn-copy { padding: 8px 14px; background: var(--accent); color: #fff; border: none; border-radius: var(--radius-sm); font-size: 0.82rem; font-weight: 600; cursor: pointer; white-space: nowrap; }
    .btn-revoke { padding: 4px 10px; background: transparent; color: var(--danger); border: 1px solid rgba(239,68,68,0.3); border-radius: var(--radius-sm); font-size: 0.78rem; cursor: pointer; }
    .btn-revoke:hover { background: rgba(239,68,68,0.1); }

    .error-banner { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: var(--danger); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 0.85rem; margin-bottom: 16px; }
    .success-banner { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); color: #22c55e; padding: 10px 14px; border-radius: var(--radius-sm); font-size: 0.85rem; margin-bottom: 16px; }
    .warning-banner { background: rgba(250,204,21,0.1); border: 1px solid rgba(250,204,21,0.3); color: #facc15; padding: 10px 14px; border-radius: var(--radius-sm); font-size: 0.85rem; margin-bottom: 16px; }
    .loading, .empty-state { text-align: center; padding: 32px; color: var(--text-muted); }

    .form-group { margin-bottom: 14px; }
    .form-group label { display: block; font-size: 0.82rem; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
    .form-group input, .form-group select { width: 100%; padding: 10px 12px; background: var(--surface-1); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); color: var(--text-primary); font-size: 0.88rem; }
    .form-group input:focus, .form-group select:focus { outline: none; border-color: var(--accent); }

    .keys-table { display: grid; }
    .table-header, .table-row { display: grid; grid-template-columns: 1.5fr 1.2fr 0.8fr 1fr 0.8fr 0.7fr; align-items: center; padding: 10px 0; gap: 8px; }
    .table-header { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border-subtle); }
    .table-row { font-size: 0.85rem; color: var(--text-secondary); border-bottom: 1px solid rgba(255,255,255,0.04); }
    .table-row.inactive { opacity: 0.4; }
    .table-row code { font-size: 0.78rem; background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; }
    .scope-badge { font-size: 0.78rem; font-weight: 600; text-transform: uppercase; }
    .limit { color: var(--text-muted); font-size: 0.78rem; }
    .revoked-badge { font-size: 0.78rem; color: var(--text-muted); font-style: italic; }

    .modal-overlay { position: fixed; inset: 0; z-index: 100; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; }
    .modal { background: var(--surface-2); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 28px; width: 90%; max-width: 480px; }
    .modal h3 { font-size: 1.15rem; font-weight: 600; color: var(--text-primary); margin: 0 0 16px; }
    .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; }
    .key-display { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; }
    .key-display code { flex: 1; padding: 10px 12px; background: var(--surface-1); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 0.82rem; word-break: break-all; color: var(--accent); }

    @media (max-width: 768px) {
        .plans-grid { grid-template-columns: 1fr; }
        .table-header, .table-row { grid-template-columns: 1fr 1fr; }
        .col-usage, .col-used, .col-scope { display: none; }
    }

    .username-input {
        padding: 6px 10px;
        background: var(--surface-1);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-sm);
        color: var(--text-primary);
        font-size: 0.88rem;
        font-family: inherit;
        min-width: 160px;
    }
    .username-input:focus { outline: none; border-color: var(--accent); }
    .field-error { font-size: 0.78rem; color: var(--danger); margin-top: 6px; }
</style>
