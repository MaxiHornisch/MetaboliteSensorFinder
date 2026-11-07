"""The full simulated chain: bindPredict -> PSICHIC -> DiffDock -> evidence -> hypotheses ->
falsifier (scripted part) -> calibration with abstention -> dossiers -> controls.

Everything here is SIMULATION with planted truth. Records carry `simulated-` in their source
names. Nothing in this module is evidence about a real protein.

Agents then evaluate the stored artifacts (falsifier, auditor, statistician, scribe), reading
only the run directory. See docs/13 §1.1 and docs/14 §4.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sklearn.linear_model import LogisticRegression

from msf.screen.diffdock_sim import SimulatedDiffDock
from msf.screen.ingest import Row
from msf.screen.runner import Item, Thresholds, read_scores, run_stage, wire_id
from msf.screen.simulate import SimulatedWorker, _u, planted_truth

LOOP_VERSION = "screen-sim-0.1"
SNAPSHOT = "sim-snapshot-v1"
P_ACCEPT = 0.5  # pre-registered acceptance probability; set here, not tuned on the data
SIM_THRESHOLDS = Thresholds(
    calibrated=True,
    cuts={"bindpredict": 0.5, "psichic": 0.5, "diffdock": 0.0},
    source="simulation: planted-truth cuts, not fitted on real data",
)
METHANE = {"ligand_id": "CH4-CONTROL", "inchikey": "VNWKTOKETHGBQD-UHFFFAOYSA-N",
           "heavy_atoms": 1, "control": "methane"}


def library(seed: str, n: int = 40) -> list[dict]:
    """Synthetic ligand library. Methane is appended as the negative control (docs/11 §2)."""
    lig = [{"ligand_id": f"SIM-L{i:02d}",
            "inchikey": "SIMULATED-" + hashlib.sha256(f"{seed}|lig|{i}".encode()).hexdigest()[:14],
            "heavy_atoms": 12 + int(_u(seed + "|ha", str(i)) * 30)} for i in range(n)]
    return lig + [METHANE]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ece(probs: list[float], labels: list[int], bins: int = 10) -> float:
    if not probs:
        return float("nan")
    total = 0.0
    for b in range(bins):
        idx = [i for i, p in enumerate(probs) if b / bins <= p < (b + 1) / bins or
               (b == bins - 1 and p == 1.0)]
        if idx:
            conf = sum(probs[i] for i in idx) / len(idx)
            acc = sum(labels[i] for i in idx) / len(idx)
            total += len(idx) / len(probs) * abs(conf - acc)
    return total


def _split(uniprot: str, seed: str) -> str:
    u = _u(seed + "|split", uniprot)
    return "dev" if u < 0.6 else ("val" if u < 0.8 else "sealed")


def _sim_residues(sequence: str) -> list[int]:
    """Simulated pocket residues: first three charged or aromatic positions (1-based)."""
    hits = [i + 1 for i, c in enumerate(sequence) if c in "DEKRHYWF"]
    return hits[:3] or [1]


@dataclass(frozen=True)
class Stage:
    name: str
    worker_truth: set[str]
    worker: object


def run_chain(rows: list[Row], run_dir: Path, seed: str = "msf-chain-v1") -> dict:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    by_id = {r.domain_id: r for r in rows}
    lib = library(seed)
    lig_by_id = {L["ligand_id"]: L for L in lib}
    ids = [r.domain_id for r in rows]

    # --- Stage 1: bindPredict on domains (blinded) -------------------------------------
    bind_truth = planted_truth(ids, rate=0.2, seed=seed)

    def wired(truth: set[str]) -> set[str]:
        # Workers receive opaque wire ids, so the planted truth must be expressed in wire space.
        return {wire_id(seed, t) for t in truth}

    bind_worker = SimulatedWorker(wired(bind_truth), seed)
    run_stage("bindpredict", rows, bind_worker, run_dir / "stages", SIM_THRESHOLDS,
              batch_size=100, blind_salt=seed)
    bind_rows = read_scores(run_dir / "stages", "bindpredict")
    advanced_domains = [r["item_id"] for r in bind_rows if r.get("advanced") is True]

    # --- True pairs: each planted positive domain has one planted ligand -----------------
    true_lig = {d: lib[int(_u(seed + "|lig", d) * (len(lib) - 1))]["ligand_id"]
                for d in bind_truth}
    pair_truth = {f"{d}|{lig}" for d, lig in true_lig.items()}

    def pair_items(domains: list[str]) -> list[Item]:
        out = []
        for d in domains:
            for L in lib:
                out.append(Item(item_id=f"{d}|{L['ligand_id']}",
                                input_sha256=_sha(f"{by_id[d].sequence_sha256}|{L['ligand_id']}")))
        return out

    # --- Stage 2: PSICHIC on pairs of advanced domains ----------------------------------
    psi_items = pair_items(advanced_domains)
    run_stage("psichic", psi_items, SimulatedWorker(wired(pair_truth), seed + "|psi"),
              run_dir / "stages", SIM_THRESHOLDS, batch_size=500, blind_salt=seed)
    psi_rows = read_scores(run_dir / "stages", "psichic")
    psi_adv = [r["item_id"] for r in psi_rows if r.get("advanced") is True]

    # --- Stage 3: DiffDock (simulated worker) on PSICHIC survivors ----------------------
    # Size bias is off: the simulator looks up ligand size from the pair id, which blinding hides.
    dd_items = [Item(item_id=p, input_sha256=_sha(p + "|dd")) for p in psi_adv]
    run_stage("diffdock", dd_items,
              SimulatedDiffDock(wired(pair_truth), seed + "|dd"),
              run_dir / "stages", SIM_THRESHOLDS, batch_size=500, blind_salt=seed)
    dd_rows = read_scores(run_dir / "stages", "diffdock")
    dd_adv = {r["item_id"]: r for r in dd_rows if r.get("advanced") is True}

    # --- Evidence store: every scored row becomes one EvidenceItem ----------------------
    psi_by = {r["item_id"]: r for r in psi_rows if r.get("status") == "scored"}
    bind_by = {r["item_id"]: r for r in bind_rows if r.get("status") == "scored"}
    homology = {p for p in pair_truth if _u(seed + "|hom", p) < 0.5}
    evidence: list[dict] = []

    def where(stage: str) -> dict[str, str]:
        """Map each item to the real batch file that holds its row, so locators resolve."""
        out: dict[str, str] = {}
        for path in sorted((run_dir / "stages" / "batches").glob(f"{stage}-*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    out[json.loads(line)["item_id"]] = f"stages/batches/{path.name}"
        return out

    loc = {"bindpredict": where("bindpredict"), "psichic": where("psichic"),
           "diffdock": where("diffdock")}

    def ev(channel: str, item_id: str, row: dict, source: str, strength: float,
           assertion: str, locator: str) -> dict:
        domain = item_id.split("|")[0]
        d = by_id[domain]
        ev_id = "ev_" + _sha(f"{source}|{item_id}|{row.get('score')}")[:16]
        return {
            "evidence_id": ev_id, "channel": channel, "target": d.uniprot_id,
            "claim": {"type": source, "assertion": assertion,
                      "qualifiers": "SIMULATED. Planted truth. Not evidence about any protein."},
            "direction": "supports" if row.get("advanced") is True else "neutral",
            "strength": round(min(max(strength, 0.0), 1.0), 6),
            "provenance": {
                "source": source, "snapshot": SNAPSHOT, "retrieved": now,
                "source_date": "2026-11-07", "source_date_confidence": "low",
                "locator": f"{locator}#{item_id}",
                "tool_version": "0.1.0", "command": f"msf screen chain --seed {seed}",
                "reproducible": True,
            },
        }

    for item_id, row in bind_by.items():
        evidence.append(ev("structure", item_id, row, "simulated-bindpredict",
                           row["score"],
                           f"simulated domain score {row['score']:.3f} for small-molecule binding",
                           loc["bindpredict"][item_id]))
    for item_id, row in psi_by.items():
        evidence.append(ev("screening", item_id, row, "simulated-psichic",
                           row["score"],
                           f"simulated pair score {row['score']:.3f} (raw; not yet calibrated)",
                           loc["psichic"][item_id]))
    for item_id, row in ((r["item_id"], r) for r in dd_rows if r.get("status") == "scored"):
        # Strength is the logistic of the confidence. The assertion gives the raw confidence too.
        conf = 1 / (1 + math.exp(-row["score"]))
        evidence.append(ev("screening", item_id, row, "simulated-diffdock", conf,
                           f"simulated DiffDock confidence {row['score']:.3f} "
                           f"({row['confidence_band']}); strength = sigmoid(confidence)",
                           loc["diffdock"][item_id]))
    # The homology item is a planted fixture, not a stage row. Its locator says so.
    for p in homology:
        if p in psi_by:
            evidence.append(ev("homology", p, psi_by[p], "simulated-homology", 0.7,
                               "planted homology fixture (measures nothing; test fixture)",
                               "fixture:planted_homology"))

    evidence_ids_for: dict[str, list[str]] = {}
    for e in evidence:
        pair = e["provenance"]["locator"].split("#", 1)[1]
        evidence_ids_for.setdefault(pair, []).append(e["evidence_id"])
    evidence_ids_for = {k: v for k, v in evidence_ids_for.items()}

    # --- Hypotheses, with the 2-channel validator --------------------------------------
    hypotheses, rejected = [], []
    for pair, dd in dd_adv.items():
        domain, lig_id = pair.split("|")
        d = by_id[domain]
        channels = ["sequence_model"] + (["homology"] if pair in homology else [])
        independent = len(channels)
        residues = _sim_residues(d.sequence)
        base = {
            "hypothesis_id": "hyp_" + _sha(f"hyp|{pair}")[:16],
            "target": d.uniprot_id,
            "ligand": {"inchikey": lig_by_id[lig_id]["inchikey"], "name": lig_id},
            "mechanism": (f"SIMULATED: predicted pocket residues {residues} in domain "
                          f"{d.start}-{d.end} would contact {lig_id}. The scores are sequence-based "
                          "simulations; no experimental or predicted 3D structure was used."),
            "supporting_evidence": evidence_ids_for.get(pair, []),
            "expected_attack": ("If the residues do not contact the ligand, DiffDock confidence "
                                "reflects the template rather than the pocket; see pocket_ablation."),
            "model_prior": False,
            "prior_speculation": False,
        }
        if independent < 2:
            rejected.append({"pair": pair, "reason": f"single independent channel: {channels}"})
            continue
        hypotheses.append(base | {"_pair": pair, "_channels": channels})

    # --- Scripted falsifier attacks (computable from the artifacts) ---------------------
    lig_hits: dict[str, int] = {}
    for p in psi_adv:
        lig_hits[p.split("|")[1]] = lig_hits.get(p.split("|")[1], 0) + 1
    n_domains = max(1, len(advanced_domains))
    scripted: list[dict] = []
    for h in hypotheses:
        domain, lig_id = h["_pair"].split("|")
        attempts = []
        others = [psi_by[k]["score"] for k in psi_by
                  if k.startswith(domain + "|") and k.split("|")[1] != lig_id]
        if len(others) >= 2:
            mean = sum(others) / len(others)
            sd = (sum((x - mean) ** 2 for x in others) / (len(others) - 1)) ** 0.5
            if sd > 0:
                z = (psi_by[h["_pair"]]["score"] - mean) / sd
                attempts.append({"attack": "decoy_substitution",
                                 "outcome": "killed" if z < 2 else "survived",
                                 "detail": f"z={z:.2f} against {len(others)} decoys (kill if < 2)"})
        rate = lig_hits.get(lig_id, 0) / n_domains
        attempts.append({"attack": "promiscuity",
                         "outcome": "killed" if rate > 0.5 else "survived",
                         "detail": f"ligand advanced for {rate:.0%} of advanced domains (kill if > 50%)"})
        for name, why in [
            ("pocket_ablation", "no residue-level perturbation in simulation"),
            ("abundance", "no tissue or concentration data supplied"),
            ("pathway_coherence", "no pathway data supplied"),
            ("template_dependence", "simulated channels carry no template identifiers"),
            ("literature_contradiction", "no dated literature supplied"),
            ("conservation", "no orthologue alignment supplied"),
            ("restatement", "channels share one sequence model; restatement check needs template ids"),
        ]:
            attempts.append({"attack": name, "outcome": "not_attempted",
                             "reason_not_attempted": why})
        killed = any(a["outcome"] == "killed" for a in attempts)
        h["falsification"] = {"attempts": attempts, "survived": not killed}
        scripted.append({"hypothesis_id": h["hypothesis_id"], "pair": h["_pair"],
                         "attempts": attempts, "survived": not killed})

    # --- Calibration on val, evaluation on sealed, abstention ---------------------------
    # The calibrator is fitted on EVERY PSICHIC-scored pair, not only DiffDock survivors.
    # Fitting on survivors alone has no negatives to learn from. DiffDock stays a gate.
    cand = [(p, r) for p, r in psi_by.items()]
    split_of = {p: _split(by_id[p.split("|")[0]].uniprot_id, seed) for p, _ in cand}

    def feats(p: str) -> list[float]:
        # Homology is NOT a feature. The planted fixture exists only for true pairs, so using
        # it would leak the answer into the calibrator. It is a gate (two channels), not a feature.
        return [psi_by[p]["score"]]

    val = [(feats(p), int(p in pair_truth)) for p, _ in cand if split_of[p] == "val"]
    sealed = [(feats(p), int(p in pair_truth)) for p, _ in cand if split_of[p] == "sealed"]
    calib = {"status": "uncalibratable", "reason": "val split has one class"}
    model = None
    if len({y for _, y in val}) == 2:
        # C is large: one unscaled feature under strong L2 shrinks the slope toward zero and
        # flattens every probability. With ~2% positives in val the fit must stay weakly regularised.
        model = LogisticRegression(C=1e4, max_iter=5000).fit(
            [x for x, _ in val], [y for _, y in val])
        probs = model.predict_proba([x for x, _ in sealed])[:, 1].tolist() if sealed else []
        labels = [y for _, y in sealed]
        brier = (sum((p - y) ** 2 for p, y in zip(probs, labels)) / len(probs)) if probs else None
        calib = {"status": "fitted_on_val", "n_val": len(val), "n_sealed": len(sealed),
                 "ece_sealed": None if not probs else round(_ece(probs, labels), 4),
                 "brier_sealed": None if brier is None else round(brier, 4)}

    accepted: dict[str, list[dict]] = {}
    hyp_out = []
    for h in hypotheses:
        p = float(model.predict_proba([feats(h["_pair"])])[0][1]) if model else None
        verdict, reason = "abstain", "calibration unavailable"
        if p is not None:
            if not h["falsification"]["survived"]:
                reason = "killed by falsifier"
            elif p < P_ACCEPT:
                reason = f"p={p:.2f} below pre-registered {P_ACCEPT}"
            else:
                verdict, reason = "accept", f"p={p:.2f}"
        h["p_correct"] = None if p is None else round(p, 4)
        h["verdict"] = verdict
        h["verdict_reason"] = reason
        if verdict == "accept":
            accepted.setdefault(h["target"], []).append(h)
        hyp_out.append(h)

    # --- Write records --------------------------------------------------------------------
    art = run_dir
    (art / "evidence").mkdir(exist_ok=True)
    with (art / "evidence" / "evidence.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for e in evidence:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    (art / "hypotheses").mkdir(exist_ok=True)
    verdicts = []
    with (art / "hypotheses" / "hypotheses.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for h in hyp_out:
            # The Hypothesis schema forbids extra keys, so verdicts go in their own file.
            rec = {k: v for k, v in h.items() if not k.startswith("_")
                   and k not in ("verdict", "verdict_reason", "p_correct")}
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            verdicts.append({"hypothesis_id": h["hypothesis_id"], "p_correct": h["p_correct"],
                             "verdict": h["verdict"], "reason": h["verdict_reason"]})
    (art / "hypotheses" / "verdicts.json").write_text(json.dumps(verdicts, indent=2), encoding="utf-8")
    (art / "hypotheses" / "rejected.json").write_text(json.dumps(rejected, indent=2), encoding="utf-8")
    (art / "falsification").mkdir(exist_ok=True)
    (art / "falsification" / "scripted.json").write_text(json.dumps(scripted, indent=2), encoding="utf-8")
    (art / "dossiers").mkdir(exist_ok=True)
    targets = sorted({r.uniprot_id for r in rows})
    for t in targets:
        hs = [{k: v for k, v in h.items() if not k.startswith("_") and k not in ("verdict", "verdict_reason", "p_correct")}
              for h in accepted.get(t, [])]
        best_p = max((h["p_correct"] for h in accepted.get(t, [])), default=None)
        dossier = {
            "target": t, "run_id": run_dir.name, "loop_version": LOOP_VERSION,
            "hypotheses": hs, "abstained": not hs,
            "calibrated_probability": best_p,
            "calibration_model": (f"logistic regression on the PSICHIC score, fitted on the val "
                                  f"split ({calib['status']}). calibrated_probability is the max "
                                  "p_correct over this target's accepted hypotheses (verdicts.json)."),
            "correlation_discount_applied": False,
            "what_would_change_our_mind": {
                "experiment": "Measured binding of the top pair on a non-simulated structure.",
                "cost": {"estimate": "not estimated", "confidence": "not_estimated"},
                "does_not_resolve": "Whether the planted truth matches biology; this run is simulated.",
            },
            "library_coverage": (f"SIMULATION: library of {len(lib)} synthetic ligands including a methane "
                                 "control. The true ligand is present by construction."),
            "limitations": {"contamination_bin": "not_probed", "structure_source": "none",
                            "stratum": "clean"},
        }
        if not hs:  # abstention_reason is a string when present; omit it otherwise
            dossier["abstention_reason"] = "no hypothesis accepted (see hypotheses/verdicts.json)"
        (art / "dossiers" / f"{t}.json").write_text(json.dumps(dossier, indent=2), encoding="utf-8")

    # --- Controls (harness controls; see docs/04 §5.1) -----------------------------------
    controls = {}
    methane_pairs = [p for p in psi_by if p.endswith("|CH4-CONTROL")]
    controls["methane"] = {"pass": not any(psi_by.get(p, {}).get("advanced") for p in methane_pairs),
                           "n": len(methane_pairs),
                           "criterion": "no methane pair advances at PSICHIC"}
    scrambled = [Item(item_id=d + "|scrambled", input_sha256=_sha(by_id[d].sequence_sha256 + "scr"))
                 for d in advanced_domains]
    run_stage("bindpredict", scrambled, SimulatedWorker(set(), seed + "|scr"),
              run_dir / "controls" / "scrambled", SIM_THRESHOLDS, batch_size=500)
    scr = read_scores(run_dir / "controls" / "scrambled", "bindpredict")
    controls["scrambled_sequence"] = {"pass": not any(r.get("advanced") for r in scr),
                                      "n": len(scr),
                                      "criterion": "no scrambled domain advances at bindPredict"}
    shuffled_truth = {f"{d}|{true_lig[e]}" for d, e in zip(sorted(true_lig), sorted(true_lig)[1:] + sorted(true_lig)[:1])} if len(true_lig) > 1 else set()
    shuffled = [p for p in psi_by if p in shuffled_truth]
    shuffled_hits = [p for p in shuffled if psi_by[p].get("advanced") is True]
    controls["shuffled_pairs"] = {"pass": (len(shuffled_hits) / len(shuffled) <= 0.1) if shuffled else True,
                                  "recall_under_shuffled_labels":
                                      (len(shuffled_hits) / len(shuffled)) if shuffled else None,
                                  "n": len(shuffled),
                                  "procedure": "true ligands rotated by one domain in sorted "
                                               "domain order; deterministic, no random seed",
                                  "criterion": "recall under shuffled labels <= 0.10 "
                                               "(the real PSICHIC scores, relabelled)"}
    (art / "controls.json").write_text(json.dumps(controls, indent=2), encoding="utf-8")

    # Split membership counts only proteins that have PSICHIC pairs, so they reconcile with the
    # evaluated data. Membership per target is written to splits.json.
    scored_targets = sorted({by_id[p.split("|")[0]].uniprot_id for p in psi_by})
    split_of_target = {t: _split(t, seed) for t in scored_targets}
    split_counts = {s: sum(1 for v in split_of_target.values() if v == s)
                    for s in ("dev", "val", "sealed")}
    (art / "splits.json").write_text(json.dumps({
        "unit": "uniprot accession (proxy for the 30% sequence-identity cluster in docs/04 §1.4)",
        "membership": split_of_target, "counts": split_counts,
        "pairs_per_split": {s: sum(1 for p in psi_by if split_of_target.get(
            by_id[p.split("|")[0]].uniprot_id) == s) for s in ("dev", "val", "sealed")},
    }, indent=2), encoding="utf-8")
    summary = {
        "label": "SIMULATION. Not evidence about any protein.",
        "counts": {"domains": len(rows), "advanced_bindpredict": len(advanced_domains),
                   "pairs_psichic": len(psi_items), "advanced_psichic": len(psi_adv),
                   "advanced_diffdock": len(dd_adv), "evidence": len(evidence),
                   "hypotheses": len(hypotheses), "rejected_single_channel": len(rejected),
                   "accepted": sum(len(v) for v in accepted.values())},
        "calibration": {**calib, "note": "Planted scores separate the classes, so these numbers "
                                         "check the harness only. They are not calibration evidence."},
        "controls": controls, "splits": split_counts,
    }
    summary["run_cutoff"] = ("none. A simulation has no evidence cutoff. source_date is the run "
                             "date, not a literature date.")
    (art / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if model is not None:
        (art / "calibration.json").write_text(json.dumps({
            "feature": ["psichic_score"], "coef": model.coef_.tolist(),
            "intercept": model.intercept_.tolist(), "C": 1e4,
            "fit_split": "val", "n_val": len(val), "n_val_positive": sum(y for _, y in val),
            "eval_split": "sealed", "n_sealed": len(sealed),
            "n_sealed_positive": sum(y for _, y in sealed),
            "sealed_predictions": model.predict_proba([x for x, _ in sealed])[:, 1].tolist()
            if sealed else [],
            "sealed_labels": [y for _, y in sealed],
            "note": "Harness check only. Planted scores separate the classes.",
        }, indent=2), encoding="utf-8")
    accepted_all = [h for v in accepted.values() for h in v]
    (art / "hypotheses" / "fixture_dependence.json").write_text(json.dumps({
        "accepted": len(accepted_all),
        "accepted_needing_planted_homology_fixture": sum(
            1 for h in accepted_all if h["_pair"] in homology),
        "note": "Each accepted hypothesis passes the two-channel validator only because a planted "
                "homology fixture exists for its true pair. The fixture measures nothing.",
    }, indent=2), encoding="utf-8")
    # Planted truth lives in sealed/. Only the statistician and auditor may read it. This is a
    # process rule in the MVP, not yet a hook, so it is recorded as a known gap in docs/14 §6.
    (art / "sealed").mkdir(exist_ok=True)
    (art / "sealed" / "planted_truth.json").write_text(json.dumps({
        "label": "SIMULATION planted truth. Readable by statistician and auditor only.",
        "bind_truth": sorted(bind_truth), "pair_truth": sorted(pair_truth),
        "homology_fixture": sorted(homology), "true_ligand": true_lig,
    }, indent=2), encoding="utf-8")
    return summary
