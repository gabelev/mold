"""The perception layer: audio -> representation -> field reading.

This is the shared substrate the surveyor spec calls for (and the piece that
later serves the Ensemble Effect work). Phase 0 lives here: a bench that
embeds a hand-picked manifest of tracks and asks the two cheap questions —
is a trend visible as structure/drift in embedding space, and can it be named?

Copyright wall, enforced by shape: embedders consume a local file transiently
and return ONLY derived features. Nothing here stores or copies audio.
"""

from mold.perception.embedder import AudioEmbedder, MockEmbedder

__all__ = ["AudioEmbedder", "MockEmbedder"]
