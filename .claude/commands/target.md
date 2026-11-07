---
description: Run loop L1 on one protein - evidence, hypotheses, falsification, calibrated dossier.
argument-hint: "<uniprot-accession> [--cutoff YYYY-MM-DD] [--loop <version>]"
---

Run the target loop (`L1`) on $ARGUMENTS.

Follow [docs/03-LOOPS.md](../../docs/03-LOOPS.md) §L1 exactly. In outline:

1. Resolve the loop version (default: the incumbent in `loops/CHANGELOG.md`) and the snapshot manifest.
2. Dispatch the five evidence channels **in parallel, as separate subagents**. They must not see each other's output — independence is what the fusion step assumes.
3. Run `screener` only if `structuralist` returns a pocket verdict of `usable` or `marginal`. If `no_usable_pocket`, record that and skip the channel. **Do not dock into a model that failed the gate.**
4. `hypothesizer`, then `falsifier` on every hypothesis, bounded at 3 refinement rounds.
5. `fusion` for the calibrated probability and the abstention decision.
6. `auditor` on the dossier, then `scribe` to render it.

Stop and report when the `L1` exit condition holds:
the dossier validates, every claim traces to an evidence_id, the auditor reports zero unsupported
claims, a probability or an abstention is recorded, and "what would change our mind" names a concrete experiment.

If the honest answer is "no confident ligand", that is a successful run. Report it as such.
