# Changelog

## 0.1.1 (unreleased)

- New `x402_recommend` ($0.005): name a task in plain words and get the top-k paid x402 endpoints across the
  ecosystem, ranked by relevance, 30-day on-chain buyers, recency and liveness, with risk flags. A query with
  no match (404) is not charged.
- New free `x402_recommend_preview`: the single top pick for a task.
- Sub-cent prices are shown exactly (`$0.005`, not `$0.01`).
- The wallet key is optional again in the listings, because the preview works without it.
- Core (shared with base-memecoin-guard-mcp): a hand-written input schema can replace the OpenAPI one while
  the price still comes from the live spec.

## 0.1.0 (2026-11-01)

- First release: 12 fact-check tools at $0.01 (IBAN, EU VAT, OFAC sanctions, LEI, phone, email, FX, domain,
  business days, weather, sun, Base token facts).
- x402 payments from the user's own wallet with a per-call cap and a session budget. The client pays only the
  facts402 receiving address, and never through a Permit2 approval.
