"""Audio embedders behind one protocol — the swappable seam.

The Suno-access layer and the representation model WILL change (the spec calls
the ingestion brittle by design), so everything downstream depends only on
`AudioEmbedder`. Real MERT/CLAP embedders slot in behind it; the bench and the
clusterer never know.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class AudioEmbedder(Protocol):
    """One track file in (read transiently), one embedding vector out.

    Implementations MUST NOT retain or copy the audio — derived features only.
    """

    name: str
    dim: int

    def embed(self, path: Path) -> list[float]: ...


class MockEmbedder:
    """Deterministic pseudo-embeddings from file bytes. Zero deps, zero GPU.

    Chunk-mean features: the file is split into `dim` chunks and each dimension
    is that chunk's mean byte value. Locality-preserving (similar bytes ->
    nearby vectors), which is meaningless musically — this proves plumbing,
    not the hypothesis. Swap in MERT for the real Phase 0 test.
    """

    name = "mock"
    dim = 16

    def embed(self, path: Path) -> list[float]:
        data = path.read_bytes() or b"\x00"
        chunk = max(1, len(data) // self.dim)
        vec = []
        for i in range(self.dim):
            piece = data[i * chunk:(i + 1) * chunk] or data[-chunk:]
            vec.append(sum(piece) / (len(piece) * 255.0))
        return vec


class MERTEmbedder:
    """MERT self-supervised music representation (the spec's primary space).

    Requires the `listen` extra:  uv sync --extra listen
    Fetch audio transiently, embed, DISCARD the waveform; persist only the
    vector + metadata + the Suno link.
    """

    name = "mert"
    dim = 768

    def __init__(self, model_id: str = "m-a-p/MERT-v1-95M") -> None:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "MERTEmbedder needs the listen extra: uv sync --extra listen"
            ) from e
        self.model_id = model_id
        raise NotImplementedError(
            "MERT wiring is the Phase 0->1 step: load the model, resample to its "
            "rate, mean-pool hidden states. Tracked in the surveyor task."
        )

    def embed(self, path: Path) -> list[float]:  # pragma: no cover
        raise NotImplementedError
