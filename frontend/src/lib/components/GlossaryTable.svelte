<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { fetchGlossary, deleteGlossaryTerm, uploadGlossary } from '$lib/api';
    import { currentDomain, sourceLang, targetLang } from '$lib/stores/config';
    import { onMount } from 'svelte';

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
            alert('Delete failed');
        }
    }

    async function handleUpload(e: Event) {
        const target = e.target as HTMLInputElement;
        if (!target.files?.length) return;
        
        const fd = new FormData();
        fd.append('file', target.files[0]);
        fd.append('replace', replaceOld.toString());
        fd.append('domain', $currentDomain);
        
        // Let user know it's uploading by clearing and setting a temp state
        terms = [];
        try {
            const data = await uploadGlossary(fd);
            alert(`Added ${data.added} terms.`);
            loadTerms();
        } catch (err: any) {
            alert('Upload failed: ' + err.message);
            loadTerms();
        } finally {
            target.value = '';
        }
    }
</script>

<div class="glossary-section">
    <div class="glossary-header">
        <h3>📖 {m.glossary_title()}</h3>
        <div style="display: flex; gap: 8px; align-items: center;">
            <label style="font-size: 0.85rem; display: flex; align-items: center; gap: 4px;">
                <input type="checkbox" bind:checked={replaceOld}> {m.glossary_replace_old()}
            </label>
            <button class="btn-xliff" on:click={() => fileInput.click()} style="margin:0;">
                📤 {m.glossary_upload_csv()}
            </button>
            <input type="file" bind:this={fileInput} accept=".csv" on:change={handleUpload} hidden>
        </div>
    </div>
    <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 16px;">
        CSV Format: Column 1 (Source), Column 2 (Target), Column 3 (Context - Optional).
    </p>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th id="glossary-th-source">{$sourceLang.toUpperCase()} ({m.glossary_col_source()})</th>
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
                                    🗑️
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
        border: 1px solid var(--border-glass);
        border-radius: var(--radius);
        padding: 24px;
        margin-top: 32px;
        backdrop-filter: blur(12px);
    }

    .glossary-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        flex-wrap: wrap;
        gap: 12px;
    }

    .table-container {
        overflow-x: auto;
        border-radius: var(--radius-sm);
        border: 1px solid var(--border-glass);
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }

    th, td {
        padding: 12px 16px;
        text-align: left;
        border-bottom: 1px solid var(--border-glass);
    }

    th {
        background: rgba(255, 255, 255, 0.02);
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.8rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    tbody tr:hover {
        background: rgba(255, 255, 255, 0.02);
    }

    .seg-source { color: var(--accent-cyan); font-weight: 500; }
    .seg-context { color: var(--text-muted); font-size: 0.85rem; }
    
    .glossary-empty {
        text-align: center;
        padding: 32px !important;
        color: var(--text-muted);
        font-style: italic;
    }

    .btn-delete {
        background: none; border: none; cursor: pointer;
        opacity: 0.5; transition: opacity 0.2s;
        font-size: 1.1rem;
    }

    .btn-delete:hover { opacity: 1; }

    .btn-xliff {
        background: rgba(139, 92, 246, 0.1);
        color: var(--accent-purple);
        border: 1px solid rgba(139, 92, 246, 0.2);
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-xliff:hover {
        background: rgba(139, 92, 246, 0.2);
    }
</style>
