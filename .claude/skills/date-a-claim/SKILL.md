---
name: date-a-claim
description: Establish the earliest primary publication date for a scientific claim, for the DeorphBench time split. Use whenever a fact needs a source_date - during curation (L0), literature retrieval (L1), or when auditing a date. Never date a fact by database release or literature index date.
---

# Dating a claim

Getting this wrong invalidates the benchmark, and it does so in the direction that makes
results look **better** — so nothing downstream catches it.
This skill exists because the mistake is easy, the correct procedure is tedious,
and the difference is invisible in the output.

## The two wrong answers

**Database release date.** A pairing first appearing in ChEMBL v30 may have been published
years before v30 shipped. Dating by release lets post-cutoff facts into the evidence window.

**Literature index date.** An index records when *it* indexed the paper.
A verified real example: a paper published **2017-12-31** carries a Europe PMC first-index date of
**2019-03-26**. Date-filtering today's index is therefore provably not the same as querying the index
as it stood at the cutoff.

Both wrong answers are the ones the API hands you first.

## Procedure

1. **Find the record** asserting the claim, in whichever database you started from.
2. **Follow it to its primary reference.** Databases frequently cite a *review* rather than the
   original report. If the reference is a review, keep going.
3. **Resolve the publication date from Crossref**, not from the index you searched.
4. **Check for an earlier preprint** of the same work. Record both dates; use the earlier.
5. **Check for an earlier independent report** of the same claim. Priority disputes are common
   in this literature and the first report is what the time split cares about.
6. **Assign `date_confidence`:**

| Value | Criteria |
|---|---|
| `high` | Primary paper found, date unambiguous, no earlier report located after searching |
| `medium` | Primary paper found, some ambiguity about priority |
| `low` | Only a secondary source, conflicting dates, or a date that resolves only from an index field |

Headline metrics use `medium` and above. Never discard a `low` item — label it.

## Verify the filter actually applied

Some APIs **fail open**: ChEMBL accepts a malformed filter parameter, ignores it, and returns the
full unfiltered result set with HTTP 200.

So after any date-filtered query, assert `filtered_count < unfiltered_count` and record both.
**A filter that changed nothing is a failed filter, not an empty result.**

## Output

Fill the provenance block, keeping `source_date` and `retrieved` distinct — they are different facts
and conflating them is leak L1:

```yaml
provenance:
  source: europepmc
  locator: "DOI:10.xxxx/yyyy, Results, para 3"
  source_date: 2016-04-12        # the date of the FACT
  source_date_confidence: high
  retrieved: 2026-11-07T14:02:00Z  # when WE fetched it
  quote: "verbatim sentence supporting the assertion"
```

Also record, where they exist: the preprint date, the journal date, and whether an earlier
independent report was searched for and not found.
A negative claim ("no earlier report") needs a recorded search, or it is unsupported.

## When you cannot date it

Say so. Mark `date_confidence: low` with the reason, or exclude the item and record the exclusion in
`benchmarks/curation-log.md`.

Do not guess, and do not fall back to the release date "just to have something" —
an item with a wrong date is worse than no item, because it silently corrupts the split.
