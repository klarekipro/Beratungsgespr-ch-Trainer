# Customer role boundary (A05)

The director receives company services and limitations for interpretation. The
customer actor and its independent verifier receive only the customer's identity,
opening, authorized facts with knowledge status, current employee utterance,
visible conversation and reaction intent. Company policy is excluded in the
engine and discarded again by the provider context allowlist. Seller claims in
conversation are attributed speech, not new customer facts.

Local reply validation runs before review, after review, and at the engine's state
boundary. It rejects concrete seller-service assertions, reversed appliance-use
questions and unsupported categorical euro-price adoption. A model's all-true
review cannot override it. Rejected turns leave messages, disclosures,
confirmations, phase, receipts and version unchanged; initiated API calls and
attempts are still counted. No canned live answer or automatic retry is used.

The `/api/status` runtime snapshot records PID, Python, module paths, actor source
hash and Git revision at startup. Checking out another revision does not update
an already running server's snapshot. This is local diagnostic provenance, not
remote attestation.

## Limits

- Local patterns cover concrete observed role violations, not all paraphrases.
  The independent model review still handles semantic grounding and can err.
- Euro-price checks do not prove arbitrary diagnosis, dates or commitments.
- A seller capability claim may be questioned, but is never added to authored
  customer facts or used to expand company policy.
- Synthetic tests establish contracts and transaction safety, not live model
  quality. Live acceptance requires fresh independent OpenAI conversations.
- Existing sessions retain their original snapshots and messages, including any
  old bad reply. They are never silently rewritten.
