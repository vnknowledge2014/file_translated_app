<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { languages, domains, sourceLang, targetLang, currentDomain } from '$lib/stores/config';
    
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
            <option value="auto">🔍 {m.lang_auto_detect()}</option>
            {#each $languages as l}
                <option value={l.code}>{l.flag} {l.native_name} ({l.name})</option>
            {/each}
        </select>
    </div>

    <button class="lang-swap-btn" on:click={swapLangs} title={m.lang_swap_title()}>⇄</button>

    <div class="lang-select-group">
        <span class="lang-select-label">{m.lang_target()}</span>
        <select class="lang-select" bind:value={$targetLang}>
            {#each $languages as l}
                <option value={l.code}>{l.flag} {l.native_name} ({l.name})</option>
            {/each}
        </select>
    </div>

    <div class="lang-select-group">
        <span class="lang-select-label">{m.lang_domain()}</span>
        <select class="domain-select-inline" bind:value={$currentDomain}>
            {#each $domains as d}
                <option value={d.code}>{d.icon} {d.name}</option>
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
        margin-bottom: 32px;
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
        border-radius: 12px;
        background: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid var(--border-glass);
        font-size: 0.95rem;
        font-weight: 500;
        cursor: pointer;
        font-family: inherit;
        min-width: 180px;
        transition: all 0.2s ease;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 12px center;
        padding-right: 32px;
    }

    .lang-select:hover, .domain-select-inline:hover {
        border-color: var(--accent-blue);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }

    .lang-select:focus, .domain-select-inline:focus {
        outline: none;
        border-color: var(--accent-blue);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
    }

    .lang-swap-btn {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        color: var(--text-secondary);
        font-size: 1.2rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        margin-top: 16px;
    }

    .lang-swap-btn:hover {
        background: rgba(59, 130, 246, 0.15);
        border-color: var(--accent-blue);
        color: var(--accent-blue);
        transform: rotate(180deg);
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
