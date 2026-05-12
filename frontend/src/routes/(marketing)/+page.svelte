<script lang="ts">
	import * as m from '$lib/paraglide/messages';
	import IconUpload from '$lib/components/icons/IconUpload.svelte';
	import IconLanguages from '$lib/components/icons/IconLanguages.svelte';
	import IconEdit from '$lib/components/icons/IconEdit.svelte';
	import IconFile from '$lib/components/icons/IconFile.svelte';
	import IconCheckCircle from '$lib/components/icons/IconCheckCircle.svelte';
	import IconDownload from '$lib/components/icons/IconDownload.svelte';
	import IconChevronRight from '$lib/components/icons/IconChevronRight.svelte';
	import IconGlobe from '$lib/components/icons/IconGlobe.svelte';
	import IconChart from '$lib/components/icons/IconChart.svelte';
	import IconSearch from '$lib/components/icons/IconSearch.svelte';
	import { isAuthenticated } from '$lib/stores/auth';

	const features = [
		{
			icon: IconLanguages,
			get title() { return m.feature_ai_title(); },
			get desc() { return m.feature_ai_desc(); }
		},
		{
			icon: IconFile,
			get title() { return m.feature_format_title(); },
			get desc() { return m.feature_format_desc(); }
		},
		{
			icon: IconEdit,
			get title() { return m.feature_editor_title(); },
			get desc() { return m.feature_editor_desc(); }
		},
		{
			icon: IconGlobe,
			get title() { return m.feature_multilang_title(); },
			get desc() { return m.feature_multilang_desc(); }
		},
		{
			icon: IconChart,
			get title() { return m.feature_quality_title(); },
			get desc() { return m.feature_quality_desc(); }
		},
		{
			icon: IconSearch,
			get title() { return m.feature_glossary_title(); },
			get desc() { return m.feature_glossary_desc(); }
		}
	];

	const steps = [
		{ num: '01', get title() { return m.workflow_step1_title(); }, get desc() { return m.workflow_step1_desc(); } },
		{ num: '02', get title() { return m.workflow_step2_title(); }, get desc() { return m.workflow_step2_desc(); } },
		{ num: '03', get title() { return m.workflow_step3_title(); }, get desc() { return m.workflow_step3_desc(); } }
	];

	const formats = ['DOCX', 'XLSX', 'PPTX', 'PDF', 'CSV', 'TXT', 'MD'];
</script>

<svelte:head>
	<script type="application/ld+json">
		{JSON.stringify({
			"@context": "https://schema.org",
			"@type": "SoftwareApplication",
			"name": "InfiTrans",
			"applicationCategory": "BusinessApplication",
			"description": "AI-powered document translation platform supporting DOCX, XLSX, PPTX with formatting preservation.",
			"operatingSystem": "Web",
			"offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
			"author": { "@type": "Organization", "name": "Infinite Agent Lab" }
		})}
	</script>
</svelte:head>

