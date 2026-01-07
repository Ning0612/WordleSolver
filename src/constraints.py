"""
Constraints module for Wordle Solver.

Handles constraint representation, derivation from feedback, and merging logic.
Critical: Correctly handles duplicate letter feedback rules.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, Optional, List
from enum import Enum


class FeedbackColor(Enum):
    """Wordle feedback colors"""
    GREEN = "green"
    YELLOW = "yellow"
    GRAY = "gray"


@dataclass
class FeedbackRound:
    """
    Represents one round of guess and feedback.

    Handles the critical duplicate letter logic:
    - First identify all GREENs (exact matches)
    - Then allocate remaining letter counts to YELLOWs
    - Remaining instances become GRAY (indicating count limit)
    """
    guess: str
    feedback: List[FeedbackColor]

    def __post_init__(self):
        """Validate input"""
        if len(self.guess) != 5:
            raise ValueError(f"Guess must be 5 letters, got {len(self.guess)}: '{self.guess}'")
        if len(self.feedback) != 5:
            raise ValueError(f"Feedback must have 5 colors, got {len(self.feedback)}")
        if not self.guess.isalpha() or not self.guess.islower():
            raise ValueError(f"Guess must be lowercase alphabetic: '{self.guess}'")

        # Validate feedback types (Codex fix)
        for i, color in enumerate(self.feedback):
            if not isinstance(color, FeedbackColor):
                raise TypeError(
                    f"Feedback[{i}] must be FeedbackColor, got {type(color)}: {color}"
                )

    def to_constraint(self) -> 'Constraint':
        """
        Derive constraint from this feedback round.

        Key logic for duplicate letters:
        1. Process GREENs first (exact position matches)
        2. Count YELLOWs and GRAYs per letter
        3. For each letter:
           - min_count = greens + yellows
           - max_count = greens + yellows if any gray exists, else None

        Example: "SPEED" with feedback [GRAY, GRAY, YELLOW, GRAY, GRAY]
        - E at pos 2 is yellow, E at pos 3 is gray
        - This means: answer has exactly 1 E (the yellow one)
        - Constraint: letter_counts['e'] = (1, 1)
        - yellows['e'] = {2, 3} (exclude both yellow AND gray positions)

        Returns:
            Constraint object derived from this round
        """
        greens: Dict[int, str] = {}
        letter_counts: Dict[str, Tuple[int, Optional[int]]] = {}

        # Step 1: Process all feedback and collect positions
        green_count: Dict[str, int] = {}
        yellow_count: Dict[str, int] = {}
        gray_count: Dict[str, int] = {}
        yellow_positions: Dict[str, Set[int]] = {}  # Yellow positions only
        gray_positions: Dict[str, Set[int]] = {}    # Gray positions (may add later)

        for pos, (letter, color) in enumerate(zip(self.guess, self.feedback)):
            if color == FeedbackColor.GREEN:
                greens[pos] = letter
                green_count[letter] = green_count.get(letter, 0) + 1
            elif color == FeedbackColor.YELLOW:
                yellow_count[letter] = yellow_count.get(letter, 0) + 1
                if letter not in yellow_positions:
                    yellow_positions[letter] = set()
                yellow_positions[letter].add(pos)
            elif color == FeedbackColor.GRAY:
                gray_count[letter] = gray_count.get(letter, 0) + 1
                if letter not in gray_positions:
                    gray_positions[letter] = set()
                gray_positions[letter].add(pos)

        # Step 2: Derive letter_counts for each letter in guess
        for letter in set(self.guess):
            green_cnt = green_count.get(letter, 0)
            yellow_cnt = yellow_count.get(letter, 0)
            gray_cnt = gray_count.get(letter, 0)

            # Minimum count = greens + yellows (these are confirmed)
            min_count = green_cnt + yellow_cnt

            # Maximum count logic:
            # - If there are gray instances, max = min (count is exact)
            # - If no gray instances, max = None (could be more)
            if gray_cnt > 0:
                max_count = min_count
            else:
                max_count = None

            letter_counts[letter] = (min_count, max_count)

        # Step 3: Build yellows dict (position exclusions)
        # CRITICAL: Only add gray positions for letters that exist (min_count > 0)
        # This handles duplicate letters correctly without adding grays for absent letters
        yellows: Dict[str, Set[int]] = {}

        for letter in set(self.guess):
            min_count, _ = letter_counts[letter]

            # If letter exists in answer (min_count > 0)
            if min_count > 0:
                # Add yellow positions (always exclude)
                if letter in yellow_positions:
                    if letter not in yellows:
                        yellows[letter] = set()
                    yellows[letter] |= yellow_positions[letter]

                # Add gray positions too (for duplicate letter handling)
                # Example: SPEED with 1 yellow E + 1 gray E
                # Both positions should be excluded since answer has exactly 1 E
                if letter in gray_positions:
                    if letter not in yellows:
                        yellows[letter] = set()
                    yellows[letter] |= gray_positions[letter]

        return Constraint(
            greens=greens,
            yellows=yellows,
            letter_counts=letter_counts
        )


@dataclass
class Constraint:
    """
    Represents filtering constraints derived from Wordle feedback.

    Attributes:
        greens: Position-specific exact matches {position: letter}
        yellows: Letters that exist but not at certain positions {letter: excluded_positions}
        letter_counts: Letter count constraints {letter: (min, max)}
                       max=None means no upper limit yet
                       max=0 means letter definitely absent

    Note: 'grays' is a derived property, not stored separately to avoid inconsistency.
    """
    greens: Dict[int, str] = field(default_factory=dict)
    yellows: Dict[str, Set[int]] = field(default_factory=dict)
    letter_counts: Dict[str, Tuple[int, Optional[int]]] = field(default_factory=dict)

    @property
    def grays(self) -> Set[str]:
        """
        Derived property: letters with max_count == 0 (definitely absent).

        This is NOT manually maintained - always computed from letter_counts
        to avoid inconsistency issues.
        """
        return {letter for letter, (_, max_c) in self.letter_counts.items()
                if max_c == 0}

    def merge(self, other: 'Constraint') -> 'Constraint':
        """
        Merge this constraint with another from a different round.

        Merging rules:
        - greens: Union (conflict = user error, raise exception)
        - yellows: Union of excluded positions per letter
        - letter_counts:
          * min = max(min1, min2) - most restrictive lower bound
          * max = min(max1, max2) - most restrictive upper bound (handle None)

        Args:
            other: Another Constraint to merge with

        Returns:
            New merged Constraint

        Raises:
            ValueError: If greens conflict (same position, different letter)
        """
        # Merge greens - detect conflicts
        merged_greens = dict(self.greens)
        for pos, letter in other.greens.items():
            if pos in merged_greens and merged_greens[pos] != letter:
                raise ValueError(
                    f"Conflicting green constraints at position {pos}: "
                    f"'{merged_greens[pos]}' vs '{letter}'. "
                    f"Check feedback input for errors."
                )
            merged_greens[pos] = letter

        # Merge yellows - union of excluded positions
        merged_yellows: Dict[str, Set[int]] = {}
        all_letters = set(self.yellows.keys()) | set(other.yellows.keys())
        for letter in all_letters:
            positions = set()
            if letter in self.yellows:
                positions |= self.yellows[letter]
            if letter in other.yellows:
                positions |= other.yellows[letter]
            if positions:
                merged_yellows[letter] = positions

        # Detect green/yellow conflicts (Codex fix)
        for pos, letter in merged_greens.items():
            if letter in merged_yellows and pos in merged_yellows[letter]:
                raise ValueError(
                    f"Conflicting constraints for letter '{letter}': "
                    f"GREEN at position {pos} but YELLOW excludes position {pos}. "
                    f"Check feedback input for errors."
                )

        # Merge letter_counts
        merged_counts: Dict[str, Tuple[int, Optional[int]]] = {}
        all_letters_counts = set(self.letter_counts.keys()) | set(other.letter_counts.keys())

        for letter in all_letters_counts:
            min1, max1 = self.letter_counts.get(letter, (0, None))
            min2, max2 = other.letter_counts.get(letter, (0, None))

            # min = max(min1, min2)
            merged_min = max(min1, min2)

            # max = min(max1, max2), handling None
            if max1 is None and max2 is None:
                merged_max = None
            elif max1 is None:
                merged_max = max2
            elif max2 is None:
                merged_max = max1
            else:
                merged_max = min(max1, max2)

            # Sanity check: min <= max
            if merged_max is not None and merged_min > merged_max:
                raise ValueError(
                    f"Impossible constraint for letter '{letter}': "
                    f"min={merged_min} > max={merged_max}. "
                    f"Check feedback input for errors."
                )

            merged_counts[letter] = (merged_min, merged_max)

        return Constraint(
            greens=merged_greens,
            yellows=merged_yellows,
            letter_counts=merged_counts
        )

    def get_definitely_absent(self) -> Set[str]:
        """
        Get letters that are definitely absent (max_count == 0).

        Used for Phase 2 recommendation filtering.

        Returns:
            Set of letters with max_count == 0
        """
        return self.grays


def merge_constraints(constraints: List[Constraint]) -> Constraint:
    """
    Merge multiple constraints from different rounds.

    Args:
        constraints: List of Constraint objects to merge

    Returns:
        Single merged Constraint

    Raises:
        ValueError: If empty list or conflicts detected
    """
    if not constraints:
        raise ValueError("Cannot merge empty constraint list")

    if len(constraints) == 1:
        return constraints[0]

    result = constraints[0]
    for constraint in constraints[1:]:
        result = result.merge(constraint)

    return result


if __name__ == "__main__":
    # Test duplicate letter handling
    print("=== Test 1: SPEED with 1 yellow E + 1 gray E ===")
    feedback_round = FeedbackRound(
        guess="speed",
        feedback=[
            FeedbackColor.GRAY,    # S
            FeedbackColor.GRAY,    # P
            FeedbackColor.YELLOW,  # E (position 2)
            FeedbackColor.GRAY,    # E (position 3)
            FeedbackColor.GRAY     # D
        ]
    )
    constraint = feedback_round.to_constraint()
    print(f"letter_counts['e']: {constraint.letter_counts.get('e')}")
    print(f"Expected: (1, 1)")
    print(f"grays: {constraint.grays}")
    print(f"'e' in grays: {'e' in constraint.grays}")
    print(f"Expected: False (e exists, just limited to 1)\n")

    print("=== Test 2: SPEED with 1 green E + 1 yellow E ===")
    feedback_round2 = FeedbackRound(
        guess="speed",
        feedback=[
            FeedbackColor.GRAY,    # S
            FeedbackColor.GRAY,    # P
            FeedbackColor.GREEN,   # E (position 2)
            FeedbackColor.YELLOW,  # E (position 3)
            FeedbackColor.GRAY     # D
        ]
    )
    constraint2 = feedback_round2.to_constraint()
    print(f"letter_counts['e']: {constraint2.letter_counts.get('e')}")
    print(f"Expected: (2, None) - at least 2 E's, could be more")
    print(f"greens: {constraint2.greens}")
    print(f"yellows: {constraint2.yellows}\n")

    print("=== Test 3: Merge constraints ===")
    # Answer could be "CROWN" - C at 0, R at 1, A somewhere
    round1 = FeedbackRound(
        guess="crane",
        feedback=[FeedbackColor.GREEN,   # C at position 0
                  FeedbackColor.YELLOW,  # R exists but not at position 1
                  FeedbackColor.YELLOW,  # A exists but not at position 2
                  FeedbackColor.GRAY,    # N not in answer
                  FeedbackColor.GRAY]    # E not in answer
    )
    round2 = FeedbackRound(
        guess="grows",
        feedback=[FeedbackColor.GRAY,    # G not in answer
                  FeedbackColor.GREEN,   # R at position 1
                  FeedbackColor.GRAY,    # O not in answer
                  FeedbackColor.GRAY,    # W not in answer
                  FeedbackColor.GRAY]    # S not in answer
    )
    c1 = round1.to_constraint()
    c2 = round2.to_constraint()
    merged = c1.merge(c2)
    print(f"Merged greens: {merged.greens}")
    print(f"Expected: {{0: 'c', 1: 'r'}}")
    print(f"Merged yellows: {merged.yellows}")
    print(f"Expected: {{'r': {{1}}, 'a': {{2}}}}")
    print(f"Merged letter_counts['r']: {merged.letter_counts.get('r')}")
    print(f"Expected: (1, None) - R confirmed at position 1, min=1")
