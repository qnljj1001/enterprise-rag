"""文本编码器：bge-m3 本地模型与测试用 hash 编码器。"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import threading
from collections.abc import Sequence

from ..config import Settings
from ..ports import Embedder

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


class HashingEmbedder:
    """确定性特征哈希编码器，仅用于单元测试/E2E，不代表真实语义。"""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _tokens(self, text: str) -> list[str]:
        base = _TOKEN_RE.findall(text.lower())
        tokens: list[str] = list(base)
        for index in range(len(base) - 1):
            tokens.append(base[index] + base[index + 1])
        return tokens

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in self._tokens(text):
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                value = int.from_bytes(digest, "big")
                idx = value % self.dim
                sign = 1.0 if (value >> 63) & 1 else -1.0
                vec[idx] += sign
            norm = math.sqrt(sum(item * item for item in vec)) or 1.0
            vectors.append([item / norm for item in vec])
        return vectors


class BgeM3Embedder:
    """懒加载 BAAI/bge-m3；GPU 可用时用 fp16，OOM 回退 CPU。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.dim = settings.embedding_dim
        self._model = None
        self._device = "cpu"
        self._lock = threading.Lock()

    def _resolve_device(self) -> str:
        configured = (self.settings.embedding_device or "auto").lower()
        if configured != "auto":
            return configured
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from sentence_transformers import SentenceTransformer

            self.settings.embedding_cache_dir.mkdir(parents=True, exist_ok=True)
            device = self._resolve_device()
            logger.info("加载 bge-m3 模型：%s（device=%s）", self.settings.embedding_model, device)
            try:
                self._model = SentenceTransformer(
                    self.settings.embedding_model,
                    device=device,
                    cache_folder=str(self.settings.embedding_cache_dir),
                )
                self._device = device
            except Exception:
                logger.exception("bge-m3 GPU 加载失败，回退 CPU")
                self._model = SentenceTransformer(
                    self.settings.embedding_model,
                    device="cpu",
                    cache_folder=str(self.settings.embedding_cache_dir),
                )
                self._device = "cpu"
            try:
                self._model.max_seq_length = self.settings.embedding_max_length
            except Exception:
                pass
            logger.info("bge-m3 加载完成：device=%s dim=%s", self._device, self.dim)

    def preload(self) -> None:
        self._load()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        self._load()
        assert self._model is not None
        try:
            vectors = self._model.encode(
                list(texts),
                batch_size=self.settings.embedding_batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as exc:
            logger.warning("bge-m3 编码失败，尝试回退 CPU：%s", exc)
            self._model = None
            self.settings.embedding_device = "cpu"
            self._load()
            assert self._model is not None
            vectors = self._model.encode(
                list(texts),
                batch_size=self.settings.embedding_batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        return [list(map(float, row)) for row in vectors]


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedding_provider == "hash":
        return HashingEmbedder(settings.embedding_dim)
    return BgeM3Embedder(settings)