<!-- Hero -->
<section class="hero">
	<div class="hero-inner">
		<div class="hero-badge">
			<span class="badge-dot"></span>
			{m.hero_badge()}
		</div>
		<h1>
			{m.hero_title_1()}<br/>
			<span class="gradient-text">{m.hero_title_2()}</span>
		</h1>
		<p class="hero-sub">
			{m.hero_subtitle()}
		</p>
		<div class="hero-actions">
			{#if $isAuthenticated}
				<a href="/translate" class="btn-primary">
					Dashboard
					<IconChevronRight size={18} />
				</a>
			{:else}
				<a href="/login" class="btn-primary">
					{m.hero_cta()}
					<IconChevronRight size={18} />
				</a>
			{/if}
			<a href="/api-docs" class="btn-secondary">{m.hero_cta_secondary()}</a>
		</div>
		<p class="hero-note">{m.hero_note()}</p>
	</div>
</section>

<!-- Features -->
<section id="features" class="section">
	<div class="section-inner">
		<span class="section-label">{m.features_label()}</span>
		<h2>{m.features_title()}</h2>
		<div class="features-grid">
			{#each features as f}
				<div class="feature-card">
					<div class="feature-icon">
						<svelte:component this={f.icon} size={24} color="var(--accent)" />
					</div>
					<h3>{f.title}</h3>
					<p>{f.desc}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- How it Works -->
<section id="how-it-works" class="section section-alt">
	<div class="section-inner">
		<span class="section-label">{m.workflow_label()}</span>
		<h2>{m.workflow_title()}</h2>
		<div class="steps-row">
			{#each steps as step, i}
				<div class="step-card">
					<span class="step-num">{step.num}</span>
					<h3>{step.title}</h3>
					<p>{step.desc}</p>
				</div>
				{#if i < steps.length - 1}
					<div class="step-arrow">
						<IconChevronRight size={24} color="var(--text-muted)" />
					</div>
				{/if}
			{/each}
		</div>
	</div>
</section>

<!-- Supported Formats -->
<section id="formats" class="section">
	<div class="section-inner">
		<span class="section-label">{m.formats_label()}</span>
		<h2>{m.formats_title()}</h2>
		<div class="formats-grid">
			{#each formats as fmt}
				<div class="format-badge">{fmt}</div>
			{/each}
		</div>
	</div>
</section>

<!-- CTA -->
<section class="cta-section">
	<div class="section-inner">
		<h2>{m.cta_title()}</h2>
		<p>{m.cta_desc()}</p>
		{#if $isAuthenticated}
			<a href="/translate" class="btn-primary btn-lg">
				Dashboard
				<IconChevronRight size={20} />
			</a>
		{:else}
			<a href="/login" class="btn-primary btn-lg">
				{m.cta_button()}
				<IconChevronRight size={20} />
			</a>
		{/if}
	</div>
</section>

<style>
	/* ── Hero ── */
	.hero {
		min-height: 85vh;
		display: flex;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: 80px 24px 60px;
		position: relative;
		overflow: hidden;
	}

	.hero::before {
		content: '';
		position: absolute;
		top: -200px;
		left: 50%;
		transform: translateX(-50%);
		width: 800px;
		height: 600px;
		background: radial-gradient(ellipse, rgba(20, 184, 166, 0.08), transparent 70%);
		pointer-events: none;
	}

	.hero-inner {
		max-width: 720px;
		position: relative;
		z-index: 1;
	}

	.hero-badge {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 6px 16px;
		border: 1px solid rgba(20, 184, 166, 0.3);
		background: rgba(20, 184, 166, 0.08);
		border-radius: 100px;
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--accent);
		margin-bottom: 32px;
		letter-spacing: 0.05em;
		text-transform: uppercase;
	}

	.badge-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--accent);
		animation: pulse 2s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.4; }
	}

	h1 {
		font-size: 3.5rem;
		font-weight: 800;
		letter-spacing: -0.04em;
		line-height: 1.05;
		margin-bottom: 24px;
		color: var(--text-primary);
	}

	.gradient-text {
		background: linear-gradient(135deg, var(--accent), var(--accent-hover));
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.hero-sub {
		font-size: 1.15rem;
		color: var(--text-secondary);
		max-width: 560px;
		margin: 0 auto 40px;
		line-height: 1.7;
	}

	.hero-actions {
		display: flex;
		gap: 16px;
		justify-content: center;
		flex-wrap: wrap;
	}

	.hero-note {
		margin-top: 20px;
		font-size: 0.8rem;
		color: var(--text-muted);
	}

	/* ── Buttons ── */
	.btn-primary {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 14px 28px;
		background: var(--accent);
		color: #fff;
		border-radius: var(--radius-sm);
		text-decoration: none;
		font-weight: 600;
		font-size: 0.95rem;
		transition: all var(--transition-base);
		border: none;
		cursor: pointer;
	}

	.btn-primary:hover {
		background: var(--accent-hover);
		transform: translateY(-2px);
		box-shadow: var(--accent-glow);
	}

	.btn-lg {
		padding: 16px 36px;
		font-size: 1.05rem;
	}

	.btn-secondary {
		display: inline-flex;
		align-items: center;
		padding: 14px 28px;
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		text-decoration: none;
		font-weight: 500;
		font-size: 0.95rem;
		transition: all var(--transition-base);
	}

	.btn-secondary:hover {
		border-color: var(--text-muted);
		color: var(--text-primary);
	}

	/* ── Sections ── */
	.section {
		padding: 100px 24px;
	}

	.section-alt {
		background: var(--bg-secondary);
	}

	.section-inner {
		max-width: var(--max-width);
		margin: 0 auto;
		text-align: center;
	}

	.section-label {
		display: inline-block;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--accent);
		margin-bottom: 16px;
	}

	.section-inner h2 {
		font-size: 2.25rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		margin-bottom: 60px;
		color: var(--text-primary);
	}

	/* ── Features Grid ── */
	.features-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 24px;
		text-align: left;
	}

	.feature-card {
		padding: 32px;
		background: var(--bg-secondary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		transition: all var(--transition-slow);
	}

	.section-alt .feature-card {
		background: var(--bg-primary);
	}

	.feature-card:hover {
		border-color: var(--border);
		transform: translateY(-4px);
	}

	.feature-icon {
		width: 48px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--accent-muted);
		border-radius: 10px;
		margin-bottom: 20px;
	}

	.feature-card h3 {
		font-size: 1.05rem;
		font-weight: 600;
		margin-bottom: 10px;
		color: var(--text-primary);
	}

	.feature-card p {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.6;
	}

	/* ── Steps ── */
	.steps-row {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 24px;
	}

	.step-card {
		flex: 1;
		max-width: 280px;
		padding: 40px 32px;
		background: var(--bg-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		text-align: left;
	}

	.step-num {
		display: inline-block;
		font-size: 2rem;
		font-weight: 800;
		color: var(--accent);
		font-variant-numeric: tabular-nums;
		margin-bottom: 16px;
		opacity: 0.6;
	}

	.step-card h3 {
		font-size: 1.15rem;
		font-weight: 600;
		margin-bottom: 10px;
		color: var(--text-primary);
	}

	.step-card p {
		font-size: 0.875rem;
		color: var(--text-secondary);
		line-height: 1.6;
	}

	.step-arrow {
		flex-shrink: 0;
		opacity: 0.4;
	}

	/* ── Formats ── */
	.formats-grid {
		display: flex;
		gap: 12px;
		justify-content: center;
		flex-wrap: wrap;
	}

	.format-badge {
		padding: 10px 24px;
		background: var(--bg-secondary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-sm);
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-secondary);
		font-family: var(--font-mono);
		letter-spacing: 0.04em;
		transition: all var(--transition-base);
	}

	.format-badge:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	/* ── CTA ── */
	.cta-section {
		padding: 100px 24px;
		text-align: center;
		background: var(--bg-secondary);
		border-top: 1px solid var(--border-subtle);
	}

	.cta-section h2 {
		font-size: 2.25rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		margin-bottom: 16px;
	}

	.cta-section p {
		font-size: 1.05rem;
		color: var(--text-secondary);
		margin-bottom: 40px;
	}

	/* ── Responsive ── */
	@media (max-width: 768px) {
		h1 { font-size: 2.25rem; }
		.hero { min-height: 70vh; padding: 60px 20px 40px; }
		.hero-sub { font-size: 1rem; }
		.section { padding: 60px 20px; }
		.section-inner h2 { font-size: 1.75rem; margin-bottom: 40px; }
		.features-grid { grid-template-columns: 1fr; }
		.steps-row { flex-direction: column; }
		.step-arrow { transform: rotate(90deg); }
		.cta-section h2 { font-size: 1.75rem; }
	}
</style>
