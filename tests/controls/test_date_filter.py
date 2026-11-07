"""Leak L1: no post-cutoff document may reach an agent.

This is the highest-value test in the repository (task T-006). If it fails, every
downstream number is uninterpretable -- and it fails in the direction that makes
results look BETTER, so nothing else would catch it.

The filter must be enforced at the tool boundary, not by prompt instruction.
These tests therefore exercise the retrieval wrapper directly, bypassing any agent.
"""

import pytest

pytestmark = pytest.mark.controls


@pytest.mark.xfail(reason="T-006 not implemented", strict=False)
def test_post_cutoff_document_is_rejected():
    """A document dated after the cutoff never reaches the caller."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-006 not implemented", strict=False)
def test_rejection_is_recorded_not_silent():
    """Discarded documents appear in the retrieval log with their dates.

    A silent drop is indistinguishable from an empty search, and we need to tell
    'nothing was published' from 'everything was filtered'.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-006 not implemented", strict=False)
def test_source_date_is_not_retrieved_date():
    """source_date is the date of the FACT; retrieved is when we fetched it.

    Conflating them is the single easiest way to invalidate the benchmark.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-006 not implemented", strict=False)
def test_preprint_date_preferred_over_journal_date():
    """The earliest of preprint and journal date is used, and both are recorded."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-006 not implemented", strict=False)
def test_missing_date_is_rejected_not_assumed_old():
    """A document with no resolvable date is rejected, never treated as pre-cutoff."""
    raise NotImplementedError


@pytest.mark.xfail(reason="T-006 not implemented", strict=False)
def test_wrapper_verifies_the_filter_was_actually_applied():
    """Failure mode A13: some APIs fail OPEN on a malformed filter.

    The ChEMBL REST API accepts a bad filter parameter, ignores it, and returns the
    full unfiltered result set with HTTP 200. A typo in a date filter therefore returns
    everything -- including post-cutoff records -- and looks exactly like success.

    So every wrapper must assert filtered_count < unfiltered_count and record both.
    A filter that changed nothing is a FAILED filter, not an empty result.
    """
    raise NotImplementedError


@pytest.mark.xfail(reason="T-006 not implemented", strict=False)
def test_filter_counts_are_recorded_in_provenance():
    """Both counts travel with the evidence, so the assertion is auditable after the fact."""
    raise NotImplementedError
