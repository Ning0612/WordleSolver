"""
Recommender module for Wordle Solver.

Phase 2: Scores and ranks all dictionary words (not just Phase 1 candidates)
to recommend optimal next guesses based on information gain.
"""

from typing import List, Tuple, Dict, Set, Optional
import json
from pathlib import Path

from constraints import Constraint
from stats import LetterStats


# Default weights (used if weights.json not found)
DEFAULT_WEIGHTS = {
    "green": 10.0,      # Letter already confirmed in correct position
    "yellow": 5.0,      # Letter confirmed but position unknown
    "gray": -5.0,       # Letter confirmed absent (should be negative)
    "unused": 8.0,      # New letter (high value for exploration)
    "exploration": 12.0,  # Bonus for unused letters in early rounds
    "duplicate_penalty": 15.0  # Penalty for duplicate letters in early rounds
}


class WordRecommender:
    """
    Recommends next guess words based on weighted scoring.

    Phase 2 Strategy:
    - Scores ALL words from dictionary (not just Phase 1 candidates)
    - Only excludes words where ALL letters are definitely absent
    - Balances exploration (new letters) vs exploitation (known positions)
    """

    def __init__(
        self,
        full_dictionary: List[str],
        stats: LetterStats,
        weights_file: Optional[str | Path] = None
    ):
        """
        Initialize recommender with dictionary, statistics, and weights.

        Args:
            full_dictionary: Complete word list
            stats: LetterStats instance for frequency data
            weights_file: Optional path to weights.json (uses defaults if not provided)
        """
        self.full_dictionary = full_dictionary
        self.stats = stats
        self.weights = self._load_weights(weights_file)

    def _load_weights(self, weights_file: Optional[str | Path]) -> Dict[str, float]:
        """
        Load weights from JSON file or use defaults.

        Args:
            weights_file: Path to weights JSON file

        Returns:
            Dictionary of weight values
        """
        if weights_file is None:
            return DEFAULT_WEIGHTS.copy()

        weights_path = Path(weights_file)
        if not weights_path.exists():
            print(f"Warning: Weights file not found: {weights_path}")
            print("Using default weights")
            return DEFAULT_WEIGHTS.copy()

        try:
            with open(weights_path, 'r') as f:
                loaded_weights = json.load(f)

            # Codex fix: Validate types and filter meta keys
            weights = DEFAULT_WEIGHTS.copy()

            for key in DEFAULT_WEIGHTS.keys():
                if key in loaded_weights:
                    value = loaded_weights[key]
                    # Validate type
                    if not isinstance(value, (int, float)):
                        print(f"Warning: Invalid type for weight '{key}': {type(value)}. Using default.")
                        continue
                    weights[key] = float(value)

            return weights

        except Exception as e:
            print(f"Warning: Failed to load weights from {weights_path}: {e}")
            print("Using default weights")
            return DEFAULT_WEIGHTS.copy()

    def recommend(
        self,
        candidates: List[str],
        constraint: Constraint,
        round_number: int,
        top_n: int = 5
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Recommend words split into Candidates and Explorations.

        Phase 2 Strategy:
        1. Build scorable set from FULL dictionary (not just candidates)
        2. Exclude only words where ALL letters are definitely absent
        3. Split scorable words into:
           - Candidates: Phase 1 filtered words (possible answers)
           - Explorations: Non-candidate words for information gain
        4. Score and return top N from each category

        Args:
            candidates: Phase 1 candidates (used for position frequency calculation)
            constraint: Current constraint from all rounds
            round_number: Current round number (1-indexed)
            top_n: Number of recommendations per category (default 5)

        Returns:
            Dict with "candidates" and "explorations" keys, each containing
            list of (word, score) tuples, sorted by score descending
        """
        # Validate inputs (Codex fix)
        if round_number < 1:
            raise ValueError(f"round_number must be >= 1, got {round_number}")
        if top_n < 1:
            raise ValueError(f"top_n must be >= 1, got {top_n}")

        # Step 1: Identify definitely absent letters (max_count == 0)
        definitely_absent = constraint.get_definitely_absent()

        # Step 2: Build scorable word set from full dictionary
        # CRITICAL FIX (per Codex review): Exclude words containing ANY gray letter
        # Not just words where ALL letters are gray
        scorable_words = []
        for word in self.full_dictionary:
            # Exclude word if it contains ANY definitely absent letter
            if not any(ch in definitely_absent for ch in word):
                scorable_words.append(word)

        # Step 3: Split scorable words into candidates and explorations
        candidates_set = set(candidates)  # Fast membership check
        candidate_words = [w for w in scorable_words if w in candidates_set]
        exploration_words = [w for w in scorable_words if w not in candidates_set]

        # Step 4: Get position frequencies (based on Phase 1 candidates)
        position_freqs = self.stats.get_position_frequencies(candidates)

        # Step 5: Score candidate words
        scored_candidates: List[Tuple[str, float]] = []
        for word in candidate_words:
            score = self._score_word(
                word=word,
                constraint=constraint,
                position_freqs=position_freqs,
                round_number=round_number
            )
            scored_candidates.append((word, score))

        # Step 6: Score exploration words
        scored_explorations: List[Tuple[str, float]] = []
        for word in exploration_words:
            score = self._score_word(
                word=word,
                constraint=constraint,
                position_freqs=position_freqs,
                round_number=round_number
            )
            scored_explorations.append((word, score))

        # Step 7: Sort and return top N from each category
        scored_candidates.sort(key=lambda x: (-x[1], x[0]))  # Score desc, word asc (stable)
        scored_explorations.sort(key=lambda x: (-x[1], x[0]))  # Score desc, word asc (stable)

        return {
            "candidates": scored_candidates[:top_n],
            "explorations": scored_explorations[:top_n]
        }

    def _score_word(
        self,
        word: str,
        constraint: Constraint,
        position_freqs: Dict[int, Dict[str, float]],
        round_number: int
    ) -> float:
        """
        Compute weighted score for a single word.

        Scoring formula:
        score = position_score
              + state_weight_score
              + exploration_bonus (if round <= 3)
              - duplicate_penalty (if round <= 3)

        Args:
            word: Word to score
            constraint: Current constraint
            position_freqs: Position-based letter frequencies
            round_number: Current round number (1-indexed)

        Returns:
            Weighted score (higher is better)
        """
        score = 0.0

        # Component 1: Position score (sum of letter frequencies at each position)
        position_score = 0.0
        for pos, letter in enumerate(word):
            # Get frequency for this letter at this position
            # Default to 0.0 if letter not found (shouldn't happen with full dict)
            freq = position_freqs[pos].get(letter, 0.0)
            position_score += freq

        score += position_score

        # Component 2: State weight score
        # Categorize each letter and apply corresponding weight
        state_score = 0.0
        unique_letters = set(word)

        # Collect known letter sets from constraint
        green_letters = set(constraint.greens.values())
        yellow_letters = set(constraint.yellows.keys())
        gray_letters = constraint.grays
        known_letters = green_letters | yellow_letters | gray_letters

        for letter in unique_letters:
            if letter in green_letters:
                state_score += self.weights["green"]
            elif letter in yellow_letters:
                state_score += self.weights["yellow"]
            elif letter in gray_letters:
                state_score += self.weights["gray"]  # Should be negative/zero
            else:
                # Unused letter - high value for exploration
                state_score += self.weights["unused"]

        score += state_score

        # Component 3: Exploration bonus (rounds 1-3 only)
        if round_number <= 3:
            # Count unique letters NOT in known set
            unused_letters = unique_letters - known_letters
            exploration_bonus = len(unused_letters) * self.weights["exploration"]
            score += exploration_bonus

        # Component 4: Duplicate penalty (rounds 1-3 only)
        if round_number <= 3:
            # Penalize duplicate letters (encourages exploring more letters)
            duplicate_count = 5 - len(unique_letters)  # 0 to 4

            # Exception: Reduce penalty if constraint shows min_count > 1 for any letter
            # (means we know there are duplicates in answer)
            for letter in unique_letters:
                if letter in constraint.letter_counts:
                    min_count, _ = constraint.letter_counts[letter]
                    if min_count > 1:
                        # Reduce penalty since duplicates might be beneficial
                        duplicate_count = max(0, duplicate_count - 1)

            duplicate_penalty = duplicate_count * self.weights["duplicate_penalty"]
            score -= duplicate_penalty

        return score


if __name__ == "__main__":
    from dictionary import get_word_list
    from constraints import FeedbackRound, FeedbackColor, merge_constraints

    print("=== Recommender Module Test ===\n")

    # Load dictionary
    words = get_word_list()
    print(f"Loaded {len(words)} words")

    # Initialize stats and recommender
    stats = LetterStats(words)
    recommender = WordRecommender(words, stats)

    # Test 1: Initial recommendations (no constraints, round 1)
    print("\n=== Test 1: Initial Recommendations (Round 1, No Constraints) ===")
    from constraints import Constraint
    empty_constraint = Constraint()
    initial_recs = recommender.recommend(words, empty_constraint, round_number=1, top_n=5)
    print(f"Candidates (Top 5): {len(initial_recs['candidates'])} words")
    for i, (word, score) in enumerate(initial_recs['candidates'], 1):
        print(f"  {i}. {word}: {score:.2f}")
    print(f"\nExplorations (Top 5): {len(initial_recs['explorations'])} words")
    for i, (word, score) in enumerate(initial_recs['explorations'], 1):
        print(f"  {i}. {word}: {score:.2f}")

    # Test 2: After one round with some constraints
    print("\n=== Test 2: Recommendations After Round 1 ===")
    print("Scenario: Guessed 'CRANE', got C=green, R=yellow, A=yellow, rest gray")
    round1 = FeedbackRound(
        guess="crane",
        feedback=[
            FeedbackColor.GREEN,   # C at position 0
            FeedbackColor.YELLOW,  # R exists elsewhere
            FeedbackColor.YELLOW,  # A exists elsewhere
            FeedbackColor.GRAY,    # N not in answer
            FeedbackColor.GRAY     # E not in answer
        ]
    )
    c1 = round1.to_constraint()

    # Get Phase 1 candidates for position frequency calculation
    from solver import filter_candidates
    candidates_r1 = filter_candidates(words, c1)
    print(f"Phase 1 candidates: {len(candidates_r1)}")

    recs_r1 = recommender.recommend(candidates_r1, c1, round_number=2, top_n=5)
    print(f"\nCandidates (Top 5): {len(recs_r1['candidates'])} words")
    for i, (word, score) in enumerate(recs_r1['candidates'], 1):
        print(f"  {i}. {word}: {score:.2f}")
    print(f"\nExplorations (Top 5): {len(recs_r1['explorations'])} words")
    for i, (word, score) in enumerate(recs_r1['explorations'], 1):
        print(f"  {i}. {word}: {score:.2f}")

    # Debug: Why are candidates 0?
    print("\n=== Debug: Constraint Analysis ===")
    print(f"Greens: {c1.greens}")
    print(f"Yellows: {c1.yellows}")
    print(f"Letter counts: {c1.letter_counts}")
    print(f"Grays: {c1.grays}")

    # Manually check a few words that should match
    print("\nManual word checks:")
    test_words = ["cargo", "carbo", "cards", "coral", "circa"]
    for word in test_words:
        from solver import _matches_constraint
        matches = _matches_constraint(word, c1)
        print(f"  {word}: {'MATCH' if matches else 'NO MATCH'}")

    # Test 3: Verify Phase 2 excludes words with ANY gray letter (Codex fix)
    print("\n=== Test 3: Phase 2 Exclusion Logic (Codex Fix Verification) ===")
    definitely_absent = c1.get_definitely_absent()
    print(f"Definitely absent letters (max_count==0): {definitely_absent}")

    # Check some test words
    test_words_phase2 = ["stink", "chunk", "ninja", "coral", "moral", "rapid", "squad"]
    print("\nTest words Phase 2 eligibility:")
    for word in test_words_phase2:
        has_gray = any(ch in definitely_absent for ch in word)
        eligible = "EXCLUDED" if has_gray else "Scorable"
        gray_letters = [ch for ch in word if ch in definitely_absent]
        print(f"  {word}: {eligible} (gray letters: {gray_letters if gray_letters else 'none'})")

    # Verify actual recommendations don't contain gray letters
    print("\nVerifying actual candidate recommendations:")
    for i, (word, score) in enumerate(recs_r1['candidates'][:5], 1):
        has_gray = any(ch in definitely_absent for ch in word)
        status = "ERROR" if has_gray else "OK"
        print(f"  {i}. {word}: {status}")

    print("\nVerifying actual exploration recommendations:")
    for i, (word, score) in enumerate(recs_r1['explorations'][:5], 1):
        has_gray = any(ch in definitely_absent for ch in word)
        status = "ERROR" if has_gray else "OK"
        print(f"  {i}. {word}: {status}")
