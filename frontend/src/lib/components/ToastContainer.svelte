<script lang="ts">
    import { toastStore } from '$lib/stores/toast';
    import IconX from '$lib/components/icons/IconX.svelte';
    import { fly, fade } from 'svelte/transition';
</script>

<div class="toast-container">
    {#each $toastStore as toast (toast.id)}
        <div 
            class="toast toast-{toast.type}" 
            role="alert"
            in:fly={{ y: -20, duration: 300 }}
            out:fade={{ duration: 200 }}
        >
            <span>{toast.message}</span>
            <button class="toast-close" on:click={() => toastStore.remove(toast.id)}>
                <IconX size={14} />
            </button>
        </div>
    {/each}
</div>

<style>
    .toast-container {
        position: fixed;
        top: 24px;
        right: 24px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 10px;
        pointer-events: none;
    }

    .toast {
        pointer-events: auto;
        padding: 14px 20px;
        border-radius: 12px;
        font-size: 0.9rem;
        font-weight: 500;
        max-width: 440px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(16px);
    }

    .toast-success {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.05));
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #6ee7b7;
    }

    .toast-error {
        background: linear-gradient(135deg, rgba(244, 63, 94, 0.2), rgba(244, 63, 94, 0.05));
        border: 1px solid rgba(244, 63, 94, 0.4);
        color: #fda4af;
    }

    .toast-info {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(59, 130, 246, 0.05));
        border: 1px solid rgba(59, 130, 246, 0.4);
        color: #93c5fd;
    }

    .toast-close {
        background: none;
        border: none;
        color: inherit;
        opacity: 0.6;
        cursor: pointer;
        font-size: 1rem;
        padding: 0;
        margin-left: auto;
    }
    .toast-close:hover { opacity: 1; }
</style>
