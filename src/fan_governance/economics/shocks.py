"""Level shocks compose multiplicatively on unshocked monthly bases, never stocks.

Severity applies through duration, then declines linearly over recovery months.
Independent overlapping shocks multiply once for each affected variable. A poor
recruitment shock changes sporting value while transfer cash spending is unchanged.
"""

from fan_governance.economics.config import ShockSpec


def shock_effects(shocks: list[ShockSpec], month: int) -> dict[str, float]:
    effects = dict.fromkeys(
        (
            "matchday_revenue",
            "commercial_revenue",
            "operating_costs",
            "recruitment",
            "disposable_income",
            "renewal",
            "investor_willingness",
        ),
        1.0,
    )
    for shock in shocks:
        age = month - shock.start_month
        if age < 0:
            continue
        if age < shock.duration_months:
            intensity = shock.severity
        elif age < shock.duration_months + shock.recovery_months:
            recovery_age = age - shock.duration_months + 1
            intensity = shock.severity * (1 - recovery_age / (shock.recovery_months + 1))
        else:
            continue
        factor = 1 - intensity
        variables = {
            "revenue_loss": ("matchday_revenue", "commercial_revenue"),
            "poor_recruitment": ("recruitment",),
            "stadium_closure": ("matchday_revenue", "renewal"),
            "economic_downturn": (
                "commercial_revenue",
                "disposable_income",
                "renewal",
                "investor_willingness",
            ),
        }[shock.name]
        for variable in variables:
            effects[variable] *= factor
        if shock.name == "stadium_closure" and not shock.keep_operating_costs:
            effects["operating_costs"] *= factor
    return effects
