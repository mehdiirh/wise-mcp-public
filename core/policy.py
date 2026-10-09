"""Reviewed public actions only. Never derive this allowlist from name prefixes."""

from types import MappingProxyType

# Explicit parameter lists also block staff-only selectors and method overrides.
READ_ACTIONS = MappingProxyType(
    {
        ("/ad/", "get_ads"): frozenset({"limit", "page", "archived", "status", "query"}),
        ("/ad/", "get_ad"): frozenset({"ad_code"}),
        ("/ad/", "ad_transactions"): frozenset({"ad_code", "limit", "page"}),
        ("/ad/", "search_location"): frozenset({"country_code", "query"}),
        ("/stats/ad/", "get_daily_ad_stats"): frozenset({"ad_code", "limit", "as_csv"}),
        ("/stats/ad/", "get_hourly_ad_stats"): frozenset({"ad_code", "limit", "as_csv"}),
        ("/stats/ad/", "get_5min_ad_stats"): frozenset({"ad_code", "limit", "as_csv"}),
        ("/stats/ad/", "get_sum_ad_stats"): frozenset({"limit"}),
        ("/stats/user/", "summary"): frozenset(),
        ("/user/", "get_me"): frozenset(),
        ("/user/", "get_user_payments"): frozenset({"payment_statuses", "limit", "page"}),
        ("/user/", "referral_stats"): frozenset(),
        ("/currency/", "get_currencies"): frozenset(),
        ("/currency/", "get_currency"): frozenset({"code"}),
        ("/payment/", "get_coins_price"): frozenset({"amount", "currencies", "deduct_balance"}),
        ("/payment/", "get_currency_restrictions"): frozenset(),
        ("/utils/ad_template/", "get"): frozenset({"text_id"}),
        ("/utils/ad_template/", "get_all"): frozenset(),
        ("/autopilot/", "get_autopilot"): frozenset({"ad_code"}),
        ("/autopilot/", "get_autopilot_events"): frozenset({"ad_code", "page", "limit"}),
        ("/i18n/", "get_languages"): frozenset(),
        ("/i18n/", "get_current_language"): frozenset(),
        ("/user/auth/", "get_geolocation"): frozenset(),
    }
)


def check_action(route: str, action: str, params: dict) -> None:
    allowed = READ_ACTIONS.get((route, action))
    if allowed is None:
        raise ValueError("Action is not on the reviewed public read-only allowlist")
    if params.keys() - allowed:
        raise ValueError("Undocumented or privileged parameters are not allowed")
