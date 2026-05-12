<script lang="ts">
    const API_BASE = 'https://your-infitrans-instance.com';
    let copiedIdx = -1;

    const endpoints = [
        {
            method: 'POST',
            path: '/api/upload',
            desc: 'Upload a document for translation',
            auth: 'translate',
            params: [
                { name: 'file', type: 'File', required: true, desc: 'Document file (.docx, .xlsx, .pptx, .pdf, .csv, .txt, .md)' },
                { name: 'source_lang', type: 'string', required: false, desc: 'Source language code (default: auto-detect)' },
                { name: 'target_lang', type: 'string', required: false, desc: 'Target language code (default: en)' },
                { name: 'domain', type: 'string', required: false, desc: 'Translation domain: general, it, legal, medical, finance, marketing, it_sw' },
                { name: 'export_xliff', type: 'boolean', required: false, desc: 'Export XLIFF alongside translated file' },
                { name: 'webhook_url', type: 'string', required: false, desc: 'URL to receive job completion callback' },
            ],
            curl: `curl -X POST ${API_BASE}/api/upload \\
  -H "X-API-Key: itk_translate_your_key_here" \\
  -F "file=@document.docx" \\
  -F "target_lang=vi" \\
  -F "domain=general"`,
            response: `{
  "job_id": "job:abc123",
  "filename": "document.docx",
  "file_type": "docx",
  "status": "queued",
  "queue_position": 1
}`,
        },
        {
            method: 'GET',
            path: '/api/jobs',
            desc: 'List all translation jobs',
            auth: 'read',
            params: [],
            curl: `curl ${API_BASE}/api/jobs \\
  -H "X-API-Key: itk_read_your_key_here"`,
            response: `[
  {
    "id": "job:abc123",
    "filename": "document.docx",
    "status": "completed",
    "progress": 1.0,
    "segments_count": 142,
    "duration_seconds": 45.2,
    "created_at": "2026-05-01T10:00:00Z"
  }
]`,
        },
        {
            method: 'GET',
            path: '/api/download/{job_id}',
            desc: 'Download translated document',
            auth: 'read',
            params: [
                { name: 'xliff', type: 'boolean', required: false, desc: 'Set to true to download XLIFF instead' },
            ],
            curl: `curl -O ${API_BASE}/api/download/job:abc123 \\
  -H "X-API-Key: itk_read_your_key_here"`,
            response: '# Binary file download (Content-Disposition: attachment)',
        },
        {
            method: 'GET',
            path: '/api/jobs/{job_id}/segments',
            desc: 'Get bilingual segments for Human-in-the-Loop review',
            auth: 'read',
            params: [],
            curl: `curl ${API_BASE}/api/jobs/job:abc123/segments \\
  -H "X-API-Key: itk_read_your_key_here"`,
            response: `[\n  {\n    "index": 0,\n    "source": "Hello World",\n    "target": "Xin chào thế giới",\n    "status": "pending",\n    "confidence": 0.95\n  }\n]`,
        },
        {
            method: 'PUT',
            path: '/api/jobs/{job_id}/segments/{index}',
            desc: 'Update a specific translation segment',
            auth: 'translate',
            params: [
                { name: 'target', type: 'string', required: true, desc: 'Corrected translation text' }
            ],
            curl: `curl -X PUT ${API_BASE}/api/jobs/job:abc123/segments/0 \\
  -H "X-API-Key: itk_translate_your_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{"target": "Chào thế giới"}'`,
            response: `{\n  "status": "success"\n}`,
        },
        {
            method: 'POST',
            path: '/api/jobs/{job_id}/segments/approve-all',
            desc: 'Approve all pending segments',
            auth: 'translate',
            params: [],
            curl: `curl -X POST ${API_BASE}/api/jobs/job:abc123/segments/approve-all \\
  -H "X-API-Key: itk_translate_your_key_here"`,
            response: `{\n  "status": "success",\n  "approved_count": 142\n}`,
        },
        {
            method: 'POST',
            path: '/api/jobs/{job_id}/segments/reconstruct',
            desc: 'Trigger file reconstruction after manual edits',
            auth: 'translate',
            params: [],
            curl: `curl -X POST ${API_BASE}/api/jobs/job:abc123/segments/reconstruct \\
  -H "X-API-Key: itk_translate_your_key_here"`,
            response: `{\n  "status": "reconstructing"\n}`,
        },
        {
            method: 'POST',
            path: '/api/import-xliff',
            desc: 'Import an externally translated XLIFF file',
            auth: 'translate',
            params: [
                { name: 'file', type: 'File', required: true, desc: 'Translated .xlf file' },
                { name: 'job_id', type: 'string', required: true, desc: 'Original job ID' }
            ],
            curl: `curl -X POST ${API_BASE}/api/import-xliff \\
  -H "X-API-Key: itk_translate_your_key_here" \\
  -F "file=@translated.xlf" \\
  -F "job_id=job:abc123"`,
            response: `{\n  "status": "success",\n  "segments_updated": 142\n}`,
        },
        {
            method: 'GET',
            path: '/api/glossary',
            desc: 'List user glossary terms',
            auth: 'read',
            params: [],
            curl: `curl ${API_BASE}/api/glossary \\
  -H "X-API-Key: itk_read_your_key_here"`,
            response: `[\n  { "id": "term:123", "source_term": "InfiTrans", "target_term": "InfiTrans", "source_lang": "en", "target_lang": "vi" }\n]`,
        },
        {
            method: 'POST',
            path: '/api/glossary/upload',
            desc: 'Upload a CSV glossary',
            auth: 'translate',
            params: [
                { name: 'file', type: 'File', required: true, desc: 'CSV file (source_lang, target_lang, source_term, target_term)' }
            ],
            curl: `curl -X POST ${API_BASE}/api/glossary/upload \\
  -H "X-API-Key: itk_translate_your_key_here" \\
  -F "file=@glossary.csv"`,
            response: `{\n  "status": "success",\n  "imported_count": 500\n}`,
        },
        {
            method: 'GET',
            path: '/api/languages',
            desc: 'List supported languages',
            auth: 'none',
            params: [],
            curl: `curl ${API_BASE}/api/languages`,
            response: `[
  { "code": "ja", "name": "Japanese", "native": "日本語" },
  { "code": "vi", "name": "Vietnamese", "native": "Tiếng Việt" },
  { "code": "en", "name": "English", "native": "English" }
]`,
        },
        {
            method: 'GET',
            path: '/api/domains',
            desc: 'List supported translation domains',
            auth: 'none',
            params: [],
            curl: `curl ${API_BASE}/api/domains`,
            response: `[
  { "code": "general", "name": "General" },
  { "code": "legal", "name": "Legal" },
  { "code": "medical", "name": "Medical" }
]`,
        },
        {
            method: 'GET',
            path: '/api/health',
            desc: 'System health check',
            auth: 'none',
            params: [],
            curl: `curl ${API_BASE}/api/health`,
            response: `{
  "status": "ok",
  "llm_backend": "ollama",
  "llm": "connected",
  "database": "connected",
  "model": "HY-MT1.5-1.8B"
}`,
        },
    ];

    function copyCode(text: string, idx: number) {
        navigator.clipboard.writeText(text);
        copiedIdx = idx;
        setTimeout(() => copiedIdx = -1, 2000);
    }

    function methodColor(m: string) {
        if (m === 'POST') return '#22c55e';
        if (m === 'GET') return '#3b82f6';
        if (m === 'DELETE') return '#ef4444';
        return '#a78bfa';
    }
