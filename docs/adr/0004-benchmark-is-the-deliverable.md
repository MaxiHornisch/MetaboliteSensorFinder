# ADR-0004: The benchmark is the product; the method is the experiment

Status: accepted
Date: 2026-11-07

## Context

The obvious shape for a one-day project on orphan-protein ligands is: build a multi-agent pipeline,
run it on some orphans, present the most interesting hypothesis.

That shape has a fatal property. With no trustworthy evaluation, the output is unfalsifiable.
A ranked list of ligands looks identical whether the pipeline is sound or broken,
and a plausible mechanism written by a capable model reads like reasoning whether or not it is.
Anyone assessing such a project has to take it on trust —
and the problem we are reacting to *is* that the field has learned not to.

Meanwhile the actual gap in the field is on the evaluation side:
held-out-target splits exist, time splits do not, decoy separability is still widely ignored,
and nothing in the standard apparatus handles a language model that already knows the answer.

## Decision

`DeorphBench` is the primary deliverable. The loop is the first method evaluated against it.

Concretely, this reorders everything:

- Success criterion 1 is "the benchmark exists and is reproducible", **even if our own method performs poorly on it**.
- The evaluation document is normative and was written before the method.
- Controls run before metrics, and a control failure aborts the run.
- Rejected loop versions are recorded in the changelog with their numbers.
- An honest negative result for our method, on a benchmark others can use, is reported as a success.

## Alternatives rejected

**Method-first, evaluate later.** The default shape. Produces a demo rather than a result,
and in this area a demo is indistinguishable from a hallucination.
It also tends never to get evaluated, because by the time the evaluation is built there is a result to protect.

**Both equally.** Sounds balanced; in practice the method wins every scheduling conflict, because it is
the part that produces something to show. Declaring one primary is what makes the ordering survive a deadline.

**Use an existing benchmark.** Strongly preferred if one exists — we searched and did not find a
retrospective time-split benchmark for endogenous ligand assignment.
**This decision is explicitly reversible: finding such a benchmark is worth more to us than our own build**,
and adopting it would be a better outcome than duplicating it.

**A case study on one well-chosen orphan.** Compelling to present, and maximally exposed to
contamination and to selection of the target after seeing the answer. Rejected as a headline;
retained as an illustration once the benchmark exists.

## Consequences

**Cost — there is nothing impressive to demo.** A benchmark and a protocol are not a visualisation of a
molecule docking into a pocket. On a one-day event this is a real cost and we are paying it knowingly.

**Cost — the honest status line is "no result yet".** We would rather write that than imply more.

**Cost — we might build a benchmark that is too small to be useful**, and we will not know until `L0`
runs. That risk is named as the project's main open question rather than deferred.

**Benefit — the work survives us.** A reproducible benchmark with a frozen curation protocol is usable by
anyone, including people who think our method is wrong. A pipeline with no evaluation is usable by nobody,
including us.

**Benefit — it makes the project assessable.** Every claim we make is checkable against an artifact,
which is the only way a reader has to tell this apart from a confident-sounding pipeline.
