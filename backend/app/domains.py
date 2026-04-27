"""Domain Registry and Profile definitions for multi-domain translation."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainProfile:
    """Configuration for a specific translation domain/industry."""

    code: str
    name: str
    persona_prompt: str
    style_rules: str
    preserve_english_terms: bool
    built_in_terms: frozenset[str] = field(default_factory=frozenset)


# Base IT terms migrated from language_detect.py
_IT_TERMS = frozenset({
    "API", "REST", "GraphQL", "SDK", "CLI", "GUI", "IDE",
    "HTTP", "HTTPS", "URL", "URI", "DNS", "IP", "TCP", "UDP", "SSH", "SSL", "TLS",
    "JSON", "XML", "YAML", "CSV", "HTML", "CSS",
    "JavaScript", "TypeScript", "Python", "Java", "Ruby", "Rust", "Go", "PHP",
    "React", "Vue", "Angular", "Next", "Nuxt", "Vite", "Webpack",
    "Node", "Deno", "Bun", "npm", "yarn", "pip",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure",
    "Linux", "macOS", "Windows", "Ubuntu", "CentOS",
    "Nginx", "Apache", "Redis", "PostgreSQL", "MySQL", "MongoDB", "SQLite",
    "Git", "GitHub", "GitLab", "CI", "CD",
    "AI", "ML", "LLM", "GPT", "BERT", "Transformer",
    "GPU", "CPU", "RAM", "SSD", "HDD",
    "Ollama", "OpenAI", "Gemma", "Llama",
    "SaaS", "PaaS", "IaaS", "IoT", "CRM", "ERP", "BI",
    "OAuth", "JWT", "SAML", "LDAP",
    "PDF", "DOCX", "XLSX", "PPTX",
    "JIRA", "Slack", "Teams", "Zoom",
})

# Medical terms that should remain in Latin/English across languages
_MEDICAL_TERMS = frozenset({
    "DNA", "RNA", "CT", "MRI", "ECG", "EEG", "ICU", "BMI",
    "HIV", "AIDS", "COVID-19", "WHO", "FDA", "EMA", "CDC",
})

# Finance acronyms
_FINANCE_TERMS = frozenset({
    "GDP", "ROI", "EBITDA", "KPI", "B2B", "B2C", "IPO", "ETF",
    "USD", "EUR", "JPY", "VND", "GBP", "SWIFT", "IBAN",
})


SUPPORTED_DOMAINS: dict[str, DomainProfile] = {
    "general": DomainProfile(
        code="general",
        name="General",
        persona_prompt="You are a professional translator.",
        style_rules="- Translate naturally and fluently\n- Use common vocabulary suitable for a general audience\n- Avoid overly complex terminology unless present in the source",
        preserve_english_terms=False,
    ),
    "it": DomainProfile(
        code="it",
        name="IT & Software",
        persona_prompt="You are an expert Technical Translator specializing in Information Technology, Software Engineering, and Computer Science.",
        style_rules="- Use precise software engineering terminology\n- NEVER translate variable names, code snippets, or configuration keys\n- Keep technical abbreviations and system architecture terms in English",
        preserve_english_terms=True,
        built_in_terms=_IT_TERMS,
    ),
    "medical": DomainProfile(
        code="medical",
        name="Medical & Healthcare",
        persona_prompt="You are an expert Medical Translator specializing in healthcare, clinical trials, and anatomical sciences.",
        style_rules="- Use strict, precise medical terminology\n- Do not creatively rephrase clinical findings or diagnoses\n- Preserve standardized Latin/English anatomical acronyms where appropriate",
        preserve_english_terms=False,
        built_in_terms=_MEDICAL_TERMS,
    ),
    "legal": DomainProfile(
        code="legal",
        name="Legal",
        persona_prompt="You are an expert Legal Translator specializing in contracts, compliance, and corporate law.",
        style_rules="- Maintain formal, authoritative legal phrasing\n- Preserve complex, long sentence structures if necessary for legal precision\n- Translate all terminology to proper legal equivalents in the target language",
        preserve_english_terms=False,
    ),
    "finance": DomainProfile(
        code="finance",
        name="Finance & Business",
        persona_prompt="You are an expert Financial Translator specializing in corporate finance, banking, and market analysis.",
        style_rules="- Use standard financial and accounting terminology\n- Ensure precise translation of numbers, currencies, and percentages\n- Maintain a professional, business-oriented tone",
        preserve_english_terms=False,
        built_in_terms=_FINANCE_TERMS,
    ),
    "marketing": DomainProfile(
        code="marketing",
        name="Marketing",
        persona_prompt="You are an expert Localization Specialist and Copywriter.",
        style_rules="- Prioritize tone, emotional impact, and natural flow over strict literal translation\n- Adapt cultural references so they resonate with the target audience\n- Keep brand names and taglines as-is unless specific translation instructions exist",
        preserve_english_terms=False,
    ),
}


def get_domain(code: str | None) -> DomainProfile:
    """Get domain profile by code, defaulting to 'general'."""
    if not code:
        return SUPPORTED_DOMAINS["general"]
    return SUPPORTED_DOMAINS.get(code.lower(), SUPPORTED_DOMAINS["general"])

def list_supported_domains() -> dict:
    """List all supported domains for API/UI consumption."""
    # We assign an icon for each domain for the UI dropdown
    icons = {
        "general": "🌍",
        "it": "💻",
        "medical": "⚕️",
        "legal": "⚖️",
        "finance": "📈",
        "marketing": "📢"
    }
    
    domains_list = [
        {
            "code": p.code,
            "name": p.name,
            "icon": icons.get(p.code, "📁")
        }
        for p in SUPPORTED_DOMAINS.values()
    ]
    return {"domains": domains_list}
