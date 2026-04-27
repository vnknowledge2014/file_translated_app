"""Prompt Router for Context Engineering Matrix.

This module dynamically assembles the "Super-Prompt" for the LLM based on:
1. Source language characteristics
2. Target language style guidelines
3. Domain terminology rules
4. File format translation rules
"""

import os
from app.languages import get_language


class PromptRouter:
    """Dynamically routes and assembles prompt matrix."""

    def __init__(self, prompts_dir: str | None = None):
        """Initialize the router with the base prompts directory."""
        if prompts_dir is None:
            self.prompts_dir = os.path.join(os.path.dirname(__file__), "../prompts")
        else:
            self.prompts_dir = prompts_dir

    def _load_prompt(self, base_category: str, category: str, name: str) -> str:
        """Load a specific markdown file from the rules or skills matrix."""
        path = os.path.join(self.prompts_dir, base_category, category, f"{name}.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def build_prompt(
        self,
        source_lang: str,
        target_lang: str,
        domain: str,
        file_type: str,
        mixed_languages: list[str] | None = None,
    ) -> str:
        """Assemble the Super-Prompt."""
        src_profile = get_language(source_lang)
        tgt_profile = get_language(target_lang)

        # 1. Base translation directive
        prompt_parts = [
            f"You are a professional translator translating from {src_profile.name} to {tgt_profile.name}.",
            "## OUTPUT FORMAT",
            "- Translate the text directly. Do not add any conversational filler, notes, or explanations.",
            "- In batch mode, segments are separated by `|||`. You MUST output the exact same number of `|||` delimiters as the input.",
        ]

        # 2. Add Domain Skill
        domain_skill = self._load_prompt("skills", "domains", domain)
        if not domain_skill:
            domain_skill = self._load_prompt("skills", "domains", "general")
        if domain_skill:
            prompt_parts.append("\n" + domain_skill)

        # 3. Add Format Rule
        # Map file types to their format rule names
        format_map = {
            "docx": "ooxml",
            "pptx": "ooxml",
            "xlsx": "ooxml",
            "txt": "plaintext",
            "md": "plaintext",
            "csv": "plaintext",
        }
        format_name = format_map.get(file_type.lower(), "plaintext")
        format_rule = self._load_prompt("rules", "formats", format_name)
        if format_rule:
            prompt_parts.append("\n" + format_rule)

        # 4. Add Source Language Quirks (Skill)
        src_skill = self._load_prompt("skills", "languages/source", source_lang.lower())
        if src_skill:
            prompt_parts.append("\n" + src_skill)

        # 5. Add Target Language Style Guide (Skill)
        tgt_skill = self._load_prompt("skills", "languages/target", target_lang.lower())
        if tgt_skill:
            prompt_parts.append("\n" + tgt_skill)

        # 6. Add Mixed Language Handling (Auto-detect integration)
        if mixed_languages:
            langs = [get_language(l).name for l in mixed_languages if l != source_lang]
            if langs:
                prompt_parts.append(
                    f"\n# Mixed Language Handling\n"
                    f"- This text may contain segments in {', '.join(langs)}."
                    f"\n- Translate the primary {src_profile.name} text to {tgt_profile.name}, but handle the mixed languages appropriately (usually by keeping them as-is if they are technical terms)."
                )

        # Combine all parts and replace template variables
        super_prompt = "\n".join(prompt_parts)
        super_prompt = super_prompt.replace("{{SOURCE_LANG}}", src_profile.name)
        super_prompt = super_prompt.replace("{{TARGET_LANG}}", tgt_profile.name)

        return super_prompt
