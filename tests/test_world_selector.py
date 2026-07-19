"""Smoke tests for world selection system.

Verifies WorldSelector can select worlds based on criteria
and handles edge cases.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crawler_agent.cognitive.world_selector import SelectionCriteria, WorldSelector


class TestWorldSelector:
    """Test WorldSelector selection logic."""

    def setup_method(self):
        self.selector = WorldSelector()

    def test_select_default(self):
        criteria = SelectionCriteria()
        result = self.selector.select(criteria)
        assert result is not None
        assert result.world is not None
        assert result.reason is not None

    def test_select_by_difficulty(self):
        criteria = SelectionCriteria(max_difficulty=0.3)
        result = self.selector.select(criteria)
        assert result is not None
        assert result.world is not None

    def test_select_with_weak_skills(self):
        criteria = SelectionCriteria(weak_skills=["navigation", "manipulation"])
        result = self.selector.select(criteria)
        assert result is not None

    def test_select_excludes_worlds(self):
        all_names = list(
            self.selector.select(SelectionCriteria()).world.name
            if hasattr(self.selector.select(SelectionCriteria()).world, "name")
            else str(self.selector.select(SelectionCriteria()).world)
        )
        criteria = SelectionCriteria(exclude_worlds=[all_names[0]] if all_names else [])
        result = self.selector.select(criteria)
        assert result is not None

    def test_select_by_goal(self):
        result = self.selector.select_by_goal("explore indoor environment")
        assert result is not None
        assert result.world is not None

    def test_history_tracking(self):
        for _ in range(3):
            self.selector.select(SelectionCriteria())
        assert len(self.selector.history) == 3

    def test_weak_skills(self):
        self.selector.update_skill("navigation", 0.2)
        self.selector.update_skill("manipulation", 0.8)
        weak = self.selector.get_weak_skills(threshold=0.5)
        assert "navigation" in weak
        assert "manipulation" not in weak
