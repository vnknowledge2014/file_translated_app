"""Unit Tests — Model Router.

Tests the tiered model resolution strategy:
1. Exact match: MODEL_{SRC}_{TGT}_{DOMAIN}
2. Lang-pair: MODEL_{SRC}_{TGT}
3. Source-lang: MODEL_{SRC}
4. Domain: MODEL_DOMAIN_{DOMAIN}
5. Fallback: settings.MODEL
"""

import os
from unittest.mock import patch


class TestModelRouter:
    """Test ModelRouter resolution cascade."""

    def _create_router(self, env_overrides: dict | None = None):
        """Create a fresh ModelRouter with optional env overrides."""
        env = dict(os.environ)
        if env_overrides:
            env.update(env_overrides)

        with patch.dict(os.environ, env, clear=True):
            # Force reimport to pick up new env
            from importlib import reload
            import app.config

            reload(app.config)
            import app.llm.model_router as mr_mod

            reload(mr_mod)
            return mr_mod.ModelRouter()

    def test_fallback_to_default(self):
        """No MODEL_* overrides → falls back to settings.MODEL."""
        # Clean env: remove any MODEL_ prefixed vars except MODEL itself
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("MODEL_")}
        clean_env["MODEL"] = "gemma4:e4b"

        with patch.dict(os.environ, clean_env, clear=True):
            from importlib import reload
            import app.config

            reload(app.config)
            import app.llm.model_router as mr_mod

            reload(mr_mod)
            router = mr_mod.ModelRouter()

            result = router.resolve("ja", "vi", "general")
            assert result == "gemma4:e4b"

    def test_exact_pair_match(self):
        """MODEL_JA_VI should match ja→vi."""
        router = self._create_router({"MODEL_JA_VI": "gemma4:e4b-ja-vi"})
        assert router.resolve("ja", "vi") == "gemma4:e4b-ja-vi"

    def test_exact_pair_domain_match(self):
        """MODEL_JA_VI_LEGAL should match ja→vi + legal domain."""
        router = self._create_router(
            {
                "MODEL_JA_VI_LEGAL": "gemma4:31b-legal",
                "MODEL_JA_VI": "gemma4:e4b",
            }
        )
        assert router.resolve("ja", "vi", "legal") == "gemma4:31b-legal"
        # Non-legal should fall to pair match
        assert router.resolve("ja", "vi", "general") == "gemma4:e4b"

    def test_source_lang_match(self):
        """MODEL_JA should match any ja→* pair."""
        router = self._create_router({"MODEL_JA": "gemma4:ja-generic"})
        assert router.resolve("ja", "en") == "gemma4:ja-generic"
        assert router.resolve("ja", "vi") == "gemma4:ja-generic"

    def test_domain_match(self):
        """MODEL_DOMAIN_MEDICAL should match any pair with medical domain."""
        router = self._create_router({"MODEL_DOMAIN_MEDICAL": "med-model:v2"})
        assert router.resolve("en", "vi", "medical") == "med-model:v2"
        assert router.resolve("de", "fr", "medical") == "med-model:v2"

    def test_priority_order(self):
        """Exact pair+domain beats pair beats source beats domain."""
        router = self._create_router(
            {
                "MODEL_JA_VI_LEGAL": "model-exact",
                "MODEL_JA_VI": "model-pair",
                "MODEL_JA": "model-source",
                "MODEL_DOMAIN_LEGAL": "model-domain",
            }
        )
        assert router.resolve("ja", "vi", "legal") == "model-exact"
        assert router.resolve("ja", "vi", "general") == "model-pair"
        assert router.resolve("ja", "en", "general") == "model-source"
        assert router.resolve("en", "fr", "legal") == "model-domain"

    def test_hyphenated_lang_code(self):
        """zh-TW should normalize to zh_tw for matching."""
        router = self._create_router({"MODEL_ZH_TW": "zh-tw-model"})
        assert router.resolve("zh-TW", "vi") == "zh-tw-model"

    def test_list_routes(self):
        """list_routes should return all routes + _default."""
        router = self._create_router(
            {
                "MODEL_JA_VI": "model-a",
                "MODEL_DE_EN": "model-b",
            }
        )
        routes = router.list_routes()
        assert "ja_vi" in routes
        assert "de_en" in routes
        assert "_default" in routes

    def test_case_insensitive_resolution(self):
        """Resolution should be case-insensitive."""
        router = self._create_router({"MODEL_JA_VI": "test-model"})
        assert router.resolve("JA", "VI") == "test-model"
        assert router.resolve("ja", "vi") == "test-model"
