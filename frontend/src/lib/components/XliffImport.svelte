<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { API_BASE } from '$lib/api';
    import IconFile from '$lib/components/icons/IconFile.svelte';
    import IconFileText from '$lib/components/icons/IconFileText.svelte';
    import IconCheckCircle from '$lib/components/icons/IconCheckCircle.svelte';
    import IconSpinner from '$lib/components/icons/IconSpinner.svelte';
    import IconReconstruct from '$lib/components/icons/IconReconstruct.svelte';
    import IconDownload from '$lib/components/icons/IconDownload.svelte';
    import IconAlertTriangle from '$lib/components/icons/IconAlertTriangle.svelte';

    let originalFile: File | null = null;
    let xliffFile: File | null = null;
    let isProcessing = false;
    let resultMessage = '';
    let resultType: 'success' | 'error' | '' = '';

    let originalInput: HTMLInputElement;
    let xliffInput: HTMLInputElement;

    $: isReady = originalFile && xliffFile && !isProcessing;

    function handleOriginalSelect(e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files?.length) originalFile = target.files[0];
    }

    function handleXliffSelect(e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files?.length) xliffFile = target.files[0];
    }

    async function submitReconstruct() {
        if (!originalFile || !xliffFile) return;
        isProcessing = true;
        resultMessage = '';
        resultType = '';

        const fd = new FormData();
        fd.append('original', originalFile);
        fd.append('xliff', xliffFile);

        const token = localStorage.getItem('access_token');

        try {
            const resp = await fetch(`${API_BASE}/api/reconstruct-xliff`, {
                method: 'POST',
                body: fd,
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (resp.ok) {
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const cd = resp.headers.get('content-disposition');
                const fn = cd ? cd.split('filename=')[1]?.replace(/"/g, '') : 'reconstructed.docx';
                a.href = url;
                a.download = fn;
                a.click();
                URL.revokeObjectURL(url);
                resultMessage = 'Reconstruction complete. File downloaded.';
                resultType = 'success';
            } else {
                const data = await resp.json().catch(() => ({}));
                resultMessage = `${data.error || data.detail || 'Reconstruction failed'}`;
                resultType = 'error';
            }
        } catch (e: any) {
            resultMessage = `Error: ${e.message}`;
            resultType = 'error';
        } finally {
            isProcessing = false;
        }
    }

    function resetForm() {
        originalFile = null;
        xliffFile = null;
        resultMessage = '';
        resultType = '';
        if (originalInput) originalInput.value = '';
        if (xliffInput) xliffInput.value = '';
    }
</script>

<section class="xliff-section">
    <h3><IconDownload size={18} color="var(--accent)" /> XLIFF Import — Reconstruct from Reviewed XLIFF</h3>
    <p class="xliff-desc">
        Drop your original document and reviewed XLIFF file to reconstruct a translated version.
    </p>

    <div class="xliff-grid">
        <!-- Original file drop -->
        <div 
            class="xliff-drop" 
            class:has-file={originalFile}
            on:click={() => originalInput.click()}
        >
            <div class="drop-icon">
                {#if originalFile}
                    <IconCheckCircle size={32} color="var(--success)" />
                {:else}
                    <IconFile size={32} color="var(--text-muted)" />
                {/if}
            </div>
            <strong>{originalFile ? 'Original Selected' : 'Original Document'}</strong>
            <small>{originalFile ? originalFile.name : 'DOCX, XLSX, PPTX...'}</small>
            <input 
                type="file" 
                bind:this={originalInput} 
                on:change={handleOriginalSelect} 
                accept=".docx,.xlsx,.pptx,.pdf" 
                style="display:none;"
            >
        </div>

        <!-- XLIFF file drop -->
        <div 
            class="xliff-drop"
            class:has-file={xliffFile} 
            on:click={() => xliffInput.click()}
        >
            <div class="drop-icon">
                {#if xliffFile}
                    <IconCheckCircle size={32} color="var(--success)" />
                {:else}
                    <IconFileText size={32} color="var(--text-muted)" />
                {/if}
            </div>
            <strong>{xliffFile ? 'XLIFF Selected' : 'Reviewed XLIFF'}</strong>
            <small>{xliffFile ? xliffFile.name : '.xlf or .xliff file'}</small>
            <input 
                type="file" 
                bind:this={xliffInput} 
                on:change={handleXliffSelect} 
                accept=".xlf,.xliff" 
                style="display:none;"
            >
        </div>

        <!-- Submit button -->
        <button 
            class="xliff-submit"
            class:ready={isReady}
            on:click={submitReconstruct}
            disabled={!isReady}
        >
            {#if isProcessing}
                <IconSpinner size={16} color="#fff" /> Processing...
            {:else}
                <IconReconstruct size={16} /> Reconstruct from XLIFF
            {/if}
        </button>
    </div>

    {#if resultMessage}
        <div class="xliff-result" class:success={resultType === 'success'} class:error={resultType === 'error'}>
            {#if resultType === 'success'}
                <IconCheckCircle size={16} color="var(--success)" />
            {:else}
                <IconAlertTriangle size={16} color="var(--danger)" />
            {/if}
            {resultMessage}
            <button class="reset-btn" on:click={resetForm}>Reset</button>
        </div>
    {/if}
</section>

<style>
    .xliff-section {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius);
        padding: 24px;
        margin-top: 32px;
    }

    .xliff-section h3 {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .xliff-desc {
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-bottom: 20px;
    }

    .xliff-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    .xliff-drop {
        border: 1px dashed var(--border);
        border-radius: var(--radius-sm);
        padding: 24px;
        text-align: center;
        cursor: pointer;
        transition: all var(--transition-base);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
    }

    .xliff-drop:hover {
        border-color: var(--accent);
        background: var(--accent-muted);
    }

    .xliff-drop.has-file {
        border-color: var(--success);
        border-style: solid;
        background: var(--success-muted);
    }

    .xliff-drop strong {
        font-size: 0.85rem;
        color: var(--text-primary);
    }

    .xliff-drop small {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    .xliff-submit {
        grid-column: 1 / -1;
        padding: 12px 24px;
        border-radius: var(--radius-sm);
        background: var(--accent);
        color: #fff;
        font-weight: 600;
        font-size: 0.85rem;
        font-family: inherit;
        border: none;
        cursor: pointer;
        transition: all var(--transition-base);
        opacity: 0.4;
        pointer-events: none;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }

    .xliff-submit.ready {
        opacity: 1;
        pointer-events: auto;
    }

    .xliff-submit.ready:hover {
        background: var(--accent-hover);
        transform: translateY(-1px);
        box-shadow: var(--accent-glow);
    }

    .xliff-result {
        margin-top: 16px;
        padding: 12px 16px;
        border-radius: var(--radius-sm);
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .xliff-result.success {
        background: var(--success-muted);
        color: var(--success);
    }

    .xliff-result.error {
        background: var(--danger-muted);
        color: var(--danger);
    }

    .reset-btn {
        margin-left: auto;
        padding: 4px 12px;
        border-radius: 6px;
        border: 1px solid currentColor;
        background: transparent;
        color: inherit;
        font-size: 0.75rem;
        font-family: inherit;
        cursor: pointer;
        opacity: 0.7;
    }

    .reset-btn:hover { opacity: 1; }
</style>
