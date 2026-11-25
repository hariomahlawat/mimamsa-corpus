# Definition applied (H-HOLD-C13 adjudication)

> A holding is a proposition of law, or of law applied to the material facts, that the court itself states and that is necessary to its decision on an issue before it. It must be in the court's own voice, not a recital of counsel's submissions, a summary of the lower forum, or a quotation of another case unless the court adopts it as its own reasoning. Obiter remarks and pure findings of fact are not holdings. A question of law is an issue the court expressly frames for decision.

## Operating conventions used consistently across all 79 items

1. **Unit.** One `holding` row per distinct issue the court decides. Where the court restates the same proposition
   several times (for example in the reasoning and again in the conclusion), one row is coded, using the clearest
   statement in the court's own voice (normally the "we hold" / concluding statement). Restatements are not separate
   holdings (note category GRANULARITY_SPLIT where the coders split or merged differently).
2. **Question of law.** Coded only where the court itself expressly frames an issue for decision ("the question
   which arises is whether...", "the point for determination is..."). Issues implied from the reasoning, or framed
   only in counsel's submissions or the lower forum's order, are not coded.
3. **Court's voice.** Recitals of submissions (COUNSEL_VOICE), summaries of the tribunal or lower court (SCOPE),
   and quotations of precedent not adopted as the court's own reasoning (QUOTED_PRECEDENT) are excluded. A quoted
   proposition is coded only where the court expressly adopts and applies it, and then the court's own applying
   sentence is preferred as the excerpt.
4. **Necessity.** Remarks not needed for the result, including issues the court says it need not decide
   (OBITER), and pure findings of fact or appraisals of evidence with no legal proposition (FACT_FINDING) are excluded.
   Operative directions (costs, time limits for compliance, bare "petition dismissed") are not holdings.
5. **No holding.** A readable order that disposes of the matter without stating any proposition of law (for example,
   a withdrawal, an adjournment, a consent order, or a remand with no legal reasoning) gets one row with notes `NO_HOLDING`.
6. **Scope / uncodable.** UNCODABLE codes from the coding guide are used only where the guide's conditions are met;
   an armed-forces service or military-law matter is in scope even if the legal point is general service law.
7. **agrees_with.** X or Y only where my coding of the item matches that coder's set of units substantively
   (same units, same item types; minor excerpt boundary differences ignored); otherwise NEITHER.
