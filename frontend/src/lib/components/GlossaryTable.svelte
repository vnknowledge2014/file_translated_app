<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { fetchGlossary, deleteGlossaryTerm, uploadGlossary } from '$lib/api';
    import { currentDomain, sourceLang, targetLang } from '$lib/stores/config';
    import { onMount } from 'svelte';
    import IconFileText from '$lib/components/icons/IconFileText.svelte';
    import IconUpload from '$lib/components/icons/IconUpload.svelte';
    import { showToast } from '$lib/stores/toast';
    import IconTrash from '$lib/components/icons/IconTrash.svelte';

    let terms: any[] = [];
    let replaceOld = true;
    let fileInput: HTMLInputElement;

    async function loadTerms() {
        try {
            const data = await fetchGlossary($currentDomain);
            terms = data.terms || [];
        } catch (e) {
            console.error('Failed to load glossary:', e);
        }
    }

    // Reload when domain changes
    $: if ($currentDomain) {
        loadTerms();
    }

    onMount(loadTerms);

    async function handleDelete(id: number) {
        if (!confirm(m.glossary_delete_confirm())) return;
        try {
            await deleteGlossaryTerm(id);
            terms = terms.filter(t => t.id !== id);
        } catch (e) {
            showToast('Delete failed', 'error');
        }
    }

    async function handleUpload(e: Event) {
        const target = e.target as HTMLInputElement;
        if (!target.files?.length) return;
        
        const fd = new FormData();
        fd.append('file', target.files[0]);
        fd.append('replace', replaceOld.toString());
        fd.append('domain', $currentDomain);
        
        terms = [];
        try {
            const data = await uploadGlossary(fd);
            showToast(`Added ${data.added} terms.`, 'success');
            loadTerms();
        } catch (err: any) {
            showToast('Upload failed: ' + err.message, 'error');
            loadTerms();
        } finally {
            target.value = '';
        }
    }
</script>

<div class="glossary-section">
    <div class="glossary-header">
        <h3><IconFileText size={18} color="var(--accent)" /> {m.glossary_title()}</h3>
        <div style="display: flex; gap: 8px; align-items: center;">
            <label class="toggle-row">
                <span class="toggle-switch" class:on={replaceOld} on:click|preventDefault={() => replaceOld = !replaceOld}>
                    <span class="toggle-knob"></span>
                </span>
                <span class="toggle-text">{m.glossary_replace_old()}</span>
            </label>
            <button class="btn-upload" on:click={() => fileInput.click()}>
                <IconUpload size={14} /> {m.glossary_upload_csv()}
            </button>
            <input type="file" bind:this={fileInput} accept=".csv" on:change={handleUpload} hidden>
        </div>
    </div>
    <p class="csv-hint">
        CSV Format: Column 1 (Source), Column 2 (Target), Column 3 (Context - Optional).
    </p>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th id="glossary-th-source">{$sourceLang === 'auto' ? 'SOURCE' : $sourceLang.toUpperCase()} ({m.glossary_col_source()})</th>
                    <th id="glossary-th-target">{$targetLang.toUpperCase()} ({m.glossary_col_target()})</th>
                    <th>{m.glossary_col_context()}</th>
                    <th style="width: 80px; text-align: center;">{m.glossary_col_action()}</th>
                </tr>
            </thead>
            <tbody>
                {#if terms.length === 0}
                    <tr><td colspan="4" class="glossary-empty">{m.glossary_empty()}</td></tr>
                {:else}
                    {#each terms as t (t.id)}
                        <tr>
                            <td class="seg-source">{t.source_text || t.jp}</td>
                            <td>{t.target_text || t.vi}</td>
                            <td class="seg-context">{t.context || ''}</td>
                            <td style="text-align: center;">
                                <button class="btn-delete" on:click={() => handleDelete(t.id)} title={m.glossary_delete()}>
                                    <IconTrash size={16} color="var(--danger)" />
                                </button>
                            </td>
                        </tr>
                    {/each}
                {/if}
            </tbody>
        </table>
    </div>
</div>

<style>
    .glossary-section {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius);
        padding: 24px;
        margin-top: 32px;
    }

    .glossary-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        flex-wrap: wrap;
        gap: 12px;
    }

    .glossary-header h3 {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1rem;
    }

    .toggle-row {
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--text-secondary);
        cursor: pointer;
    }

    .toggle-switch {
        width: 32px;
        height: 18px;
        border-radius: 9px;
        background: var(--border);
        position: relative;
        cursor: pointer;
        transition: background 0.2s ease;
        flex-shrink: 0;
    }

    .toggle-switch.on {
        background: var(--accent);
    }

    .toggle-knob {
        position: absolute;
        top: 2px;
        left: 2px;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #fff;
        transition: transform 0.2s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }

    .toggle-switch.on .toggle-knob {
        transform: translateX(14px);
    }

    .toggle-text {
        user-select: none;
    }

    .csv-hint {
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-bottom: 16px;
    }

    .table-container {
        overflow-x: auto;
        border-radius: var(--radius-sm);
        border: 1px solid var(--border-subtle);
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }

    th, td {
        padding: 12px 16px;
        text-align: left;
        border-bottom: 1px solid var(--border-subtle);
    }

    th {
        background: var(--bg-elevated);
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    tbody tr:hover {
        background: var(--bg-elevated);
    }

    .seg-source { color: var(--accent); font-weight: 500; }
    .seg-context { color: var(--text-muted); font-size: 0.8rem; }
    
    .glossary-empty {
        text-align: center;
        padding: 32px !important;
        color: var(--text-muted);
        font-style: italic;
    }

    .btn-delete {
        background: none;
        border: none;
        cursor: pointer;
        opacity: 0.5;
        transition: opacity var(--transition-base);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
    }

    .btn-delete:hover { opacity: 1; }

    .btn-upload {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--accent-muted);
        color: var(--accent);
        border: 1px solid rgba(20, 184, 166, 0.3);
        padding: 8px 16px;
        border-radius: var(--radius-sm);
        font-size: 0.8rem;
        font-weight: 500;
        font-family: inherit;
        cursor: pointer;
        transition: all var(--transition-base);
    }

    .btn-upload:hover {
        background: rgba(20, 184, 166, 0.2);
    }
</style>
