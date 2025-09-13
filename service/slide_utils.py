# slide_utils.py
"""
Functions to slice text_chunks into slides with natural phrasing:
- At most two lines per slide
- At most ~33 characters per line (tunable)
- Avoid slides with single words or very short phrases

Each slide dict has:
  - text: a string with 1–2 lines separated by newline
  - style: 'content' (for PPT generator)
"""
from typing import List, Dict, Tuple, Set, Optional


def _split_long_word(word: str, max_chars: int) -> List[str]:
    """
    Break a single word into multiple chunks of at most max_chars.
    """
    return [word[i:i+max_chars] for i in range(0, len(word), max_chars)]


def _wrap_part_to_lines(part: str, max_chars: int, target_chars: int, min_words_per_line: int) -> List[str]:
    """Word-wrap a single part into lines using DP to minimize raggedness.

    Penalizes very short lines and one-word lines to avoid awkward slides.
    """
    words = part.strip().split()
    # Split overly long words into smaller tokens
    tokens: List[str] = []
    for w in words:
        if len(w) > max_chars:
            tokens.extend(_split_long_word(w, max_chars))
        else:
            tokens.append(w)

    n = len(tokens)
    if n == 0:
        return []

    INF = 10**12
    dp = [INF] * (n + 1)
    nxt = [-1] * (n + 1)
    dp[n] = 0

    # Precompute token lengths for quick line length calculation
    lens = [len(t) for t in tokens]

    BAD_END_WORDS = {
        "and", "or", "but", "a", "an", "the", "to", "we", "i",
        "of", "in", "on", "at", "for", "with", "by", "as", "from",
        "that"
    }

    for i in range(n - 1, -1, -1):
        line_len = 0
        for j in range(i, n):
            # Add token and a space if not the first token on the line
            line_len += lens[j] + (0 if j == i else 1)
            if line_len > max_chars:
                break
            words_cnt = j - i + 1
            slack = max(target_chars - line_len, 0)
            penalty = slack * slack
            if words_cnt < min_words_per_line:
                penalty += 200
            if words_cnt == 1:
                penalty += 800
            # Discourage lines that end with weak function words
            last_word = tokens[j].rstrip(',;:').lower()
            if last_word in BAD_END_WORDS:
                penalty += 180
            cost = penalty + dp[j + 1]
            if cost < dp[i]:
                dp[i] = cost
                nxt[i] = j + 1

    # Reconstruct lines
    lines: List[str] = []
    i = 0
    while i < n and nxt[i] != -1:
        j = nxt[i]
        lines.append(" ".join(tokens[i:j]))
        i = j
    if i < n:  # fallback, shouldn't happen
        lines.append(" ".join(tokens[i:]))
    return lines


def _group_lines_into_slides(
    lines: List[str],
    max_lines_per_slide: int,
    max_chars: int,
    target_chars: int,
    min_words_per_line: int,
    min_words_per_slide: int,
    forced_first_line: Optional[Set[int]] = None,
) -> List[List[str]]:
    """Group wrapped lines into slides (1–2 lines) via DP to minimize badness."""
    m = len(lines)
    if m == 0:
        return []

    lens = [len(s) for s in lines]
    words = [len(s.split()) for s in lines]

    def slide_penalty(i: int, k: int) -> int:
        # k = number of lines in this slide (1 or 2)
        assert 1 <= k <= max_lines_per_slide
        # Base penalty strongly favors two-line slides
        base = 120 if k == 1 else 0
        # Line raggedness
        rag = 0
        for t in range(k):
            slack = max(target_chars - lens[i + t], 0)
            rag += slack * slack
            if words[i + t] < min_words_per_line:
                rag += 120
            if words[i + t] == 1:
                rag += 1000
        # Single-line slides must be reasonably substantive
        if k == 1 and words[i] < min_words_per_slide:
            base += 280
        # Discourage pairing a full-stop ending with a following line
        end_punct = lines[i].rstrip().endswith(('.', '!', '?'))
        if k == 2 and end_punct:
            base += 140
        # But allow a single-line slide if it ends a sentence and is long enough
        if k == 1 and end_punct and words[i] >= min_words_per_slide:
            base = max(0, base - 120)
        # Mild penalty for very imbalanced two-line slides
        if k == 2 and abs(lens[i] - lens[i + 1]) >= 12:
            base += 25
        return base + rag

    INF = 10**12
    dp = [INF] * (m + 1)
    choice = [0] * (m + 1)
    dp[m] = 0
    forced_first_line = forced_first_line or set()
    for i in range(m - 1, -1, -1):
        # Option 1: single-line slide
        best = slide_penalty(i, 1) + dp[i + 1]
        pick = 1
        # Option 2: two-line slide if possible
        if i + 1 < m and (i + 1) not in forced_first_line:
            cost2 = slide_penalty(i, 2) + dp[i + 2]
            if cost2 < best:
                best = cost2
                pick = 2
        dp[i] = best
        choice[i] = pick

    # Reconstruct slide line groups
    slides: List[List[str]] = []
    i = 0
    while i < m:
        k = choice[i] if choice[i] else 1
        slides.append(lines[i:i + k])
        i += k
    return slides


def slice_into_slides(
    text_chunks: List[str],
    max_chars: int = 33,
    max_lines: int = 2,
    min_words_per_line: int = 3,
    min_words_per_slide: int = 5,
    force_new_slide_prefixes: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """
    Convert a list of paragraphs (text_chunks) into a list of slides,
    each obeying the constraints:
      - <= max_lines lines per slide
      - <= max_chars characters per line

    Returns:
        List of dicts with keys:
          - 'text': slide text (lines joined by '\n')
          - 'style': 'content'
    """
    target_chars = max(1, max_chars - 2)

    # 1) Wrap each chunk into lines using DP wrapper, respecting explicit newlines
    all_lines: List[str] = []
    for chunk in text_chunks:
        parts = [p for p in chunk.splitlines() if p.strip()] or [chunk]
        for part in parts:
            all_lines.extend(_wrap_part_to_lines(part, max_chars, target_chars, min_words_per_line))

    # 2) Compute indices that must start a new slide (marker-prefixed lines)
    force_new_slide_prefixes = force_new_slide_prefixes or []
    def is_marker_line(s: str) -> bool:
        st = s.lstrip()
        return any(st.startswith(p) for p in force_new_slide_prefixes)

    forced_first: Set[int] = {i for i, s in enumerate(all_lines) if is_marker_line(s)}

    # 3) Group the lines into slides via DP with forced boundaries
    grouped = _group_lines_into_slides(
        all_lines,
        max_lines_per_slide=max_lines,
        max_chars=max_chars,
        target_chars=target_chars,
        min_words_per_line=min_words_per_line,
        min_words_per_slide=min_words_per_slide,
        forced_first_line=forced_first,
    )

    # 4) Build slide dicts
    slides: List[Dict[str, str]] = []
    for lines in grouped:
        slides.append({"text": "\n ".join(lines), "style": "content"})
    return slides
