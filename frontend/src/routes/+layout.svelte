<script lang="ts">
    import '../app.css';
    import { uiLang } from '$lib/stores/i18n';
    import { isAuthenticated } from '$lib/stores/auth';
    import Login from '$lib/components/Login.svelte';
    import UserBar from '$lib/components/UserBar.svelte';
</script>

<!-- The store forces reactivity across the app when language changes -->
{#key $uiLang}
<div class="bg-gradient"></div>
<div class="container">
    {#if $isAuthenticated}
        <UserBar />
        <slot />
    {:else}
        <Login />
    {/if}
</div>
{/key}
