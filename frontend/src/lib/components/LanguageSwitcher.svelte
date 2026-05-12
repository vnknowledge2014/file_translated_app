<script lang="ts">
    import { uiLang } from '$lib/stores/i18n';
    import { availableLanguageTags, type AvailableLanguageTag } from '$lib/paraglide/runtime';
    import IconGlobe from '$lib/components/icons/IconGlobe.svelte';

    const langNames: Record<AvailableLanguageTag, string> = {
        en: 'English',
        vi: 'Tiếng Việt',
        ja: '日本語',
        zh: '中文'
    };

    let isOpen = false;

    function selectLang(lang: AvailableLanguageTag) {
        uiLang.setLanguage(lang);
        isOpen = false;
        window.location.reload();
    }
</script>

<div class="lang-switcher">
    <button class="switcher-btn" on:click={() => isOpen = !isOpen} title="Change UI Language">
        <IconGlobe size={16} />
        {$uiLang.toUpperCase()}
    </button>
    
    {#if isOpen}
        <div class="dropdown-menu">
            {#each availableLanguageTags as lang}
                <button 
                    class="dropdown-item" 
                    class:active={$uiLang === lang}
                    on:click={() => selectLang(lang)}
                >
                    {langNames[lang]}
                </button>
            {/each}
        </div>
    {/if}
</div>

<style>
    .lang-switcher {
        position: relative;
    }

    .switcher-btn {
        background: var(--bg-elevated);
        border: 1px solid var(--border-subtle);
        color: var(--text-secondary);
        padding: 6px 14px;
        border-radius: 20px;
        cursor: pointer;
        font-weight: 600;
        font-size: 0.75rem;
        font-family: inherit;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all var(--transition-base);
    }

    .switcher-btn:hover {
        background: var(--bg-card-hover);
        color: var(--text-primary);
    }

    .dropdown-menu {
        position: absolute;
        top: 100%;
        right: 0;
        margin-top: 8px;
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        overflow: hidden;
        min-width: 150px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        z-index: 100;
    }

    .dropdown-item {
        display: block;
        width: 100%;
        text-align: left;
        padding: 10px 16px;
        background: transparent;
        border: none;
        color: var(--text-secondary);
        cursor: pointer;
        font-family: inherit;
        font-size: 0.85rem;
        transition: all var(--transition-base);
    }

    .dropdown-item:hover {
        background: var(--bg-elevated);
        color: var(--text-primary);
    }

    .dropdown-item.active {
        color: var(--accent);
        background: var(--accent-muted);
        font-weight: 600;
    }
</style>
