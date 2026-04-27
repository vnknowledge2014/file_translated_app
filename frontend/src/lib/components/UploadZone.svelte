<script lang="ts">
    import * as m from '$lib/paraglide/messages';
    import { uploadDocument } from '$lib/api';
    import { sourceLang, targetLang, currentDomain } from '$lib/stores/config';
    import { createEventDispatcher } from 'svelte';

    const dispatch = createEventDispatcher();

    let fileInput: HTMLInputElement;
    let exportXliff = false;
    let xliffVersion = '2.1';
    let isDragging = false;
    let isUploading = false;

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
            upload(e.dataTransfer.files[0]);
        }
    }

    function handleFileSelect(e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files?.length) {
            upload(target.files[0]);
        }
    }

    async function upload(file: File) {
        if (!file) return;
        isUploading = true;
        const fd = new FormData();
        fd.append('file', file);
        fd.append('export_xliff', exportXliff.toString());
        fd.append('xliff_version', xliffVersion);
        fd.append('domain', $currentDomain);
        fd.append('source_lang', $sourceLang);
        fd.append('target_lang', $targetLang);

        try {
            const data = await uploadDocument(fd);
            dispatch('uploaded', data);
        } catch (e: any) {
            alert('Upload failed: ' + e.message);
        } finally {
            isUploading = false;
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
    <div class="upload-icon">📄</div>
    <h3>{isUploading ? m.glossary_uploading() : m.upload_title()}</h3>
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

    <input 
        type="file" 
        bind:this={fileInput} 
        on:change={handleFileSelect}
        accept=".docx,.xlsx,.pptx,.pdf,.csv,.txt,.md" 
        style="display: none;"
    >
    
    <!-- Prevent click propagation to parent -->
    <div class="upload-options" on:click|stopPropagation>
        <label class="checkbox-label">
            <input type="checkbox" bind:checked={exportXliff}>
            {m.upload_xliff_option()}
            
            <select bind:value={xliffVersion} class="version-select">
                <option value="2.1">{m.upload_version_new()}</option>
                <option value="1.2">{m.upload_version_old()}</option>
            </select>
        </label>
    </div>
</div>

<style>
    .upload-zone {
        position: relative;
        background: var(--bg-card);
        border: 2px dashed var(--border-glass);
        border-radius: var(--radius);
        padding: 60px 40px;
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
        border-color: var(--accent-blue);
        box-shadow: var(--shadow-glow);
    }

    .upload-zone:hover:not(.uploading)::before {
        opacity: 0.04;
    }

    .upload-zone.dragover {
        border-color: var(--accent-purple);
        transform: scale(1.01);
    }
    
    .upload-zone.uploading {
        opacity: 0.7;
        cursor: wait;
    }

    .upload-icon {
        font-size: 4rem;
        margin-bottom: 16px;
        position: relative;
        z-index: 1;
    }

    .upload-zone h3 {
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 8px;
        position: relative;
        z-index: 1;
    }

    .upload-zone p {
        color: var(--text-muted);
        font-size: 0.85rem;
        position: relative;
        z-index: 1;
    }

    .file-types {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-top: 16px;
        position: relative;
        z-index: 1;
    }

    .file-type-badge {
        padding: 4px 12px;
        border-radius: 100px;
        background: rgba(59, 130, 246, 0.1);
        color: var(--accent-blue);
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    .upload-options {
        margin-top: 20px;
        font-size: 0.9rem;
        z-index: 2;
        position: relative;
    }

    .checkbox-label {
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        color: var(--text-secondary);
    }
    
    .version-select {
        padding: 2px 6px;
        border-radius: 4px;
        background: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid var(--border-glass);
        outline: none;
    }
</style>
