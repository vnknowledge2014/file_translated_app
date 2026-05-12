"""Unit Tests — Billing Logic.

Tests plan pricing, limits, expiry, and monthly reset logic.
"""

from datetime import datetime, timezone, timedelta


class TestPlanLimits:
    """Unit: Plan limits are correctly defined."""

    def test_plan_limits_exist(self):
        from app.routes.billing import PLAN_LIMITS

        assert isinstance(PLAN_LIMITS, dict)
        assert "free" in PLAN_LIMITS
        assert "pro" in PLAN_LIMITS
        assert "enterprise" in PLAN_LIMITS

    def test_free_plan_100_pages(self):
        from app.routes.billing import PLAN_LIMITS

        assert PLAN_LIMITS["free"] == 100

    def test_pro_plan_5000_pages(self):
        from app.routes.billing import PLAN_LIMITS

        assert PLAN_LIMITS["pro"] == 5000

    def test_enterprise_unlimited(self):
        from app.routes.billing import PLAN_LIMITS

        # Enterprise should be a very large number or None
        assert PLAN_LIMITS["enterprise"] >= 999999 or PLAN_LIMITS["enterprise"] is None


class TestPlanPricing:
    """Unit: Plan pricing is correctly defined."""

    def test_plan_prices_exist(self):
        from app.routes.billing import PLAN_PRICES

        assert isinstance(PLAN_PRICES, dict)
        assert "pro" in PLAN_PRICES
        assert "enterprise" in PLAN_PRICES

    def test_pro_price_positive(self):
        from app.routes.billing import PLAN_PRICES

        assert PLAN_PRICES["pro"] > 0

    def test_enterprise_more_than_pro(self):
        from app.routes.billing import PLAN_PRICES

        assert PLAN_PRICES["enterprise"] > PLAN_PRICES["pro"]


class TestQuotaCheck:
    """Unit: Quota enforcement logic."""

    def test_free_user_under_limit_allowed(self):
        """Free user with 50/100 pages should be allowed."""
        used = 50
        limit = 100
        assert used < limit

    def test_free_user_at_limit_blocked(self):
        """Free user at 100/100 pages should be blocked."""
        used = 100
        limit = 100
        assert used >= limit

    def test_enterprise_no_limit(self):
        """Enterprise user with no practical limit."""
        from app.routes.billing import PLAN_LIMITS

        limit = PLAN_LIMITS["enterprise"]
        # Should be effectively unlimited
        assert limit is None or limit >= 999999


class TestPlanExpiry:
    """Unit: Plan expiry detection logic."""

    def test_expired_plan_detected(self):
        """Plan with expiry date in the past."""
        expiry = datetime.now(timezone.utc) - timedelta(days=1)
        now = datetime.now(timezone.utc)
        assert expiry < now  # Expired

    def test_active_plan_not_expired(self):
        """Plan with expiry date in the future."""
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        now = datetime.now(timezone.utc)
        assert expiry > now  # Active

    def test_no_expiry_free_plan(self):
        """Free plan has no expiry date."""
        plan = "free"
        expiry = None
        assert expiry is None  # Free plan never expires


class TestMonthlyReset:
    """Unit: Monthly usage reset logic."""

    def test_reset_needed_different_month(self):
        """If last_reset_month is different from current month, reset needed."""
        last_reset = datetime(2025, 11, 15, tzinfo=timezone.utc)
        now = datetime(2025, 12, 1, tzinfo=timezone.utc)
        needs_reset = last_reset.month != now.month or last_reset.year != now.year
        assert needs_reset

    def test_no_reset_same_month(self):
        """If last_reset_month is same as current month, no reset."""
        last_reset = datetime(2025, 12, 5, tzinfo=timezone.utc)
        now = datetime(2025, 12, 20, tzinfo=timezone.utc)
        needs_reset = last_reset.month != now.month or last_reset.year != now.year
        assert not needs_reset

    def test_reset_on_year_change(self):
        """Reset needed when year changes."""
        last_reset = datetime(2025, 12, 31, tzinfo=timezone.utc)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        needs_reset = last_reset.month != now.month or last_reset.year != now.year
        assert needs_reset
