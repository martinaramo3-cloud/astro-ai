"""Bands cut from what the engine actually produces, not from guessed numbers.

The old thresholds put "obsessive" at 21 and "toxic" at 13. Measured against a
thousand fictional pairs, the tenth percentile for attraction is 23 and for
toxicity 18.5 — so almost every pair cleared both, and 95.8% of all couples
were classified a "toxic attraction". The label fired for nearly every two
people alive, which made it meaningless and, to the person reading it, untrue.
"""
import pytest

from app.compatibility_service import RULES, _bucketize_index, _classify_relationship


def test_every_index_is_banded():
    """Only attraction and toxicity had bands; emotional and long_term were
    computed and then never described."""
    assert set(RULES["index_thresholds"]) == {"attraction", "emotional", "long_term", "toxicity"}


@pytest.mark.parametrize("index, value, band", [
    # Percentiles of 1,000 fictional pairs.
    ("attraction", 20.0, "low"), ("attraction", 38.5, "typical"),
    ("attraction", 52.0, "high"), ("attraction", 80.0, "exceptional"),
    ("toxicity", 18.0, "low"), ("toxicity", 36.0, "typical"),
    ("toxicity", 55.0, "high"), ("toxicity", 90.0, "exceptional"),
    ("emotional", 2.0, "low"), ("emotional", 12.5, "typical"),
    ("long_term", 1.0, "low"), ("long_term", 10.0, "typical"),
])
def test_bands_sit_where_the_data_sits(index, value, band):
    assert _bucketize_index(index, value) == band


def test_a_median_pair_is_not_remarkable():
    """The median pair used to come out obsessive and toxic."""
    median = {"attraction": 38.5, "emotional": 12.5, "long_term": 10.0, "toxicity": 36.2}
    assert _bucketize_index("attraction", median["attraction"]) == "typical"
    assert _bucketize_index("toxicity", median["toxicity"]) == "typical"
    assert _classify_relationship(median) == ["nothing that stands out either way"]


def test_high_pull_with_high_friction_is_now_rare():
    """It needs the top quarter for attraction and the top tenth for friction —
    about 5% of pairs, not 96%."""
    ordinary = {"attraction": 38.5, "emotional": 12.5, "long_term": 10.0, "toxicity": 36.2}
    assert "high pull with high friction" not in _classify_relationship(ordinary)
    extreme = {"attraction": 60.0, "emotional": 12.5, "long_term": 10.0, "toxicity": 70.0}
    assert "high pull with high friction" in _classify_relationship(extreme)


def test_every_matching_description_is_kept():
    """A pair can have real long-term potential and real friction. Returning
    whichever was listed first threw away half the reading."""
    both = {"attraction": 55.0, "emotional": 20.0, "long_term": 20.0, "toxicity": 65.0}
    matched = _classify_relationship(both)
    assert "strong relationship potential" in matched
    assert "high pull with high friction" in matched
    assert isinstance(matched, list)


def test_no_label_calls_anybody_toxic():
    """Describe the friction, never label the people."""
    for classifier in RULES["classifiers"].values():
        assert "toxic" not in classifier["label"].lower(), classifier["label"]


def test_eighth_house_is_depth_not_a_point_in_its_favour():
    """Intensity says how deep an exchange goes, not whether it is enjoyable,
    mutual or sustainable."""
    assert not any("8th" in flag for flag in RULES["green_flags"])
    assert any("8th" in marker for marker in RULES["neutral_markers"])
