# Dashboard acceptance checks

Run from the repository root after installing the dashboard requirements:

```sh
python3 -m unittest discover -s tests/dashboard -p 'test_*.py' -v
```

The suite is separate from the historical feasibility tests and does not require their ignored raw archives.

## What HTTP acceptance covers

`test_http.py` uses FastAPI's actual ASGI application and a temporary SQLite database. It exercises company/scenario editing, snapshot isolation, hiding private answers from an active learner session, message idempotency and stale-version rejection, provider failure without fake dialogue progress, restart persistence, explicit finish/export, and submission to the internal mentor review queue. It also checks bounded input, same-origin mutations, the local mentor workspace header and rejection of OpenAI mode without a configured key.

The full guided examples use the deterministic scenario provider. The HTTP suite clears `OPENAI_API_KEY`; injected failure providers never contact an external service. The checks do not make paid API calls, send messages, or modify the user's persistent database.

PDF checks in the HTTP suite cover delivery, media type and basic file structure. Visual layout and Cyrillic rendering require the separate rendered-PDF review; a `%PDF` header is not evidence of correct typography.

## Boundaries

Passing these checks does not establish OpenAI semantic reliability, unrestricted natural-language understanding, learning improvement or production security. The two workspaces belong to one local owner. `X-Workspace-Role` is a local interface boundary, not multi-user authentication. Real users and PostgreSQL are a later integration step with their own checks.
