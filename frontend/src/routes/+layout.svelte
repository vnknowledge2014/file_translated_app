<script lang="ts">
    import '../app.css';
    import { uiLang } from '$lib/stores/i18n';
</script>

<!-- The store forces reactivity across the app when language changes -->
{#key $uiLang}
<div class="bg-gradient"></div>
<div class="container">
    <slot />
</div>
{/key}
