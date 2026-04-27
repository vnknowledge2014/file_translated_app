<script lang="ts">
    import { user, logout } from '$lib/stores/auth';
</script>

<header class="user-bar">
    <div class="left">
        <span class="app-name">📄 Translation Portal</span>
    </div>
    <div class="right">
        {#if $user}
            <span class="username">👤 {$user.username}</span>
        {/if}
        <button class="logout-btn" on:click={logout}>Sign Out</button>
    </div>
</header>

<style>
    .user-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.625rem 1.25rem;
        background: var(--surface-light, #ffffff);
        border-bottom: 1px solid var(--border-light, #e2e8f0);
        margin: -1rem -1rem 1rem -1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .left {
        display: flex;
        align-items: center;
    }

    .app-name {
        font-weight: 700;
        font-size: 1rem;
        color: var(--text-dark, #1a202c);
    }

    .right {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .username {
        font-size: 0.8125rem;
        color: var(--text-light, #718096);
        font-weight: 500;
    }

    .logout-btn {
        padding: 0.375rem 0.75rem;
        background: transparent;
        color: var(--text-light, #718096);
        border: 1px solid var(--border-light, #e2e8f0);
        border-radius: 6px;
        font-size: 0.8125rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }

    .logout-btn:hover {
        background: #fee2e2;
        color: #991b1b;
        border-color: #fecaca;
    }
</style>
