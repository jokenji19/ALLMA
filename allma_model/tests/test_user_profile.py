"""Profile tests migrated from the removed incremental_learning profile to core."""
from allma_model.core.user_profile import UserProfile, UserPreferences
from allma_model.emotional_system.emotional_core import EmotionalState
from types import SimpleNamespace
import pytest


def test_profile_defaults_are_independent():
    first, second = UserProfile('a'), UserProfile('b')
    first.preferences.favorite_topics.append('mare')
    assert second.preferences.favorite_topics == []
    assert first.get_preferences()['communication_style'] == 'neutral'
    assert first.user_id == 'a'


@pytest.mark.parametrize('text,style', [('Cortesemente, vorrei aiuto', 'formal'), ('Ehi ciao!', 'casual')])
def test_profile_adapts_to_user(text, style):
    profile = UserProfile('u')
    profile.update_preferences(text, EmotionalState('joy', 0.9, {}, 0.8), SimpleNamespace(engagement_level=0.9))
    assert profile.preferences.communication_style == style
    assert profile.preferences.emotional_sensitivity == pytest.approx(0.59)
    assert len(profile.interaction_history) == 1
    assert len(profile.social_history) == 1


def test_profile_round_trip(tmp_path):
    profile = UserProfile('u')
    profile.preferences.favorite_topics = ['mare']
    path = tmp_path / 'profile.json'
    profile.save_to_file(str(path))
    restored = UserProfile('u')
    restored.load_from_file(str(path))
    assert restored.get_preferences() == profile.get_preferences()
    assert restored.last_update == profile.last_update
