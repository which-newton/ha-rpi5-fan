# Hub maintenance for ha-rpi5-fan

Hub project IDs: `rpi5-fan`.

Maintain the listed project summaries and canonical destinations when their meaning changes.

The [canonical integration guide](https://github.com/which-newton/tpdowns-hub/blob/main/docs/PROJECT-INTEGRATION.md) explains registry updates, hosted
pages, the Prado sync, verification and release. Read its current version rather
than copying a second publishing process here. A sibling checkout is normally
`/home/toby/Projects/tpdowns-hub`; use its current default branch and preserve
other work. If it is unavailable, use GitHub to prepare a hub PR.

Before completing a user-facing change:

1. Review the relevant hub entry and tools against the change. Update purpose,
   status, links, usage notes or hosted UI where they have become inaccurate.
   Internal refactors and routine fixes with no hub-visible effect can use `none`.
2. Prepare the corresponding hub change in the same work session. Preserve
   custom fields, unrelated entries, canonical source ownership and shared UI.
3. Add `Hub-Impact: update`, `Hub-PR: <exact hub PR URL>` and a concrete
   `Hub-Reason` to the source PR. Otherwise use `Hub-Impact: none` and explain
   why the existing hub remains accurate; leave Hub-PR blank.
4. Run the appropriate source and hub checks. Follow existing deployment
   authorization; do not create new credentials or publish automatically.
5. Report source/hub PRs and whether they are prepared, merged, deployed or
   live-verified. An open hub PR is a handoff, not a completed live update.

The `Hub maintenance` GitHub check fails a missing, contradictory or incomplete
assessment. It uses PR metadata only, with no checkout, secrets or network.
It cannot prove the truth of a reason or that a private companion PR is released.
Reviewers must check the linked change and live evidence. Required checks on
private repositories need GitHub Pro or higher; where unavailable, failed CI
remains visible but GitHub does not prevent an administrator from merging.
