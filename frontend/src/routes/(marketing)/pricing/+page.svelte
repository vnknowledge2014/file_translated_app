<script lang="ts">
	import * as m from '$lib/paraglide/messages';
	import IconChevronRight from '$lib/components/icons/IconChevronRight.svelte';
	import IconCheckCircle from '$lib/components/icons/IconCheckCircle.svelte';
	import { isAuthenticated } from '$lib/stores/auth';

	const plans = [
		{
			get name() { return m.pricing_free_name(); },
			price: '$0',
			get period() { return m.pricing_free_period(); },
			get desc() { return m.pricing_free_desc(); },
			badge: '',
			get features() { return [m.pricing_f_free_1(), m.pricing_f_free_2(), m.pricing_f_free_3(), m.pricing_f_free_4(), m.pricing_f_free_5()]; },
			get cta() { return m.pricing_free_cta(); },
			ctaLink: '/login',
			highlight: false,
		},
		{
			get name() { return m.pricing_pro_name(); },
			price: '$29',
			get period() { return m.pricing_pro_period(); },
			get desc() { return m.pricing_pro_desc(); },
			get badge() { return m.pricing_pro_badge(); },
			get features() { return [m.pricing_f_pro_1(), m.pricing_f_pro_2(), m.pricing_f_pro_3(), m.pricing_f_pro_4(), m.pricing_f_pro_5(), m.pricing_f_pro_6(), m.pricing_f_pro_7()]; },
			get cta() { return m.pricing_pro_cta(); },
			ctaLink: '/login',
			highlight: true,
		},
		{
			get name() { return m.pricing_ent_name(); },
			price: '$99',
			get period() { return m.pricing_ent_period(); },
			get desc() { return m.pricing_ent_desc(); },
			badge: '',
			get features() { return [m.pricing_f_ent_1(), m.pricing_f_ent_2(), m.pricing_f_ent_3(), m.pricing_f_ent_4(), m.pricing_f_ent_5(), m.pricing_f_ent_6(), m.pricing_f_ent_7(), m.pricing_f_ent_8()]; },
			get cta() { return m.pricing_ent_cta(); },
			ctaLink: '/login',
			highlight: false,
		},
	];

	const paymentMethods = [
		{ name: 'USDT', icon: '₮' },
		{ name: 'USDC', icon: '$' },
	];

	const faqs = [
		{ get q() { return m.pricing_faq_q1(); }, get a() { return m.pricing_faq_a1(); } },
		{ get q() { return m.pricing_faq_q2(); }, get a() { return m.pricing_faq_a2(); } },
		{ get q() { return m.pricing_faq_q3(); }, get a() { return m.pricing_faq_a3(); } },
		{ get q() { return m.pricing_faq_q4(); }, get a() { return m.pricing_faq_a4(); } },
		{ get q() { return m.pricing_faq_q5(); }, get a() { return m.pricing_faq_a5(); } },
	];
</script>

<svelte:head>
	<title>Pricing — InfiTrans</title>
	<meta name="description" content="Simple, transparent pricing for AI-powered document translation. Start free, scale as you grow." />
</svelte:head>

<section class="pricing-hero">
	<div class="hero-inner">
		<span class="section-label">{m.pricing_label()}</span>
		<h1>{m.pricing_title()}</h1>
		<p class="hero-sub">{m.pricing_subtitle()}</p>
	</div>
</section>