</script>

<svelte:head>
    <title>API Documentation — InfiTrans</title>
    <meta name="description" content="InfiTrans API documentation for third-party integration. Translate documents programmatically." />
</svelte:head>

<div class="docs-page">
    <div class="docs-header">
        <h1>API Documentation</h1>
        <p class="docs-subtitle">Integrate InfiTrans document translation into your applications</p>
    </div>

    <!-- Quick Start -->
    <section class="docs-section" id="quickstart">
        <h2>Quick Start</h2>
        <div class="steps">
            <div class="step">
                <span class="step-num">1</span>
                <div>
                    <strong>Get an API Key</strong>
                    <p>Go to <a href="/settings">Settings → API Keys</a> and create a key with <code>translate</code> scope.</p>
                </div>
            </div>
            <div class="step">
                <span class="step-num">2</span>
                <div>
                    <strong>Upload a document</strong>
                    <p><code>POST /api/upload</code> with your file and API key.</p>
                </div>
            </div>
            <div class="step">
                <span class="step-num">3</span>
                <div>
                    <strong>Poll for status</strong>
                    <p><code>GET /api/jobs</code> until <code>status: "completed"</code>.</p>
                </div>
            </div>
            <div class="step">
                <span class="step-num">4</span>
                <div>
                    <strong>Download result</strong>
                    <p><code>GET /api/download/&#123;job_id&#125;</code> to get the translated file.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Authentication -->
    <section class="docs-section" id="auth">
        <h2>Authentication</h2>
        <p>Pass your API key via the <code>X-API-Key</code> header:</p>
        <div class="code-block">
            <pre>X-API-Key: itk_translate_your_key_here</pre>
        </div>
        <h3>Scopes</h3>
        <div class="scope-table">
            <div class="scope-row">
                <code class="scope read">read</code>
                <span>View jobs, download files, list languages/domains</span>
            </div>
            <div class="scope-row">
                <code class="scope translate">translate</code>
                <span>Everything in <code>read</code> + upload files, manage glossary</span>
            </div>
            <div class="scope-row">
                <code class="scope admin">admin</code>
                <span>Everything in <code>translate</code> + manage API keys, users</span>
            </div>
        </div>
    </section>

    <!-- Webhooks -->
    <section class="docs-section" id="webhooks">
        <h2>Webhooks</h2>
        <p>Add <code>webhook_url</code> when uploading to receive a callback when the job completes:</p>
        <div class="code-block">
            <pre>{`POST /api/upload
  -F "webhook_url=https://your-app.com/hooks/translation"`}</pre>
        </div>
        <p>InfiTrans will <code>POST</code> to your URL with:</p>
        <div class="code-block">
            <pre>{`{
  "event": "job.completed",
  "job_id": "job:abc123",
  "filename": "document.docx",
  "status": "completed",
  "download_url": "/api/download/job:abc123",
  "segments_count": 142,
  "duration_seconds": 45.2,
  "timestamp": "2026-05-01T10:30:00Z"
}`}</pre>
        </div>
        <p>Verify the <code>X-InfiTrans-Signature</code> header (HMAC-SHA256) to ensure authenticity.</p>
    </section>

    <!-- Endpoints -->
    <section class="docs-section" id="endpoints">
        <h2>Endpoints</h2>

        {#each endpoints as ep, i}
            <div class="endpoint" id={ep.path.replace(/[^a-z]/g, '-')}>
                <div class="endpoint-header">
                    <span class="method-badge" style="background: {methodColor(ep.method)}">{ep.method}</span>
                    <code class="endpoint-path">{ep.path}</code>
                    {#if ep.auth !== 'none'}
                        <span class="auth-badge">{ep.auth}</span>
                    {/if}
                </div>
                <p class="endpoint-desc">{ep.desc}</p>

                {#if ep.params.length > 0}
                    <table class="params-table">
                        <thead>
                            <tr><th>Parameter</th><th>Type</th><th>Required</th><th>Description</th></tr>
                        </thead>
                        <tbody>
                            {#each ep.params as p}
                                <tr>
                                    <td><code>{p.name}</code></td>
                                    <td>{p.type}</td>
                                    <td>{p.required ? '✓' : '—'}</td>
                                    <td>{p.desc}</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                {/if}

                <div class="code-example">
                    <div class="code-header">
                        <span>curl</span>
                        <button class="copy-btn" on:click={() => copyCode(ep.curl, i)}>
                            {copiedIdx === i ? '✓ Copied' : 'Copy'}
                        </button>
                    </div>
                    <pre>{ep.curl}</pre>
                </div>

                <div class="code-example response">
                    <div class="code-header"><span>Response</span></div>
                    <pre>{ep.response}</pre>
                </div>
            </div>
        {/each}
    </section>

    <!-- Error Codes -->
    <section class="docs-section" id="errors">
        <h2>Error Codes</h2>
        <table class="params-table">
            <thead><tr><th>Code</th><th>Meaning</th></tr></thead>
            <tbody>
                <tr><td><code>400</code></td><td>Bad request — invalid parameters</td></tr>
                <tr><td><code>401</code></td><td>Unauthorized — missing or invalid API key</td></tr>
                <tr><td><code>403</code></td><td>Forbidden — insufficient scope or registration disabled</td></tr>
                <tr><td><code>413</code></td><td>File too large (default limit: 50MB)</td></tr>
                <tr><td><code>429</code></td><td>Rate limited — too many requests or quota exceeded</td></tr>
                <tr><td><code>500</code></td><td>Internal server error</td></tr>
            </tbody>
        </table>
    </section>
</div>

<style>
    .docs-page {
        max-width: 860px;
        margin: 0 auto;
        padding: 40px 24px 80px;
        font-family: 'Inter', -apple-system, sans-serif;
    }

    .docs-header {
        margin-bottom: 40px;
    }

    .back-link {
        font-size: 0.85rem;
        color: var(--accent, #a78bfa);
        text-decoration: none;
        margin-bottom: 12px;
        display: inline-block;
    }

    .docs-header h1 {
        font-size: 2rem;
        font-weight: 800;
        color: var(--text-primary, #f4f4f5);
        margin: 8px 0 4px;
    }

    .docs-subtitle {
        color: var(--text-muted, #71717a);
        font-size: 1rem;
    }

    .docs-section {
        margin-bottom: 48px;
    }

    .docs-section h2 {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--text-primary, #f4f4f5);
        margin: 0 0 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    .docs-section h3 {
        font-size: 1.05rem;
        font-weight: 600;
        color: var(--text-primary, #f4f4f5);
        margin: 20px 0 10px;
    }

    .docs-section p {
        color: var(--text-secondary, #a1a1aa);
        font-size: 0.92rem;
        line-height: 1.6;
        margin: 0 0 12px;
    }

    /* Steps */
    .steps {
        display: grid;
        gap: 16px;
    }

    .step {
        display: flex;
        gap: 14px;
        align-items: flex-start;
        padding: 16px;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
    }

    .step-num {
        min-width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--accent, #a78bfa);
        color: #fff;
        font-size: 0.82rem;
        font-weight: 700;
        border-radius: 50%;
    }

    .step strong {
        color: var(--text-primary, #f4f4f5);
        display: block;
        margin-bottom: 2px;
    }

    .step p {
        margin: 0;
        font-size: 0.85rem;
    }

    /* Scope table */
    .scope-table { display: grid; gap: 8px; margin-top: 8px; }

    .scope-row {
        display: flex;
        gap: 12px;
        align-items: center;
        font-size: 0.88rem;
        color: var(--text-secondary, #a1a1aa);
    }

    .scope {
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .scope.read { background: rgba(59,130,246,0.15); color: #3b82f6; }
    .scope.translate { background: rgba(167,139,250,0.15); color: #a78bfa; }
    .scope.admin { background: rgba(239,68,68,0.15); color: #ef4444; }

    /* Endpoint */
    .endpoint {
        margin-bottom: 32px;
        padding: 20px;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
    }

    .endpoint-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }

    .method-badge {
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 800;
        color: #fff;
    }

    .endpoint-path {
        font-size: 0.95rem;
        color: var(--text-primary, #f4f4f5);
    }

    .auth-badge {
        font-size: 0.72rem;
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(167,139,250,0.12);
        color: #a78bfa;
        font-weight: 600;
    }

    .endpoint-desc {
        margin: 0 0 12px;
    }

    /* Tables */
    .params-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
        margin-bottom: 16px;
    }

    .params-table th {
        text-align: left;
        padding: 8px 10px;
        color: var(--text-muted, #71717a);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    .params-table td {
        padding: 8px 10px;
        color: var(--text-secondary, #a1a1aa);
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }

    .params-table code {
        font-size: 0.82rem;
        color: var(--accent, #a78bfa);
    }

    /* Code blocks */
    .code-block, .code-example {
        background: rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 12px;
    }

    .code-block pre, .code-example pre {
        padding: 14px 16px;
        margin: 0;
        font-size: 0.82rem;
        line-height: 1.5;
        color: #d4d4d8;
        overflow-x: auto;
        white-space: pre-wrap;
        word-break: break-word;
    }

    .code-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 14px;
        background: rgba(255,255,255,0.04);
        font-size: 0.75rem;
        color: var(--text-muted, #71717a);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .copy-btn {
        padding: 2px 10px;
        background: transparent;
        border: 1px solid rgba(255,255,255,0.1);
        color: var(--text-muted, #71717a);
        border-radius: 4px;
        font-size: 0.72rem;
        cursor: pointer;
        transition: all 0.15s;
    }

    .copy-btn:hover {
        background: rgba(255,255,255,0.06);
        color: var(--text-primary, #f4f4f5);
    }

    .response pre {
        color: #86efac;
    }

    code {
        font-size: 0.85em;
        background: rgba(255,255,255,0.06);
        padding: 1px 5px;
        border-radius: 3px;
        color: var(--accent, #a78bfa);
    }

    @media (max-width: 640px) {
        .docs-page { padding: 24px 16px 60px; }
        .endpoint { padding: 14px; }
    }
</style>
