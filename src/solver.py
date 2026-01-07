"""
Solver module for Wordle Solver.

Phase 1: Candidate filtering based on constraints.
"""

from typing import List
from collections import Counter

from constraints import Constraint


def filter_candidates(words: List[str], constraint: Constraint) -> List[str]:
    """
    Filter word list to only candidates matching the constraint.

    Filtering rules:
    1. Green positions must match exactly
    2. Yellow letters must exist in word, but NOT at excluded positions
    3. Letter counts must satisfy min/max constraints
    4. Gray letters (max_count==0) must not appear

    Performance optimization (per Codex review):
    - Use Counter() once per word to avoid repeated word.count()

    Args:
        words: List of candidate words to filter
        constraint: Constraint to apply

    Returns:
        List of words matching all constraints
    """
    candidates = []

    for word in words:
        if _matches_constraint(word, constraint):
            candidates.append(word)

    return candidates


def _matches_constraint(word: str, constraint: Constraint) -> bool:
    """
    Check if a single word matches the constraint.

    Args:
        word: Word to check
        constraint: Constraint to match against

    Returns:
        True if word matches all constraints, False otherwise
    """
    # Rule 1: Check green positions
    for pos, letter in constraint.greens.items():
        if word[pos] != letter:
            return False

    # Precompute letter counts for efficiency (Codex optimization)
    word_counts = Counter(word)

    # Rule 2: Check yellows (must exist, not at excluded positions)
    for letter, excluded_positions in constraint.yellows.items():
        # Letter must exist in word
        if word_counts[letter] == 0:
            return False

        # Letter must not be at any excluded position
        for pos in excluded_positions:
            if word[pos] == letter:
                return False

    # Rule 3: Check letter count constraints
    for letter, (min_count, max_count) in constraint.letter_counts.items():
        actual_count = word_counts[letter]

        # Check minimum
        if actual_count < min_count:
            return False

        # Check maximum (if specified)
        if max_count is not None and actual_count > max_count:
            return False

    return True


if __name__ == "__main__":
    from constraints import FeedbackRound, FeedbackColor
    from dictionary import get_word_list

    print("=== Solver Test ===\n")

    # Load small subset for testing
    all_words = get_word_list()
    print(f"Total words in dictionary: {len(all_words)}")

    # Test case: First guess "CRANE" with specific feedback
    # Assume answer is "CARBY" - C at 0, A at 1, R at 2, B at 3, Y at 4
    print("\n=== Test: Answer is CARBY ===")
    print("Round 1: Guess CRANE")
    print("Feedback: C=green, R=yellow, A=yellow, N=gray, E=gray")

    round1 = FeedbackRound(
        guess="crane",
        feedback=[
            FeedbackColor.GREEN,   # C at position 0
            FeedbackColor.YELLOW,  # R exists but not at 1
            FeedbackColor.YELLOW,  # A exists but not at 2
            FeedbackColor.GRAY,    # N not in answer
            FeedbackColor.GRAY     # E not in answer
        ]
    )
    c1 = round1.to_constraint()

    candidates1 = filter_candidates(all_words, c1)
    print(f"Candidates after round 1: {len(candidates1)}")
    print(f"First 20: {candidates1[:20]}")
    print(f"'carby' in candidates: {'carby' in candidates1}")

    # Round 2: Guess "CARBS"
    print("\nRound 2: Guess CARBS")
    print("Feedback: C=green, A=green, R=green, B=yellow, S=gray")

    round2 = FeedbackRound(
        guess="carbs",
        feedback=[
            FeedbackColor.GREEN,   # C at position 0
            FeedbackColor.GREEN,   # A at position 1
            FeedbackColor.GREEN,   # R at position 2
            FeedbackColor.YELLOW,  # B exists but not at 3
            FeedbackColor.GRAY     # S not in answer
        ]
    )
    c2 = round2.to_constraint()
    merged = c1.merge(c2)

    candidates2 = filter_candidates(all_words, merged)
    print(f"Candidates after round 2: {len(candidates2)}")
    print(f"Candidates: {candidates2[:50]}")
    print(f"'carby' in candidates: {'carby' in candidates2}")

    # Test duplicate letter case
    print("\n=== Test: Duplicate Letter Handling ===")
    print("Guess: SPEED")
    print("Feedback: S=gray, P=gray, E=yellow (pos 2), E=gray (pos 3), D=gray")
    print("This means: exactly 1 E in answer, not at position 2")

    speed_round = FeedbackRound(
        guess="speed",
        feedback=[
            FeedbackColor.GRAY,    # S
            FeedbackColor.GRAY,    # P
            FeedbackColor.YELLOW,  # E at position 2
            FeedbackColor.GRAY,    # E at position 3
            FeedbackColor.GRAY     # D
        ]
    )
    speed_constraint = speed_round.to_constraint()
    print(f"Constraint letter_counts['e']: {speed_constraint.letter_counts.get('e')}")

    # Filter with a small test set
    test_words = ["creep", "ember", "enter", "venom", "plumb", "steel", "below", "melon"]
    filtered = filter_candidates(test_words, speed_constraint)
    print(f"Test words: {test_words}")
    print(f"Filtered (should have exactly 1 E, not at pos 2): {filtered}")
    print(f"Expected: venom, melon (exactly 1 E not at position 2)")
    print(f"Note: creep/ember/enter/steel have 2+ E's, plumb/below have E at pos 2")
