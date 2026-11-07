"""Loopspec schema validation (task T-002). Schema before implementation.

These are real tests, not stubs. They assert the properties the schema exists to enforce,
so that a future edit cannot quietly remove a guarantee the rest of the project assumes.
"""

import copy
import json
import pathlib

import jsonschema
import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "loops" / "loopspec.schema.json"
BASELINE_PATH = ROOT / "loops" / "v0.1.0-baseline.yaml"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def baseline() -> dict:
    return yaml.safe_load(BASELINE_PATH.read_text(encoding="utf-8"))


def test_schema_is_itself_a_valid_jsonschema(schema):
    """Catches an editing mistake in the schema before it silently stops validating."""
    jsonschema.Draft202012Validator.check_schema(schema)


def test_baseline_validates(schema, baseline):
    """The incumbent loop version conforms to the schema."""
    jsonschema.validate(baseline, schema)


def test_every_loopspec_on_disk_validates(schema):
    """Every versioned loopspec, not just the baseline."""
    specs = sorted((ROOT / "loops").glob("v*.yaml"))
    assert specs, "no loopspecs found; the incumbent version must exist on disk"
    for spec in specs:
        jsonschema.validate(yaml.safe_load(spec.read_text(encoding="utf-8")), schema)


def test_raw_docking_score_is_not_a_permitted_normalisation(schema, baseline):
    """The central scientific prohibition, enforced by the schema rather than by review.

    Empirical scoring functions rank poses within one ligand acceptably and rank different
    molecules against each other poorly. The schema must admit no option for ranking on a
    raw score -- see .claude/agents/screener.md.
    """
    allowed = schema["properties"]["channels"]["properties"]["screening"] \
                    ["properties"]["score_normalisation"]["enum"]
    assert set(allowed) == {"decoy_zscore", "library_percentile"}

    bad = copy.deepcopy(baseline)
    bad["channels"]["screening"]["score_normalisation"] = "raw_score"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_min_independent_channels_cannot_be_below_two(schema, baseline):
    """A hypothesis needs two independent non-LLM channels, counted after the
    correlation discount. One channel is an anecdote."""
    bad = copy.deepcopy(baseline)
    bad["hypothesis"]["min_independent_channels"] = 1
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_require_mechanism_cannot_be_disabled(schema, baseline):
    """A ligand name without a mechanism naming pocket residues is a guess."""
    bad = copy.deepcopy(baseline)
    bad["hypothesis"]["require_mechanism"] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_fusion_cannot_be_fitted_on_sealed_or_dev(schema, baseline):
    """fitted_on admits only `val`.

    Fitting on `dev` overfits the development targets; fitting on `sealed` is tuning on
    the test set. The fusion agent refuses at runtime too, but the schema makes the
    configuration unwritable in the first place.
    """
    assert schema["properties"]["fusion"]["properties"]["fitted_on"]["enum"] == ["val"]
    for split in ("sealed", "dev"):
        bad = copy.deepcopy(baseline)
        bad["fusion"]["fitted_on"] = split
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


def test_version_id_must_be_semver(schema, baseline):
    """Versioning is over comparability of results, so the id carries meaning."""
    for bad_id in ("latest", "v1", "0.1.0", "v0.1"):
        bad = copy.deepcopy(baseline)
        bad["id"] = bad_id
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


def test_date_filter_only_admits_strict_or_none(schema):
    """`none` exists so a discovery-mode run can be expressed, but the guard refuses it
    on any benchmark split. The schema records both options; enforcement is at the hook."""
    enum = schema["properties"]["channels"]["properties"]["literature"] \
                 ["properties"]["date_filter"]["enum"]
    assert set(enum) == {"strict", "none"}


def test_baseline_uses_strict_date_filtering(baseline):
    """The incumbent must be benchmark-safe out of the box."""
    assert baseline["channels"]["literature"]["date_filter"] == "strict"


def test_baseline_does_not_use_a_non_redistributable_library(baseline):
    """HMDB is CC BY-NC 4.0 and would make this repository undonatable.

    Guards the substitution recorded in docs/06-DATA-SOURCES.md, so a future edit cannot
    quietly reintroduce it. See failure mode B13.
    """
    library = baseline["channels"]["chemistry"]["library"].lower()
    for forbidden in ("hmdb", "kegg", "drugbank", "zinc", "archs4"):
        assert forbidden not in library, (
            f"{forbidden} is marked AVOID in docs/06-DATA-SOURCES.md and cannot be "
            f"the default candidate library"
        )


def test_baseline_excludes_predicted_structures(baseline):
    """AlphaFold DB postdates the 2015 and 2018 cutoffs entirely, so a predicted model is
    future information at those dates. Leak L5b."""
    sources = baseline["channels"]["structure"]["allowed_structure_sources"]
    assert "predicted" not in sources


def test_falsifier_battery_includes_restatement(baseline):
    """`restatement` detects channels that are the same fact arriving twice, which is the
    main route to over-confidence in this architecture. It is not optional."""
    assert "restatement" in baseline["falsification"]["battery"]


def test_refinement_rounds_are_bounded(schema, baseline):
    """Unbounded critique converges on text that satisfies the critic, not on a better
    hypothesis."""
    assert baseline["falsification"]["max_refinement_rounds"] <= 5
    bad = copy.deepcopy(baseline)
    bad["falsification"]["max_refinement_rounds"] = 50
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_abstention_threshold_is_present_and_nonzero(baseline):
    """A loop version that can never abstain cannot be promoted (ADR-0003)."""
    assert baseline["fusion"]["abstain_below"] > 0


def test_budgets_are_declared(baseline):
    """Cost is a declared property of a loop version, so a change that triples it is
    visible in the diff."""
    budgets = baseline["budgets"]
    assert budgets["usd_per_target"] > 0
    assert budgets["wallclock_minutes_per_target"] > 0
