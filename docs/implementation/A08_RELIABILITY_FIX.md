# A08 — targeted reliability changes

Diagnosis was completed against the seven A07 private audit records before edits.
The full table, candidates, model decisions and state comparisons stay outside Git.

Confirmed mechanisms:

- Empty incoming question targets were represented as an unconstrained string
  array. Actor/Verifier mixed fact/topic IDs and customer follow-up questions with
  incoming q-IDs. Both schemas now set maxItems=0 for the empty set, enumerate the
  actual q-IDs otherwise, and describe the namespaces. Local validation still
  rejects invented IDs, omissions and duplicate IDs.
- Verifier omitted an answered but unprovided inspection date from its coverage
  array despite positive semantic flags. Prompts/field descriptions explicitly
  distinguish a bounded uncertainty answer from an authored fact. Missing coverage
  still fails; no positive boolean overrides it. Retry feedback names the actual
  target set and unknown targets, without supplying a canned reply.
- The compound appliance-type question had been merged into model/number/power.
  Explicit type questions now retain their own target and authored equipment fact;
  the existing combined goal fact is used only when its label explicitly covers
  equipment. No scenario values are edited.
- Price statements classified as `other` fell into generic clarification. A narrow
  price-discussion intent reacts to the seller's estimate without treating it as
  the customer's budget or consent. The stage machine and bounded retry stay intact.
- Verifier mistook thanks + capability questions before booking for acceptance.
  The distinction is clarified without relaxing consent or factual checks.

Local rejection remains for unambiguous premature booking/payment/repair consent,
receiver ownership inversion, service withdrawal promoted to company closure, and
unprovided inspection data promoted to personal memory. Ordinary pronouns,
negated non-consent and attributed speech remain valid. These small domain guards
are not a universal semantic proof; independent review is still required.

There is still at most one regeneration. No technical reply templates are used in
OpenAI mode. Rejection preserves consultation state; only operational counters and
separate system-error records advance. Parsed token usage and more precise local
rejection-stage diagnostics are recorded in the private audit for cost/reliability
analysis, without credentials or HTTP headers.

The operational A07 installation and port 8100 are not changed by this branch's
isolated acceptance run. Live small-set acceptance is distinct from commercial
readiness and must be assessed from the saved actual replies.

A first isolated 20-turn trial exposed two additional concrete cases. The follow-up
patch discards only out-of-turn question metadata for a valid proposal/statement;
it still rejects out-of-turn evidence for actual discovery questions. Discarded
metadata cannot grant customer facts and is recorded as plan normalization. The
second change preserves customer ownership in indirect price reports; only a
clearly attributed direct quotation may retain seller-relative appliance pronouns.
These are covered by dedicated regressions. The first trial's failed result and
all raw diagnostics remain available privately; the follow-up is assessed as a
separate, bounded acceptance run rather than overwriting the failed trial.
