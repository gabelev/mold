"""The Mold masthead. Each persona is an ensemble.Agent subclass.

Base prompts + personalities live here (instance content). The drifting
self-state lives in terrarium so it is public and diff-able.
"""

from mold.personas.planner import PlanningAgent
from mold.personas.critic import CriticAgent
from mold.personas.editor import EditorAgent

__all__ = ["PlanningAgent", "CriticAgent", "EditorAgent"]
