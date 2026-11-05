# A06: semantic response planning

A06 extends A05; the existing stage machine still owns transitions. The semantic
director enumerates current question targets with verbatim evidence and topic
IDs separately from fact selection. The engine validates that evidence, separates
historical inspection from future visit tolerance, then builds a response plan:
customer identity, speech act, targets, permitted fact IDs, ownership, uncertainties,
reaction intent and noncommitment limits. Missing inspection data is not replaced
by a waiting-time fact and never added to the authored scenario.

The actor receives the plan and customer-visible context, not company policy,
private assessments or stage flags. The verifier independently evaluates observed
ownership, relevance to every target, factual support, conversation consistency
and stage consistency. Actor self-reported fact and target IDs are not passed to
it. Local checks still reject concrete ownership inversion and the observed
historical-inspection/future-waiting substitution even if review booleans are true.

An unprovided detail permits narrow conversational uncertainty: the customer can
say they cannot confirm that detail now. It does not authorize a fictional memory,
missed inspection, date, diagnosis, document or promise. Authored unknowns preserve
their status. This deliberately distinguishes missing author data from personal
ignorance instead of altering seed facts.

Only one candidate regeneration is allowed, after semantic/local candidate or
review rejection, with fixed error type and failed check names. The second
candidate receives the same identity, targets and evidence. Network, access,
rate-limit and timeout errors are not retried. A normal turn uses 3 HTTP requests;
a reviewed rejection followed by reviewed success/failure uses at most 5. Every
initiated request is counted, including rejected attempts. No canned live answer
or unverified second candidate is substituted.

Rejection leaves the consultation messages, disclosures, stages, confirmations,
version and receipts unchanged. Operational counters and separately labelled
system issues remain. Learner mistakes (premature repairs, scheduling and guessed
prices) are valid input and should get ordinary customer hesitation, not a learner
validation error.

## Private local audit

Setting TRAINER_AUDIT_DIR enables a separate mode-0600 JSON journal per attempt:
current input, typed plan, parsed director/actor/verifier results, validation
outcomes, regeneration count and API count. It contains private dialogue and must
stay outside Git. No key, HTTP authorization header, raw provider response envelope
or upstream exception body is recorded. Rejected candidates may be inspected in
this explicit diagnostic journal, but never become consultation messages.

`/api/status` snapshots the loaded Git commit, module paths and source hashes at
startup, including the planning module, data path and audit-enabled flag. A later
checkout cannot relabel an old running process.

## Limits

Semantic planning and independent review are still model judgments. Local guards
cover unambiguous cases, not universal natural-language correctness. The temporal
cross-check currently has a small RU/DE domain vocabulary. The empty/fallback plan
path remains for older custom adapters and the 68 original contract tests; every
production engine OpenAI response uses the A06 plan. Only fresh live trials support
an acceptance claim.
