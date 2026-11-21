# Phase 4 · Employment, education and household independence

Sign in on the synthetic HTTPS demo, open **Data & reports**, and replay **2026-08-31 · Work and household test month**. The test month is separate from the September and October A1 fixtures.

| Case | What to check |
| --- | --- |
| DEMO-00001 | A qualifying Sek II start and a household shared with DEMO-00002. The exported responsibility end stays the working cutoff. |
| DEMO-00002 | The work periods end 31 March and resume 2 April. The day without evidence breaks continuity. The earliest possible six-month date is 2 October if work continues. A household member joins on 1 June 2026, so the demo restarts the 12-month clock on that date. |
| DEMO-00003 | One financial support record has an unknown category. The whole household result requires review. |

## Rules used

Employment requires 60% in a single qualifying job at each point. The demo unions overlapping or adjacent qualifying intervals and ignores simultaneous jobs below the threshold rather than adding their workloads. Imported end dates are inclusive. The eligibility test uses the six-calendar-month anniversary and is capped by the report date and exported end of responsibility. A recognized Sek II or tertiary start qualifies in this version. Computed and official dates remain separate. Rows without qualifying market evidence or dates can require review.

The household is keyed by Dossier-Nr. The demo conservatively restarts the support-free period when the observed membership changes and keeps ambiguous cutoff, category or coverage in review. In the demo, **Sozialhilfe** and **Nothilfe** interrupt the period and **Keine Unterstützung** does not. An absence of support rows can only count as support-free in the synthetic profile. Real coverage needs positive verification by ASD. Conflicting exported responsibility cutoffs require review. Household results are calculated once, then shown on authorized member pages. The aggregate Excel lists each scoped household once. Person-specific official records stay on the case pages.

Reference dates are separate from operational cutoffs. The [versioned policy](../cockpit/responsibility-policy.json) records five years from asylum application for B-FL/B-RSFL/B-SL, seven years from entry for VA/F-FL, and a five-year 2027 candidate. Authorized operators can configure the transition cohort through COCKPIT_RESPONSIBILITY_POLICY. The candidate does not change attainment or the exported deadline.

ASD still needs to confirm primary-market evidence, education start versus completion, adjacency, treatment of Nothilfe, membership transitions, coverage and the 2027 cohort. The sample report was reopened independently in each language with 144 person rows and 48 distinct scoped household rows.
