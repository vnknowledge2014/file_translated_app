<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { languages, domains, sourceLang, targetLang, currentDomain } from '$lib/stores/config';
    import IconSwap from '$lib/components/icons/IconSwap.svelte';
    import IconSearch from '$lib/components/icons/IconSearch.svelte';
    
    function swapLangs() {
        if ($sourceLang === 'auto') return;
        const temp = $sourceLang;
        sourceLang.set($targetLang);
        targetLang.set(temp);
    }
</script>

<div class="lang-bar">
    <div class="lang-select-group">
        <span class="lang-select-label">{m.lang_source()}</span>
        <select class="lang-select" bind:value={$sourceLang}>
            <option value="auto">
                Auto Detect
            </option>
            {#each $languages as l}
                <option value={l.code}>{l.native_name} ({l.name})</option>
            {/each}
        </select>
    </div>

    <button class="lang-swap-btn" on:click={swapLangs} title={m.lang_swap_title()} disabled={$sourceLang === 'auto'}>
        <IconSwap size={18} />
    </button>

    <div class="lang-select-group">
        <span class="lang-select-label">{m.lang_target()}</span>
        <select class="lang-select" bind:value={$targetLang}>
            {#each $languages as l}
                <option value={l.code}>{l.native_name} ({l.name})</option>
            {/each}
        </select>
    </div>

    <div class="lang-select-group">
        <span class="lang-select-label">{m.lang_domain()}</span>
        <select class="domain-select-inline" bind:value={$currentDomain}>
            {#each $domains as d}
                <option value={d.code}>{d.name}</option>
            {/each}
        </select>
    </div>
</div>

<style>
    .lang-bar {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        flex-wrap: wrap;
    }

    .lang-select-group {
        display: flex;
        flex-direction: column;
        gap: 4px;
        align-items: center;
    }

    .lang-select-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: var(--text-muted);
        font-weight: 600;
    }

    .lang-select, .domain-select-inline {
        padding: 10px 16px;
        border-radius: var(--radius-sm);
        background: var(--bg-secondary);
        color: var(--text-primary);
        border: 1px solid var(--border);
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        font-family: inherit;
        min-width: 180px;
        transition: all var(--transition-base);
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2371717a' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 12px center;
        padding-right: 32px;
    }

    .lang-select:hover, .domain-select-inline:hover {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px var(--accent-muted);
    }

    .lang-select:focus, .domain-select-inline:focus {
        outline: none;
        border-color: var(--accent);
        box-shadow: 0 0 0 3px var(--accent-muted);
    }

    .lang-swap-btn {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        color: var(--text-secondary);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all var(--transition-slow);
        margin-top: 16px;
    }

    .lang-swap-btn:hover:not(:disabled) {
        background: var(--accent-muted);
        border-color: var(--accent);
        color: var(--accent);
        transform: rotate(180deg);
    }

    .lang-swap-btn:disabled {
        opacity: 0.3;
        cursor: not-allowed;
    }

    @media (max-width: 768px) {
        .lang-bar {
            flex-direction: column;
            gap: 8px;
        }
        .lang-swap-btn {
            margin-top: 0;
            transform: rotate(90deg);
        }
        .lang-select, .domain-select-inline {
            min-width: 100%;
        }
    }
</style>
