import os
import sys

# Add the parent directory to sys.path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

from app.languages import SUPPORTED_LANGUAGES
from app.domains import SUPPORTED_DOMAINS

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def generate():
    base_dir = os.path.join(os.path.dirname(__file__), "../backend/app/prompts")
    
    src_dir = os.path.join(base_dir, "skills/languages/source")
    tgt_dir = os.path.join(base_dir, "skills/languages/target")
    dom_dir = os.path.join(base_dir, "skills/domains")
    
    ensure_dir(src_dir)
    ensure_dir(tgt_dir)
    ensure_dir(dom_dir)

    print("Generating Domain Skill files...")
    for code, domain in SUPPORTED_DOMAINS.items():
        path = os.path.join(dom_dir, f"{code}.md")
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Domain: {domain.name}\n\n")
                f.write(f"- {domain.persona_prompt.strip()}\n")
                f.write(f"- {domain.style_rules.strip()}\n")
            print(f"  Created: {path}")

    print("Generating Source Language Skill files...")
    for lang in SUPPORTED_LANGUAGES.values():
        path = os.path.join(src_dir, f"{lang.code}.md")
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Source Language Profile: {lang.name} ({lang.code.upper()})\n\n")
                f.write(f"- Note: This is an auto-generated profile for {lang.name}.\n")
                f.write(f"- Ensure all technical terms specific to {{TARGET_LANG}} are respected.\n")
                if not lang.has_spaces:
                    f.write(f"- Note that {lang.name} does not use spaces between words. Be careful when splitting.\n")
            print(f"  Created: {path}")

    print("Generating Target Language Skill files...")
    for lang in SUPPORTED_LANGUAGES.values():
        path = os.path.join(tgt_dir, f"{lang.code}.md")
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Target Language Style Guide: {lang.name} ({lang.code.upper()})\n\n")
                f.write(f"- Translate into natural, professional {lang.name}.\n")
                if lang.has_spaces:
                    f.write(f"- Ensure proper word spacing, especially around <tagX> markers.\n")
                f.write(f"- Maintain technical consistency according to the domain.\n")
            print(f"  Created: {path}")

if __name__ == "__main__":
    generate()
    print("Matrix generation complete.")
