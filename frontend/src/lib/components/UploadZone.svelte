<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { uploadDocument } from '$lib/api';
    import { sourceLang, targetLang, currentDomain } from '$lib/stores/config';
    import { createEventDispatcher } from 'svelte';
    import IconUpload from '$lib/components/icons/IconUpload.svelte';
    import IconX from '$lib/components/icons/IconX.svelte';
    import { showToast } from '$lib/stores/toast';

    const dispatch = createEventDispatcher();

    let fileInput: HTMLInputElement;
    let exportXliff = false;
    let noTranslate = false;
    let xliffVersion = '2.1';
    let isDragging = false;
    let isUploading = false;
    let uploadFileName = '';
    let uploadCurrent = 0;
    let uploadTotal = 0;



    function handleDragOver(e: DragEvent) {
        e.preventDefault();
        isDragging = true;
    }

    function handleDragLeave(e: DragEvent) {
        e.preventDefault();
        isDragging = false;
    }

    function handleDrop(e: DragEvent) {
        e.preventDefault();
        isDragging = false;
        if (e.dataTransfer?.files.length) {
            uploadMultiple(Array.from(e.dataTransfer.files));
        }
    }

    function handleFileSelect(e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files?.length) {
            uploadMultiple(Array.from(target.files));
        }
    }

    async function uploadMultiple(files: File[]) {
        if (!files.length) return;
        uploadTotal = files.length;
        uploadCurrent = 0;
        for (const file of files) {
            uploadCurrent++;
            await upload(file);
        }
        uploadTotal = 0;
        uploadCurrent = 0;
    }

    async function upload(file: File) {
        if (!file) return;
        isUploading = true;
        uploadFileName = file.name;
        const fd = new FormData();
        fd.append('file', file);
        fd.append('export_xliff', exportXliff.toString());
        fd.append('xliff_version', xliffVersion);
        fd.append('no_translate', noTranslate.toString());
        fd.append('domain', $currentDomain);
        fd.append('source_lang', $sourceLang);
        fd.append('target_lang', $targetLang);

        try {
            const data = await uploadDocument(fd);
            showToast(`"${file.name}" — Translation queued successfully`, 'success');
            dispatch('uploaded', data);
        } catch (e: any) {
            showToast(`Upload failed: ${e.message}`, 'error');
        } finally {
            isUploading = false;
            uploadFileName = '';
            if (fileInput) fileInput.value = '';
        }
    }
</script>



<div 
    class="upload-zone {isDragging ? 'dragover' : ''} {isUploading ? 'uploading' : ''}"
    on:dragover={handleDragOver}
    on:dragleave={handleDragLeave}
    on:drop={handleDrop}
    on:click={() => !isUploading && fileInput.click()}
