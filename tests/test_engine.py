from types import SimpleNamespace

import pytest

from terchess.engine import validate_skill_level


def make_engine(minimum=0, maximum=20):
    option = SimpleNamespace(min=minimum, max=maximum)
    return SimpleNamespace(options={"Skill Level": option})


@pytest.mark.parametrize("level", [0, 1, 10, 20])
def test_validate_skill_level_accepts_supported_values(level):
    validate_skill_level(make_engine(), level)


@pytest.mark.parametrize("level", [-1, 21])
def test_validate_skill_level_rejects_values_outside_supported_range(level):
    with pytest.raises(ValueError, match="between 0 and 20"):
        validate_skill_level(make_engine(), level)


def test_validate_skill_level_rejects_engine_without_skill_option():
    engine = SimpleNamespace(options={})
    with pytest.raises(RuntimeError, match="does not expose"):
        validate_skill_level(engine, 10)


def test_validate_skill_level_respects_engine_specific_limits():
    with pytest.raises(ValueError, match="maximum Skill Level is 18"):
        validate_skill_level(make_engine(maximum=18), 20)
