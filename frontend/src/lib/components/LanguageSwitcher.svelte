<script lang="ts">
    import { uiLang } from '$lib/stores/i18n';
    import { availableLanguageTags, type AvailableLanguageTag } from '$lib/paraglide/runtime';

    const langNames: Record<AvailableLanguageTag, string> = {
        en: 'English',
        vi: 'Tiếng Việt',
        ja: '日本語'
    };

    let isOpen = false;

    function selectLang(lang: AvailableLanguageTag) {
        uiLang.setLanguage(lang);
        isOpen = false;
        // Optionally reload page to ensure all external non-reactive elements refresh
        window.location.reload();
    }
</script>

<div class="lang-switcher">
    <button class="switcher-btn" on:click={() => isOpen = !isOpen} title="Change UI Language">
        🌐 {$uiLang.toUpperCase()}
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
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
    }

    .switcher-btn {
        background: var(--bg-glass);
        border: 1px solid var(--border-glass);
        color: var(--text-primary);
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-weight: 600;
        backdrop-filter: blur(8px);
        transition: all 0.2s;
    }

    .switcher-btn:hover {
        background: rgba(255, 255, 255, 0.1);
    }

    .dropdown-menu {
        position: absolute;
        top: 100%;
        right: 0;
        margin-top: 8px;
        background: var(--bg-card);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        overflow: hidden;
        min-width: 150px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }

    .dropdown-item {
        display: block;
        width: 100%;
        text-align: left;
        padding: 12px 16px;
        background: transparent;
        border: none;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all 0.2s;
    }

    .dropdown-item:hover {
        background: rgba(255, 255, 255, 0.05);
        color: var(--text-primary);
    }

    .dropdown-item.active {
        color: var(--accent-blue);
        background: rgba(59, 130, 246, 0.1);
        font-weight: 600;
    }
</style>
