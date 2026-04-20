"""Compatibility matching for `compatible_with` patterns.

## Matching rule (documented)

An entry `A` (area or room) has a list of patterns in `compatible_with`.
A pattern is one of:

- an exact id (`"swamp.witch_hut"`) — matches that id literally
- a dotted glob (`"swamp.*"`, `"ruin.*"`) — matches if the *candidate's*
  biome equals the glob's head, OR if any of the candidate's tags equals
  the glob's head, OR if its id starts with `"<head>."` (i.e. the id's
  dotted namespace prefix matches), OR if `fnmatch` of the id against
  the raw pattern matches
- a bare token (`"path"`, `"overgrown"`) — matches if any of the
  candidate's tags equals the token, or its biome equals the token, or
  its id contains the token

Two entries A and B are **compatible** iff
A matches any pattern in B.compatible_with, OR
B matches any pattern in A.compatible_with.

This bidirectional rule is taken verbatim from the generator task spec.

### Why not plain fnmatch?

The catalog idioms use `"forest.*"` to mean "anything forest-flavored"
— but area ids look like `"area.barrow_swamp"`, not `"swamp.*"`. Plain
`fnmatch("area.barrow_swamp", "swamp.*")` is False. Matching on the
candidate's *biome* and *tags* — which are what `"swamp.*"` conceptually
refers to — is what the content authors actually meant.

### Determinism

This module is pure / stateless. No randomness.
"""

from __future__ import annotations

import fnmatch
from typing import Any


def _candidate_tokens(entry: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    """Extract (id, biome, tags) from an entry, defaulting missing to ''/()."""
    eid = str(entry.get("id", ""))
    biome = str(entry.get("biome", ""))
    tags = tuple(str(t) for t in (entry.get("tags") or ()))
    return eid, biome, tags


def _pattern_matches(pattern: str, candidate: dict[str, Any]) -> bool:
    """True iff `pattern` matches anything about `candidate`.

    See module docstring for the full rule. In plain English:

    - dotted glob (`swamp.*`): head must equal candidate biome, or a
      candidate tag, or be an id-namespace prefix, or fnmatch the id.
    - exact id or bare token: matches id equality, biome equality,
      any-tag equality, or a substring of the id.
    """
    if not pattern:
        return False
    cid, cbiome, ctags = _candidate_tokens(candidate)

    if "*" in pattern or "?" in pattern or "[" in pattern:
        # Glob case. Prefer semantic match on the head before falling back
        # to literal fnmatch on the id.
        head, _, _tail = pattern.partition(".")
        if head:
            if head == cbiome:
                return True
            if head in ctags:
                return True
            if cid.startswith(head + "."):
                return True
            # Also: area ids like `area.barrow_swamp` — head `swamp` isn't
            # a prefix of the id, so match on the underscored segment.
            # e.g. pattern `swamp.*` vs id `area.barrow_swamp` → check
            # if `swamp` is a token in the id (after splitting on non-alnum).
            if any(part == head for part in cid.replace(".", "_").split("_")):
                return True
        # Fallback: literal fnmatch of the id.
        return fnmatch.fnmatchcase(cid, pattern)

    # Non-glob: exact match against id, biome, tags, or substring in id.
    if pattern == cid:
        return True
    if pattern == cbiome:
        return True
    if pattern in ctags:
        return True
    if pattern in cid:
        return True
    return False


def matches_any(candidate: dict[str, Any], patterns: list[str]) -> bool:
    """True iff `candidate` matches any pattern in `patterns`."""
    if not patterns:
        return False
    for p in patterns:
        if _pattern_matches(str(p), candidate):
            return True
    return False


def compatible(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Bidirectional compatibility check per the task's prescribed rule."""
    a_pats = [str(p) for p in (a.get("compatible_with") or ())]
    b_pats = [str(p) for p in (b.get("compatible_with") or ())]
    return matches_any(b, a_pats) or matches_any(a, b_pats)
