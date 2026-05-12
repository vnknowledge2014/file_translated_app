"""Model Router — select the best LLM model for a given language pair + domain.

Uses a tiered resolution strategy:
1. Exact match: MODEL_{SOURCE}_{TARGET}_{DOMAIN}  (e.g. MODEL_JA_VI_LEGAL)
2. Lang-pair match: MODEL_{SOURCE}_{TARGET}        (e.g. MODEL_JA_VI)
3. Source-lang match: MODEL_{SOURCE}                (e.g. MODEL_JA)
4. Domain match: MODEL_DOMAIN_{DOMAIN}              (e.g. MODEL_DOMAIN_MEDICAL)
5. Fallback: MODEL (default model from config)

All env var names are uppercased. Language codes with hyphens
(e.g. zh-TW) use underscores (e.g. MODEL_ZH_TW).

Usage:
    from app.llm.model_router import model_router
    model = model_router.resolve("ja", "vi", "general")
"""

from __future__ import annotations

import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


class ModelRouter:
    """Route model selection based on language pair and domain.

    Reads MODEL_* environment variables at init time and caches
    the routing table for fast lookups during translation.
    """

    def __init__(self):
        self._routes: dict[str, str] = {}
        self._load_routes()

    def _load_routes(self) -> None:
        """Scan environment for MODEL_* overrides and build routing table."""
        prefix = "MODEL_"
        for key, value in os.environ.items():
            if key.startswith(prefix) and key != "MODEL" and value.strip():
                # Normalize: MODEL_JA_VI_LEGAL -> ja_vi_legal
                route_key = key[len(prefix) :].lower()
                self._routes[route_key] = value.strip()

        if self._routes:
            logger.info(
                f"ModelRouter loaded {len(self._routes)} route(s): "
                f"{list(self._routes.keys())}"
            )
        else:
            logger.info(
                f"ModelRouter: no overrides found, using default model: {settings.MODEL}"
            )

    def _normalize_code(self, code: str) -> str:
        """Normalize language code for env var matching.

        zh-TW -> zh_tw, ja -> ja
        """
        return code.lower().replace("-", "_")

    def resolve(
        self,
        source_lang: str,
        target_lang: str,
        domain: str = "general",
    ) -> str:
        """Resolve the best model for a given translation context.

        Resolution order (first match wins):
        1. MODEL_{SOURCE}_{TARGET}_{DOMAIN}
        2. MODEL_{SOURCE}_{TARGET}
        3. MODEL_{SOURCE}
        4. MODEL_DOMAIN_{DOMAIN}
        5. settings.MODEL (global default)

        Args:
            source_lang: Source language code (e.g. "ja").
            target_lang: Target language code (e.g. "vi").
            domain: Domain code (e.g. "medical", "legal", "general").

        Returns:
            Model name string (e.g. "gemma4:e4b").
        """
        src = self._normalize_code(source_lang)
        tgt = self._normalize_code(target_lang)
        dom = domain.lower()

        # Resolution cascade
        candidates = [
            f"{src}_{tgt}_{dom}",  # MODEL_JA_VI_LEGAL
            f"{src}_{tgt}",  # MODEL_JA_VI
            f"{src}",  # MODEL_JA
            f"domain_{dom}",  # MODEL_DOMAIN_MEDICAL
        ]

        for key in candidates:
            if key in self._routes:
                model = self._routes[key]
                logger.debug(
                    f"ModelRouter: {source_lang}→{target_lang} [{domain}] "
                    f"→ {model} (matched: MODEL_{key.upper()})"
                )
                return model

        # Fallback to global default
        logger.debug(
            f"ModelRouter: {source_lang}→{target_lang} [{domain}] "
            f"→ {settings.MODEL} (default)"
        )
        return settings.MODEL

    def list_routes(self) -> dict[str, str]:
        """Return all configured model routes for debugging/API.

        Returns:
            Dict of route_key -> model_name.
        """
        return {
            **self._routes,
            "_default": settings.MODEL,
        }


# Singleton
model_router = ModelRouter()
