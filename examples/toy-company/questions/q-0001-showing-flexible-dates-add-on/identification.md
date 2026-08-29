# ✅ Identification — q-0001

**Verdict:** `IDENTIFIED`

- **Treatment:** addon_shown
- **Outcome:** churn_90d
- **Graph:** addon_uptake

## Strategies

### backdoor
- Variables: `booking_value`, `lead_time_days`
- Adjust for these and the backdoor paths are blocked.
- _Unconfoundedness_: If U→{addon_shown} and U→churn_90d then P(churn_90d|addon_shown,lead_time_days,booking_value,U) = P(churn_90d|addon_shown,lead_time_days,booking_value)

### frontdoor
- Variables: `addon_purchased`
- These fully mediate the effect; estimate in two stages.
- _Full-mediation_: addon_purchased intercepts (blocks) all directed paths from addon_shown to churn_90d.
- _First-stage-unconfoundedness_: If U→{addon_shown} and U→{addon_purchased} then P(addon_purchased|addon_shown,U) = P(addon_purchased|addon_shown)
- _Second-stage-unconfoundedness_: If U→{addon_purchased} and U→churn_90d then P(churn_90d|addon_purchased, addon_shown, U) = P(churn_90d|addon_purchased, addon_shown)

### general_adjustment
- Variables: `booking_value`, `lead_time_days`
- A generalised adjustment set; equivalent to backdoor here.
- _Unconfoundedness_: If U→{addon_shown} and U→churn_90d then P(churn_90d|addon_shown,lead_time_days,booking_value,U) = P(churn_90d|addon_shown,lead_time_days,booking_value)