<section class="plans-section">
	<div class="plans-grid">
		{#each plans as plan}
			<div class="plan-card" class:highlight={plan.highlight}>
				{#if plan.badge}
					<span class="plan-badge">{plan.badge}</span>
				{/if}
				<h3>{plan.name}</h3>
				<div class="price-row">
					<span class="price">{plan.price}</span>
					<span class="period">{plan.period}</span>
				</div>
				<p class="plan-desc">{plan.desc}</p>
				<a href={plan.ctaLink} class="plan-cta" class:primary={plan.highlight}>
					{plan.cta}
					<IconChevronRight size={16} />
				</a>
				<ul class="features-list">
					{#each plan.features as f}
						<li>
							<IconCheckCircle size={16} color={plan.highlight ? 'var(--accent)' : 'var(--text-muted)'} />
							<span>{f}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/each}
	</div>
</section>

<section class="payment-methods">
	<div class="section-inner">
		<span class="section-label">{m.pricing_payment_label()}</span>
		<h2>{m.pricing_payment_title()}</h2>
		<div class="methods-row">
			<div class="method-card">
				<div class="method-icon crypto">◎</div>
				<h4>{m.pricing_payment_crypto_title()}</h4>
				<p>{m.pricing_payment_crypto_desc()}</p>
			</div>
			<div class="method-card">
				<div class="method-icon phantom">👻</div>
				<h4>{m.pricing_payment_phantom_title()}</h4>
				<p>{m.pricing_payment_phantom_desc()}</p>
			</div>
		</div>
	</div>
</section>

<section class="faq-section">
	<div class="section-inner">
		<span class="section-label">{m.pricing_faq_label()}</span>
		<h2>{m.pricing_faq_title()}</h2>
		<div class="faq-grid">
			{#each faqs as faq}
				<div class="faq-item">
					<h4>{faq.q}</h4>
					<p>{faq.a}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<section class="cta-bottom">
	<div class="section-inner">
		<h2>{m.pricing_cta_title()}</h2>
		<p>{m.pricing_cta_desc()}</p>
		<div class="cta-actions">
			{#if $isAuthenticated}
				<a href="/translate" class="btn-primary btn-lg">
					Dashboard
					<IconChevronRight size={20} />
				</a>
			{:else}
				<a href="/login" class="btn-primary btn-lg">
					{m.pricing_cta_button()}
					<IconChevronRight size={20} />
				</a>
			{/if}
			<a href="/api-docs" class="btn-secondary">{m.hero_cta_secondary()}</a>
		</div>
	</div>
</section>

<style>
	.pricing-hero {
		text-align: center;
		padding: 80px 24px 40px;
	}

	.hero-inner { max-width: 600px; margin: 0 auto; }

	.section-label {
		display: inline-block;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--accent);
		margin-bottom: 16px;
	}

	h1 {
		font-size: 3rem;
		font-weight: 800;
		letter-spacing: -0.04em;
		color: var(--text-primary);
		margin: 0 0 16px;
	}

	.hero-sub {
		font-size: 1.15rem;
		color: var(--text-secondary);
		line-height: 1.7;
	}

	/* Plans Grid */
	.plans-section {
		padding: 20px 24px 80px;
	}

	.plans-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 24px;
		max-width: 1100px;
		margin: 0 auto;
	}

	.plan-card {
		position: relative;
		padding: 36px 28px;
		background: var(--bg-secondary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-lg);
		transition: all 0.3s ease;
	}

	.plan-card:hover {
		border-color: var(--border);
		transform: translateY(-4px);
	}

	.plan-card.highlight {
		border-color: var(--accent);
		background: linear-gradient(180deg, rgba(20,184,166,0.06) 0%, var(--bg-secondary) 40%);
		box-shadow: 0 0 40px rgba(20,184,166,0.08);
	}

	.plan-badge {
		position: absolute;
		top: -12px;
		left: 50%;
		transform: translateX(-50%);
		padding: 4px 16px;
		background: var(--accent);
		color: #fff;
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		border-radius: 100px;
		white-space: nowrap;
	}

	.plan-card h3 {
		font-size: 1.2rem;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 16px;
	}

	.price-row {
		display: flex;
		align-items: baseline;
		gap: 4px;
		margin-bottom: 8px;
	}

	.price {
		font-size: 3rem;
		font-weight: 800;
		color: var(--text-primary);
		letter-spacing: -0.04em;
		line-height: 1;
	}

	.period {
		font-size: 0.9rem;
		color: var(--text-muted);
	}

	.plan-desc {
		font-size: 0.85rem;
		color: var(--text-secondary);
		margin: 0 0 24px;
		line-height: 1.5;
	}

	.plan-cta {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		width: 100%;
		padding: 12px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-secondary);
		text-decoration: none;
		font-weight: 600;
		font-size: 0.9rem;
		transition: all 0.2s;
		margin-bottom: 24px;
	}

	.plan-cta:hover {
		border-color: var(--text-muted);
		color: var(--text-primary);
	}

	.plan-cta.primary {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
	}

	.plan-cta.primary:hover {
		background: var(--accent-hover);
		transform: translateY(-1px);
		box-shadow: var(--accent-glow);
	}

	.features-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.features-list li {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 0.85rem;
		color: var(--text-secondary);
	}

	/* Payment Methods */
	.payment-methods {
		padding: 80px 24px;
		background: var(--bg-secondary);
	}

	.section-inner {
		max-width: 900px;
		margin: 0 auto;
		text-align: center;
	}

	.section-inner h2 {
		font-size: 2rem;
		font-weight: 700;
		letter-spacing: -0.02em;
		color: var(--text-primary);
		margin: 0 0 48px;
	}

	.methods-row {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 20px;
	}

	.method-card {
		padding: 28px;
		background: var(--bg-primary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
		transition: all 0.3s;
	}

	.method-card:hover {
		border-color: var(--border);
		transform: translateY(-2px);
	}

	.method-icon {
		font-size: 2rem;
		margin-bottom: 12px;
	}

	.method-icon.crypto { color: #26a17b; }
	.method-icon.phantom { color: #ab9ff2; }

	.method-card h4 {
		font-size: 1rem;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 6px;
	}

	.method-card p {
		font-size: 0.82rem;
		color: var(--text-muted);
		margin: 0;
	}

	/* FAQ */
	.faq-section {
		padding: 80px 24px;
	}

	.faq-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 20px;
		text-align: left;
	}

	.faq-item {
		padding: 24px;
		background: var(--bg-secondary);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius);
	}

	.faq-item h4 {
		font-size: 0.95rem;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 8px;
	}

	.faq-item p {
		font-size: 0.85rem;
		color: var(--text-secondary);
		margin: 0;
		line-height: 1.6;
	}

	/* CTA Bottom */
	.cta-bottom {
		padding: 80px 24px;
		background: var(--bg-secondary);
		text-align: center;
		border-top: 1px solid var(--border-subtle);
	}

	.cta-bottom h2 {
		font-size: 2rem;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0 0 12px;
	}

	.cta-bottom p {
		font-size: 1rem;
		color: var(--text-secondary);
		margin: 0 0 32px;
	}

	.cta-actions {
		display: flex;
		gap: 16px;
		justify-content: center;
	}

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
		transition: all 0.2s;
	}

	.btn-primary:hover {
		background: var(--accent-hover);
		transform: translateY(-2px);
		box-shadow: var(--accent-glow);
	}

	.btn-lg { padding: 16px 36px; font-size: 1.05rem; }

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
		transition: all 0.2s;
	}

	.btn-secondary:hover {
		border-color: var(--text-muted);
		color: var(--text-primary);
	}

	@media (max-width: 768px) {
		h1 { font-size: 2.25rem; }
		.plans-grid { grid-template-columns: 1fr; max-width: 400px; }
		.methods-row { grid-template-columns: 1fr; }
		.faq-grid { grid-template-columns: 1fr; }
		.cta-actions { flex-direction: column; align-items: center; }
	}
</style>
