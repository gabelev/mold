"""Mold's design system: the petri palette, the starter primitive kit, and the
Art Director that composes issues from it. All instance content — the
composition *mechanics* live in ensemble.design."""

from mold.design.artdirector import ArtDirectorAgent
from mold.design.primitives import build_library, STANCE_MAP

__all__ = ["ArtDirectorAgent", "build_library", "STANCE_MAP"]