>
    <!-- Upload progress overlay -->
    {#if isUploading}
        <div class="upload-progress-overlay">
            <div class="upload-spinner"></div>
            <h3 class="uploading-title">{uploadTotal > 1 ? `Uploading ${uploadCurrent}/${uploadTotal}` : 'Uploading & Queuing…'}</h3>
            <p class="uploading-filename">{uploadFileName}</p>
            <div class="progress-track">
                <div class="progress-bar-fill"></div>
            </div>
            <p class="uploading-hint">Your file is being sent to the translation engine</p>
        </div>
    {:else}
        <div class="upload-icon"><IconUpload size={36} color="var(--accent)" /></div>
        <h3>{m.upload_title()}</h3>
        <p>{m.upload_subtitle()}</p>
        
        <div class="file-types">
            <span class="file-type-badge">DOCX</span>
            <span class="file-type-badge">XLSX</span>
            <span class="file-type-badge">PPTX</span>
            <span class="file-type-badge">PDF</span>
            <span class="file-type-badge">CSV</span>
            <span class="file-type-badge">TXT</span>
            <span class="file-type-badge">MD</span>
        </div>
    {/if}

    <input 
        type="file" 
        bind:this={fileInput} 
        on:change={handleFileSelect}
        accept=".docx,.xlsx,.pptx,.pdf,.csv,.txt,.md" 
        multiple
        style="display: none;"
    >
    
    <!-- Prevent click propagation to parent -->
    {#if !isUploading}
        <div class="upload-options" on:click|stopPropagation>
            <label class="toggle-row">
                <span class="toggle-switch" class:on={exportXliff} on:click|preventDefault={() => exportXliff = !exportXliff}>
                    <span class="toggle-knob"></span>
                </span>
                <span class="toggle-text">{m.upload_xliff_option()}</span>
                {#if exportXliff}
                    <select bind:value={xliffVersion} class="version-select">
                        <option value="2.1">{m.upload_version_new()}</option>
                        <option value="1.2">{m.upload_version_old()}</option>
                    </select>
                {/if}
            </label>
            <label class="toggle-row">
                <span class="toggle-switch" class:on={noTranslate} on:click|preventDefault={() => noTranslate = !noTranslate}>
                    <span class="toggle-knob"></span>
                </span>
                <span class="toggle-text">Extract Only (No Translation)</span>
            </label>
        </div>
    {/if}
</div>

<style>

    .upload-zone {
        position: relative;
        background: var(--bg-card);
        border: 2px dashed var(--border);
        border-radius: var(--radius);
        padding: 36px 32px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        backdrop-filter: blur(12px);
        overflow: hidden;
    }

    .upload-zone::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: var(--radius);
        background: var(--gradient-primary);
        opacity: 0;
        transition: opacity 0.3s;
    }

    .upload-zone:hover:not(.uploading) {
        border-color: var(--accent);
        box-shadow: var(--shadow-glow);
    }

    .upload-zone:hover:not(.uploading)::before {
        opacity: 0.04;
    }

    .upload-zone.dragover {
        border-color: var(--accent-hover);
        transform: scale(1.01);
    }
    
    .upload-zone.uploading {
        cursor: wait;
        border-color: rgba(99, 102, 241, 0.5);
        border-style: solid;
        box-shadow: 0 0 30px rgba(99, 102, 241, 0.15);
    }

    .upload-icon {
        font-size: 4rem;
        margin-bottom: 12px;
        position: relative;
        z-index: 1;
    }

    .upload-zone h3 {
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 6px;
        position: relative;
        z-index: 1;
    }

    .upload-zone p {
        color: var(--text-muted);
        font-size: 0.82rem;
        position: relative;
        z-index: 1;
    }

    .file-types {
        display: flex;
        justify-content: center;
        gap: 6px;
        margin-top: 14px;
        position: relative;
        z-index: 1;
        flex-wrap: wrap;
    }

    .file-type-badge {
        padding: 3px 10px;
        border-radius: 100px;
        background: rgba(59, 130, 246, 0.1);
        color: var(--accent);
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    .upload-options {
        margin-top: 16px;
        z-index: 2;
        position: relative;
    }

    /* ── Toggle Switch ── */
    .toggle-row {
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        color: var(--text-secondary);
        font-size: 0.82rem;
    }

    .toggle-switch {
        width: 36px;
        height: 20px;
        border-radius: 10px;
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
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #fff;
        transition: transform 0.2s ease;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    }

    .toggle-switch.on .toggle-knob {
        transform: translateX(16px);
    }

    .toggle-text {
        user-select: none;
    }
    
    .version-select {
        padding: 3px 8px;
        border-radius: 6px;
        background: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid var(--border);
        outline: none;
        font-size: 0.78rem;
        font-family: inherit;
    }

    /* ── Upload Progress Overlay ── */
    .upload-progress-overlay {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        position: relative;
        z-index: 2;
    }

    .upload-spinner {
        width: 48px;
        height: 48px;
        border: 3px solid rgba(99, 102, 241, 0.15);
        border-top-color: var(--accent);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .uploading-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
        animation: pulse-text 1.5s ease-in-out infinite;
    }

    @keyframes pulse-text {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    .uploading-filename {
        font-size: 0.85rem;
        color: var(--accent);
        font-weight: 500;
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin: 0;
    }

    .progress-track {
        width: 280px;
        height: 6px;
        background: rgba(255, 255, 255, 0.06);
        border-radius: 100px;
        overflow: hidden;
        margin-top: 4px;
    }

    .progress-bar-fill {
        height: 100%;
        width: 30%;
        background: linear-gradient(90deg, var(--accent), var(--accent-hover));
        border-radius: 100px;
        animation: indeterminate 1.5s ease-in-out infinite;
    }

    @keyframes indeterminate {
        0% { width: 10%; margin-left: 0; }
        50% { width: 50%; margin-left: 25%; }
        100% { width: 10%; margin-left: 90%; }
    }

    .uploading-hint {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin: 0;
    }
</style>
