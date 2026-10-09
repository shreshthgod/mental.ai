# Support routing policy

Engineering specification, 2026-10-08. Product support categories, not diagnoses or clinical probabilities. The current evidence engine is `mental_health_screening.safety.evaluate`, policy `safety-policy-2026.10.09.6`; candidate semantic validation is outstanding. No new rule alternatives are authorized to chase consumed holdouts. Historical .5 reports remain recorded; .6 changes generic HIGH copy only, not routing/classifier mechanics. Source fingerprints distinguish uncommitted states.

| Level | Meaning | Support |
|---|---|---|
| NONE_DETECTED | No relevant concern detected by the supported assessment; never confirmed safety | Explain assessment limits; invite support if it does not reflect the disclosure |
| NEEDS_CLARIFICATION | Potential concern whose meaning is ambiguous | Direct safety question for the affected person |
| CONCERNING | Distress, passive death wishes, historical concern or self-harm concern | Trusted-person or professional support and follow-up |
| HIGH | Reliable explicit current intent or serious threat | Urgent support, ask current safety without inventing location/access/time |
| IMMEDIATE | Stated current danger or an act underway | Local emergency help and safe distance from danger |
| UNKNOWN | Insufficient information or available capability | Explicit limitation and useful generic support, never numerically below NONE_DETECTED |

Subject: self / another_person / fictional_or_quoted / unclear. Temporal context: current / recent / historical / hypothetical / unclear. Immediacy: stated / not_stated / unclear, independently derived from the text. HIGH does not establish immediacy. IMMEDIATE alone must not manufacture stated timing. Review recommended is a recommendation, never notification.

Same-disclosure clause aggregation retains unresolved evidence. It is not conversation memory, and not a universal rule that a person's assessed state can only rise. A retraction alone does not resolve explicit intent. Credible later recovery context can change present support while preserving historical facts. The single-text API has no structured multi-turn memory.

| Evidence / availability | Required fusion |
|---|---|
| Reliable explicit danger, primary Normal or unavailable | Preserve urgent evidence and raw model output; degraded optional analysis can coexist with HIGH |
| Validated semantic concern, no rule match | Consider concern/clarification under versioned validation; do not silently discard |
| Noisy legacy flag, credible benign context | Do not automatically emergency-route; raw flag remains evidence |
| Conflicting assessments | Clarify/abstain under declared capability; do not fabricate certainty |
| Unsupported language | Explicit capability limitation; reliable recognized evidence may still justify useful support |
| Semantic unavailable | Retain reliable fallback; lack of patterns alone cannot establish complete assessment |
| All safety components unavailable | UNKNOWN/unavailable; no fake negative probabilities or safe result |

Current production limitation: there is no validated semantic component. The legacy urgency model uses proxy subreddit labels and flags 67/78 seeds in the previous evidence. D-061 supersedes D-001 narrowly: unresolved learned concern can prompt clarification, never emergency by itself. Credible recognized benign context remains protected. The local MiniLM/logistic candidate was evaluated and remains disabled after misses/false escalation; see SEMANTIC-CANDIDATE.md.

Implemented execution: authenticate, validate limits, raw-text safety, optional semantic/legacy inference, fusion, response validation, bounded persistence, frontend support and owner-scoped history. Raw-text evaluation precedes lossy preprocessing with isolated component failure scopes. Optional packages and resources are loaded only when legacy analysis runs; no request downloads them.

Language detection is fallible. The function-word heuristic is not proof of English support; short German/English overlap, Hindi transliteration and code switching remain validation requirements. Accepted input does not imply understood input. Developer synthetic labels are not expert-reviewed. Independent validation is BLOCKED on reviewed data/policy and a qualified review.

Support wording reference checked 2026-10-08: [NIMH action steps](https://www.nimh.nih.gov/health/publications/5-action-steps-to-help-someone-having-thoughts-of-suicide) supports direct questions, connection with trusted people and maintaining contact. This does not validate the routing engine. No US number was added; region is unknown. The existing-app support aside now uses authoritative generic guidance. The old assumed-India primary=Anxiety resource list was removed from response handling because region is unknown; no visual styling changed.

Temporal context refers to the concern described, not the time of unrelated ordinary activity. Effective concern clauses contribute subject/time after context gates. Present intention/state is current, without implying immediate action; explicitly anchored recent/historical events retain their event time. No concern implies unclear concern-event time; fiction-only concern is hypothetical.

## Fusion amendment (D-061)

A functioning raw classifier does not establish assessment completeness. Production semantic status is disabled; assessment_scope is recognized_rules_only and supported outputs are degraded. Reliable rule HIGH/IMMEDIATE/CONCERNING/clarification survives raw failures. Resolved fiction/education/history or a named location without stated action may retain limited NONE_DETECTED. With no supported context, a flagged legacy signal prompts NEEDS_CLARIFICATION; an absent/negative flag yields UNKNOWN. Neither branch invents an emergency or safe result. Raw Normal never lowers concern. Unvalidated semantic outputs cannot contribute. Future validated structured semantic concern may contribute under the table above, without canceling reliable positive evidence.

The original regression corpus's exact NONE expectations outside this now limited capability remain diagnostic failures, not silently relabeled successes. Measure abstention and unnecessary clarification separately from urgent misses/false emergencies. Clinical/generalization validation remains blocked.

Generic HIGH may concern different kinds of danger, so it does not universally attribute self-harm to the writer. It retains urgent local/trusted-person support without promising a later country/service lookup. Another-person support addresses that person. No reviewer is notified by a review recommendation. Browser support/history consume the same authoritative snapshot; recorded context is not a new current-state assessment.
