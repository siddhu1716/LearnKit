"""Diversity-aware re-ranking utilities.

Ported from ruflo's SmartRetrieval pipeline (ADR-090, LongMemEval-derived):
``ruflo/v3/@claude-flow/memory/src/smart-retrieval.ts``.

Two language-agnostic algorithms are reproduced here:

* **MMR (Maximal Marginal Relevance)** diversity re-ranking using a
  token-Jaccard proxy. No embeddings are required, so it can run anywhere a
  record exposes textual content — including inside the bounded
  :class:`~learnkit.router.MemoryRouter` budget selection.
* **Reciprocal Rank Fusion (RRF)** for fusing several ranked candidate lists
  (e.g. a lexical/BM25 arm and a dense/vector arm) without having to normalise
  heterogeneous score scales.

Motivation: LearnKit's router previously admitted records into the bounded
8-record / ~1200-token budget purely by confidence. When several near-duplicate
records (e.g. variants of the same skill) outranked everything else, they could
fill the entire budget and crowd out diverse, complementary context — the
"memory soup" / wrong-pattern failure mode documented in the codebase reviews.
MMR re-ranking spends the budget on relevant *and* non-redundant records.
"""

from __future__ import annotations

from typing import Callable, Hashable, Sequence, TypeVar

T = TypeVar("T")

# Small English stoplist mirrored from ruflo's smart-retrieval tokenizer so the
# Jaccard overlap proxy keys on content words rather than glue words.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "did", "do",
        "does", "for", "from", "has", "have", "how", "i", "if", "in", "is",
        "it", "its", "me", "my", "of", "on", "or", "that", "the", "this", "to",
        "was", "were", "what", "when", "where", "which", "who", "why", "will",
        "with", "you", "your",
    }
)


def tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, drop stopwords and short tokens.

    Mirrors ruflo's ``tokenize`` helper — tokens shorter than 3 characters and
    stopwords are discarded so the Jaccard overlap reflects content similarity.
    """
    tokens: set[str] = set()
    for raw in _split_words(text.lower()):
        if len(raw) > 2 and raw not in _STOPWORDS:
            tokens.add(raw)
    return tokens


def _split_words(text: str) -> list[str]:
    out: list[str] = []
    current: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            current.append(ch)
        elif current:
            out.append("".join(current))
            current = []
    if current:
        out.append("".join(current))
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets, in ``[0, 1]``."""
    if not a and not b:
        return 0.0
    intersect = len(a & b)
    union = len(a) + len(b) - intersect
    return intersect / union if union else 0.0


def mmr_order(
    candidates: Sequence[T],
    relevance_of: Callable[[T], float],
    text_of: Callable[[T], str],
    lambda_: float = 0.7,
    limit: int | None = None,
) -> list[T]:
    """Re-order ``candidates`` by Maximal Marginal Relevance.

    Greedy selection identical to ruflo's ``mmrRerank``: seed with the
    highest-relevance candidate, then repeatedly pick the candidate maximising
    ``lambda * relevance - (1 - lambda) * max_overlap`` where ``max_overlap`` is
    the largest token-Jaccard similarity against the already-selected set.

    Args:
        candidates: items to re-rank (any order — relevance is read via
            ``relevance_of`` rather than assumed from position).
        relevance_of: returns a per-candidate relevance score (higher = better).
        text_of: returns the candidate's textual content for the overlap proxy.
        lambda_: relevance/diversity trade-off. ``1.0`` = pure relevance
            (no diversity), ``0.0`` = pure diversity. Default ``0.7``.
        limit: optional cap on the number of returned items.

    Returns:
        Candidates re-ordered so relevant, non-redundant items come first.
    """
    items = list(candidates)
    if limit is None:
        limit = len(items)
    if len(items) <= 1 or lambda_ >= 1.0:
        return items[:limit]

    pool = sorted(items, key=relevance_of, reverse=True)
    tokens: dict[int, set[str]] = {i: tokenize(text_of(c)) for i, c in enumerate(pool)}

    remaining = list(range(len(pool)))
    selected: list[int] = [remaining.pop(0)]

    while remaining and len(selected) < limit:
        best_idx = -1
        best_mmr = float("-inf")
        for pos, idx in enumerate(remaining):
            max_overlap = 0.0
            for sel in selected:
                sim = jaccard(tokens[idx], tokens[sel])
                if sim > max_overlap:
                    max_overlap = sim
            mmr = lambda_ * relevance_of(pool[idx]) - (1.0 - lambda_) * max_overlap
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = pos
        if best_idx < 0:
            break
        selected.append(remaining.pop(best_idx))

    ordered = [pool[i] for i in selected]
    # Append any items left when limited by `limit`, preserving relevance order,
    # so callers that ignore `limit` still receive every candidate.
    if limit >= len(pool):
        chosen = set(selected)
        ordered.extend(pool[i] for i in range(len(pool)) if i not in chosen)
    return ordered


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[T]],
    key_of: Callable[[T], Hashable],
    k: int = 60,
) -> list[T]:
    """Fuse several best-first ranked lists with Reciprocal Rank Fusion.

    Each candidate accumulates ``sum(1 / (k + rank))`` across the lists it
    appears in (rank is 1-based). RRF needs no score normalisation, which makes
    it robust when fusing arms with incomparable scales (BM25 vs. cosine).
    Ported from ruflo's ``reciprocalRankFusion``.

    Args:
        ranked_lists: lists of candidates, each already sorted best-first.
        key_of: returns a stable dedup key for a candidate (e.g. record id).
        k: RRF constant; ``60`` is the conventional default.

    Returns:
        A single fused list sorted by descending RRF score.
    """
    scores: dict[Hashable, float] = {}
    reps: dict[Hashable, T] = {}
    for ranked in ranked_lists:
        for rank, cand in enumerate(ranked):
            key = key_of(cand)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            reps.setdefault(key, cand)
    return [reps[key] for key, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]
