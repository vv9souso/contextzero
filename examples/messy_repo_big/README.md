# Big Messy Demo Repo

This fixture exists to show ContextZero on a repo with realistic AI-agent context debt.

Current priority: ship the public landing page patch and keep the demo honest.
Decision: docs/current_state_truth.md is the source of truth.
Decision: docs/production_deploy_current.md is the current deployment document.

What went wrong:
- agent startup files import every historical handoff
- stale docs are not clearly separated from current docs
- outdated auth, frontend, backend, and deployment plans remain in active docs
- duplicate deployment and testing rules appear in multiple places
- long patch notes mix old decisions, current decisions, support issues, and launch chores

ContextZero should recommend reading README.md and docs/current_state_truth.md first, then avoiding stale history docs unless explicitly needed.
