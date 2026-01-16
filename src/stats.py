"""
Stats module for Wordle Solver.

Provides statistical analysis and frequency calculations for candidate words.
Implements caching strategy based on candidate set identity.
"""

from typing import List, Dict, Tuple, FrozenSet
from collections import Counter


class LetterStats:
    """
    Computes and caches letter frequency statistics for word lists.

    Uses position-based frequency analysis to help identify high-value guesses.
    Implements caching based on frozenset (Codex fix: avoids hash collision).
    """

    def __init__(self, full_dictionary: List[str]):
        """
        Initialize with full dictionary for fallback statistics.

        Args:
            full_dictionary: Complete word list for fallback when candidates are few
        """
        self.full_dictionary = full_dictionary
        # Codex fix: Use frozenset as key instead of hash to avoid collisions
        self._cache: Dict[FrozenSet[str], Dict[int, Dict[str, float]]] = {}

        # Precompute full dictionary stats at startup (used as fallback)
        self._full_dict_stats = self._compute_position_frequencies(full_dictionary)

    def _compute_position_frequencies(
        self,
        words: List[str]
    ) -> Dict[int, Dict[str, float]]:
        """
        Compute letter frequency at each position.

        Args:
            words: List of words to analyze

        Returns:
            Dictionary mapping {position: {letter: frequency}}
            where frequency = count / total_words

        Example:
            {0: {'a': 0.15, 'b': 0.08, ...}, 1: {...}, ...}
        """
        if not words:
            return {pos: {} for pos in range(5)}

        total_words = len(words)
        position_counts: Dict[int, Counter] = {pos: Counter() for pos in range(5)}

        # Count letter occurrences at each position
        for word in words:
            for pos, letter in enumerate(word):
                position_counts[pos][letter] += 1

        # Convert counts to frequencies
        position_frequencies: Dict[int, Dict[str, float]] = {}
        for pos in range(5):
            position_frequencies[pos] = {
                letter: count / total_words
                for letter, count in position_counts[pos].items()
            }

        return position_frequencies

    def get_position_frequencies(
        self,
        candidates: List[str],
        min_candidates_threshold: int = 5  # Optimization 3: 降低閾值以更早使用候選統計
    ) -> Dict[int, Dict[str, float]]:
        """
        Get position-based letter frequencies for given candidates.

        Uses caching to avoid redundant calculations.
        Falls back to full dictionary stats if candidates are too few.

        Args:
            candidates: Current candidate word list
            min_candidates_threshold: Minimum candidates to use candidate-based stats
                                     (default: 10). Below this, use full dictionary.

        Returns:
            Position frequency dictionary

        Strategy (per Codex review):
        - If candidates >= threshold: use candidate-specific frequencies (more precise)
        - If candidates < threshold: use full dictionary frequencies (more stable)
        """
        # Fallback to full dictionary if candidates too few
        if len(candidates) < min_candidates_threshold:
            return self._full_dict_stats

        # Generate cache key based on candidate set identity
        # Codex fix: Use frozenset directly as key (not hash) to avoid collisions
        cache_key = frozenset(candidates)

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Compute and cache
        frequencies = self._compute_position_frequencies(candidates)
        self._cache[cache_key] = frequencies

        return frequencies

    def get_overall_letter_frequency(self, words: List[str]) -> Dict[str, float]:
        """
        Compute overall letter frequency across all positions.

        Used for fallback scoring when position-specific data is unavailable.

        Args:
            words: Word list to analyze

        Returns:
            Dictionary mapping {letter: frequency}
        """
        if not words:
            return {}

        total_letters = len(words) * 5  # Each word has 5 letters
        letter_counts: Counter = Counter()

        for word in words:
            letter_counts.update(word)

        return {
            letter: count / total_letters
            for letter, count in letter_counts.items()
        }

    def clear_cache(self):
        """Clear the frequency cache."""
        self._cache.clear()

    def get_cache_size(self) -> int:
        """Get number of cached frequency sets."""
        return len(self._cache)


if __name__ == "__main__":
    from dictionary import get_word_list

    print("=== Stats Module Test ===\n")

    # Load dictionary
    words = get_word_list()
    print(f"Loaded {len(words)} words")

    # Initialize stats
    stats = LetterStats(words)

    # Test 1: Full dictionary statistics
    print("\n=== Test 1: Full Dictionary Position Frequencies ===")
    full_freqs = stats.get_position_frequencies(words)
    print(f"Position 0 top 5 letters:")
    pos0_sorted = sorted(full_freqs[0].items(), key=lambda x: x[1], reverse=True)[:5]
    for letter, freq in pos0_sorted:
        print(f"  {letter}: {freq:.4f}")

    # Test 2: Small candidate set (should use full dict fallback)
    print("\n=== Test 2: Small Candidate Set (< 10 words) ===")
    small_candidates = ["crane", "crate", "craze", "grace", "brace"]
    small_freqs = stats.get_position_frequencies(small_candidates)
    print(f"Candidates: {small_candidates}")
    print(f"Uses full dict fallback: {small_freqs == stats._full_dict_stats}")
    print(f"Cache size: {stats.get_cache_size()}")

    # Test 3: Large candidate set (should compute and cache)
    print("\n=== Test 3: Large Candidate Set (>= 10 words) ===")
    large_candidates = [w for w in words if w.startswith('c')][:50]
    print(f"Candidates: {len(large_candidates)} words starting with 'c'")
    large_freqs = stats.get_position_frequencies(large_candidates)
    print(f"Position 0 top 5 letters:")
    pos0_sorted = sorted(large_freqs[0].items(), key=lambda x: x[1], reverse=True)[:5]
    for letter, freq in pos0_sorted:
        print(f"  {letter}: {freq:.4f}")
    print(f"Cache size after computation: {stats.get_cache_size()}")

    # Test 4: Cache hit
    print("\n=== Test 4: Cache Hit Test ===")
    print("Requesting same candidate set again...")
    large_freqs_cached = stats.get_position_frequencies(large_candidates)
    print(f"Same result: {large_freqs == large_freqs_cached}")
    print(f"Cache size (unchanged): {stats.get_cache_size()}")

    # Test 5: Overall letter frequency
    print("\n=== Test 5: Overall Letter Frequency ===")
    overall = stats.get_overall_letter_frequency(words)
    overall_sorted = sorted(overall.items(), key=lambda x: x[1], reverse=True)[:10]
    print("Top 10 most frequent letters:")
    for letter, freq in overall_sorted:
        print(f"  {letter}: {freq:.4f}")
