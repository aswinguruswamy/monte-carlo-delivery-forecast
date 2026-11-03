"""PM-approved sentences for the AI explanation (D33.1).

Claude only picks sentence IDs. Code turns the result into a few fixed words
(`qualities`), offers only the sentences that apply, and renders the text. So
the explanation holds no number or date other than the 50%, 85% and 95% labels,
never sounds certain, and cannot state a claim that is false for this forecast.

Changing a sentence needs PM approval (D33.1).
"""

from __future__ import annotations

from mcf.result import ForecastFacts

MANDATORY = "fifty_not_certain"
WIDE_RATIO = 0.5  # (95% date - 50% date) / (50% date - day t) at or above this = wide
HIGH_BUG_SHARE = 25  # percent

BANK = {
    MANDATORY: "The 50% date is not certain: half of the simulated runs finish later.",
    "share_85": "The 85% date is a safer date to share with a sponsor.",
    "use_95": "Use the 95% date when a late finish costs a lot.",
    "simulated": "Each date comes from many simulated runs of the team's recent pace.",
    "range": "Share a range of dates, not one date.",
    "pace_assumption": "The forecast assumes that the team keeps its recent pace.",
    "spread_narrow": "The dates are close together, so the recent pace was steady.",
    "spread_wide": "The dates are far apart, so the recent pace changed a lot from day to day.",
    "velocity_before_50": (
        "The velocity date comes before the 50% date, so the velocity forecast looks hopeful."
    ),
    "velocity_50_85": "The velocity date falls between the 50% date and the 85% date.",
    "velocity_85_95": "The velocity date falls between the 85% date and the 95% date.",
    "velocity_after_95": (
        "The velocity date comes after the 95% date, so the velocity forecast looks cautious."
    ),
    "points_estimated": "The velocity date uses an estimate of the backlog points.",
    "open_items": "Open items in the file were not counted as done.",
    "bugs_high": (
        "Bugs took a large share of the recent work, and bugs do not count as value items."
    ),
}

# Which quality value each conditional sentence needs.
CONDITIONS = {
    "spread_narrow": ("spread", "narrow"),
    "spread_wide": ("spread", "wide"),
    "velocity_before_50": ("velocity", "before 50"),
    "velocity_50_85": ("velocity", "between 50 and 85"),
    "velocity_85_95": ("velocity", "between 85 and 95"),
    "velocity_after_95": ("velocity", "after 95"),
    "points_estimated": ("points", "estimated"),
    "open_items": ("open_items", "some"),
    "bugs_high": ("bugs", "high"),
}


def qualities(facts: ForecastFacts) -> dict[str, str]:
    """Turn the result into fixed words. No number leaves this function."""
    lead = (facts.mc50 - facts.t).days
    spread = (facts.mc95 - facts.mc50).days
    v = facts.velocity_date
    if v < facts.mc50:
        velocity = "before 50"
    elif v <= facts.mc85:
        velocity = "between 50 and 85"
    elif v <= facts.mc95:
        velocity = "between 85 and 95"
    else:
        velocity = "after 95"
    if facts.bug_share_percent is None:
        bugs = "none"
    else:
        bugs = "high" if facts.bug_share_percent >= HIGH_BUG_SHARE else "low"
    return {
        "spread": "wide" if lead > 0 and spread / lead >= WIDE_RATIO else "narrow",
        "velocity": velocity,
        "points": "estimated" if facts.points_estimated else "given",
        "open_items": "some" if facts.open_items > 0 else "none",
        "bugs": bugs,
    }


def applicable_ids(facts: ForecastFacts) -> list[str]:
    q = qualities(facts)
    return [
        sid for sid in BANK if sid not in CONDITIONS or q[CONDITIONS[sid][0]] == CONDITIONS[sid][1]
    ]
