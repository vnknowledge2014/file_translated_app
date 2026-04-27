<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { createEventDispatcher } from 'svelte';
    import { sourceLang, targetLang } from '$lib/stores/config';
    import { API_BASE } from '$lib/api';

    export let jobId: string | null = null;
    
    const dispatch = createEventDispatcher();
    
    let segments: any[] = [];
    let isSaving = false;

    $: if (jobId) {
        loadSegments();
    }

    async function loadSegments() {
        if (!jobId) return;
        try {
            const resp = await fetch(`${API_BASE}/api/jobs/${jobId}/segments`);
            const data = await resp.json();
            segments = data.segments || [];
        } catch (e) {
            console.error(e);
        }
    }

    function close() {
        dispatch('close');
    }

    async function save() {
        if (!jobId || isSaving) return;
        isSaving = true;
        try {
            // Update segments one by one (this is simple, actual implementation could batch)
            for (const seg of segments) {
                // In a real app we only save modified ones
                await fetch(`${API_BASE}/api/jobs/${jobId}/segments/${seg.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target_text: seg.target_text })
                });
            }

            // Reconstruct
            const resp = await fetch(`${API_BASE}/api/jobs/${jobId}/reconstruct`, { method: 'POST' });
            if (!resp.ok) throw new Error('Reconstruct failed');
            
            alert('Saved & Reconstructed successfully!');
            close();
        } catch (e: any) {
            alert('Save failed: ' + e.message);
        } finally {
            isSaving = false;
        }
    }
</script>

{#if jobId}
<div class="editor-overlay">
    <div class="editor-modal">
        <div class="editor-header">
            <h3>📝 {m.editor_title()}</h3>
            <div class="editor-actions">
                <button class="editor-btn" on:click={close}>✕ {m.editor_close()}</button>
                <button class="editor-btn primary" on:click={save} disabled={isSaving}>
                    💾 {m.editor_save()}
                </button>
            </div>
        </div>

        <div class="editor-body">
            <div class="editor-layout">
                <main class="editor-main">
                    <table class="review-table">
                        <thead>
                            <tr>
                                <th style="width: 40px">#</th>
                                <th id="review-th-source">{$sourceLang.toUpperCase()}</th>
                                <th id="review-th-target">{$targetLang.toUpperCase()}</th>
                                <th style="width: 80px">{m.editor_confidence()}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each segments as seg, i}
                                <tr>
                                    <td class="seg-idx">{i + 1}</td>
                                    <td class="seg-source">{seg.source_text}</td>
                                    <td class="seg-target">
                                        <!-- svelte-ignore a11y-autofocus -->
                                        <textarea class="edit-textarea" bind:value={seg.target_text}></textarea>
                                    </td>
                                    <td>
                                        {#if seg.confidence_score !== null}
                                            <div class="conf-score {seg.confidence_score >= 0.8 ? 'conf-high' : seg.confidence_score >= 0.5 ? 'conf-mid' : 'conf-low'}">
                                                {Math.round(seg.confidence_score * 100)}%
                                            </div>
                                        {:else}
                                            <div class="conf-score">-</div>
                                        {/if}
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </main>
            </div>
        </div>
    </div>
</div>
{/if}

<style>
    .editor-overlay {
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(0,0,0,0.8); backdrop-filter: blur(8px);
        display: flex; align-items: center; justify-content: center;
        padding: 40px;
    }
    
    .editor-modal {
        background: var(--bg-primary);
        width: 100%; max-width: 1400px; height: 100%;
        border-radius: var(--radius);
        border: 1px solid var(--border-glass);
        display: flex; flex-direction: column; overflow: hidden;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }
    
    .editor-header {
        padding: 20px 32px; background: var(--bg-card);
        border-bottom: 1px solid var(--border-glass);
        display: flex; justify-content: space-between; align-items: center;
    }

    .editor-header h3 { font-weight: 600; font-size: 1.2rem; }
    
    .editor-actions { display: flex; gap: 12px; }
    
    .editor-btn {
        padding: 8px 16px; border-radius: 8px; font-weight: 500;
        cursor: pointer; transition: all 0.2s; border: none;
        background: var(--bg-glass); color: var(--text-primary);
    }
    .editor-btn:hover { background: rgba(255,255,255,0.1); }
    .editor-btn.primary { background: var(--accent-emerald); color: white; }
    .editor-btn.primary:hover { background: #059669; }
    .editor-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    
    .editor-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
    .editor-layout { display: flex; height: 100%; }
    .editor-main { flex: 1; overflow-y: auto; padding: 24px; }
    
    .review-table { width: 100%; border-collapse: separate; border-spacing: 0 8px; }
    .review-table th {
        text-align: left; padding: 0 16px 8px;
        color: var(--text-muted); font-size: 0.85rem; font-weight: 600;
        text-transform: uppercase; border-bottom: 1px solid var(--border-glass);
    }
    .review-table td {
        background: var(--bg-card); padding: 16px; vertical-align: top;
        border-top: 1px solid var(--border-glass); border-bottom: 1px solid var(--border-glass);
    }
    .review-table td:first-child { border-left: 1px solid var(--border-glass); border-radius: 12px 0 0 12px; }
    .review-table td:last-child { border-right: 1px solid var(--border-glass); border-radius: 0 12px 12px 0; }
    
    .seg-idx { color: var(--text-muted); font-size: 0.85rem; font-weight: 600; }
    .seg-source { color: var(--text-secondary); width: 40%; line-height: 1.6; }
    .seg-target { width: 40%; }
    
    .edit-textarea {
        width: 100%; min-height: 80px; padding: 12px;
        background: rgba(0,0,0,0.2); border: 1px solid var(--border-glass);
        border-radius: 8px; color: var(--text-primary); font-family: inherit;
        font-size: 0.95rem; line-height: 1.6; resize: vertical; transition: all 0.2s;
    }
    .edit-textarea:focus { outline: none; border-color: var(--accent-blue); background: rgba(59,130,246,0.05); }
    
    .conf-score {
        display: inline-flex; align-items: center; justify-content: center;
        padding: 4px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; width: 50px;
    }
    .conf-high { background: rgba(16, 185, 129, 0.1); color: var(--accent-emerald); }
    .conf-mid { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
    .conf-low { background: rgba(244, 63, 94, 0.1); color: var(--accent-rose); }
</style>
