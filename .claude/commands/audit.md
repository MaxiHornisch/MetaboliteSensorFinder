---
description: Re-derive every claim in a document from its cited artifacts and report what is unsupported.
argument-hint: "<path to dossier, report or journal entry>"
---

Run the `auditor` subagent on $ARGUMENTS.

Check bookkeeping, not science: **does the artifact actually say what the document claims it says?**

Open the underlying artifacts, not the evidence summaries — summaries are where claim drift hides.
Classify every claim `SUPPORTED` / `OVERSTATED` / `UNSUPPORTED` / `CONTRADICTED`, and verify that every
`source_date` is at or before the run cutoff.

Lead your report with the count of unsupported and contradicted claims.
A clean audit is a short report — do not pad it.
