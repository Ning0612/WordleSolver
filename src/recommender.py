"""
Recommender module for Wordle Solver.

Phase 2: Scores and ranks all dictionary words (not just Phase 1 candidates)
to recommend optimal next guesses based on information gain.
"""

from typing import List, Tuple, Dict, Set, Optional
import json
import heapq
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass

from constraints import Constraint
from stats import LetterStats


@dataclass
class ScoringContext:
    """
    封裝評分所需的所有上下文資訊。
    
    將多個參數封裝為單一物件，簡化 API 並提升可維護性。
    """
    position_freqs: Dict[int, Dict[str, float]]
    round_number: int
    constraint: Constraint
    
    # 預計算的字母集合（Phase 1 優化：避免在 _score_word 中重複建立）
    green_letters: Set[str]
    yellow_letters: Set[str]
    gray_letters: Set[str]
    known_letters: Set[str]
    
    # Trap Pattern Detection（陷阱模式偵測）
    is_trap_situation: bool = False  # 是否處於陷阱情境（綠色 ≥ 3）
    trap_variable_positions: Set[int] = None  # 變動位置（非綠色位置）
    trap_test_letters: Set[str] = None  # 需測試的字母（候選詞在變動位置的字母）
    
    def __post_init__(self):
        """初始化預設值"""
        if self.trap_variable_positions is None:
            self.trap_variable_positions = set()
        if self.trap_test_letters is None:
            self.trap_test_letters = set()


# Position score multiplier (Optimization 1)
POSITION_WEIGHT_MULTIPLIER = 2.0  # 略小於狀態權重，達成適度平衡

# Default weights (used if weights.json not found)
DEFAULT_WEIGHTS = {
    "green": 10.0,      # Letter already confirmed in correct position
    "yellow": 5.0,      # Letter confirmed but position unknown
    "gray": -5.0,       # Letter confirmed absent (should be negative)
    "unused": 8.0,      # New letter (high value for exploration)
    "exploration": 12.0,  # Bonus for unused letters (exploration category)
    "duplicate_penalty": 15.0  # Penalty for duplicate letters (exploration category)
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
        
        # Phase 2 Optimization: Build letter index for fast exploration pool filtering
        self._letter_index = self._build_letter_index()

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

    def _build_letter_index(self) -> Dict[str, Set[str]]:
        """
        Build letter index for Phase 2 optimization.
        
        Creates a mapping from each letter to the set of words containing it.
        This enables O(M × K) filtering instead of O(N × L × M) where:
        - M = number of gray letters (typically 5-15)
        - K = average words per letter (~3000)
        - N = dictionary size (15921)
        - L = word length (5)
        
        Returns:
            Dictionary mapping {letter: set of words containing that letter}
        """
        index = defaultdict(set)
        for word in self.full_dictionary:
            for letter in set(word):  # Use set to avoid duplicates for words like "speed"
                index[letter].add(word)
        return dict(index)  # Convert to regular dict for clarity
    
    def _get_exploration_pool(self, definitely_absent: Set[str]) -> List[str]:
        """
        Get exploration pool by excluding words with gray letters.
        
        Phase 2 Optimization: Uses letter index for fast filtering.
        
        Args:
            definitely_absent: Set of letters with max_count == 0 (gray letters)
        
        Returns:
            List of words not containing any definitely absent letters
        """
        if not definitely_absent:
            return self.full_dictionary
        
        # Use letter index to find all words to exclude
        excluded = set()
        for letter in definitely_absent:
            if letter in self._letter_index:
                excluded.update(self._letter_index[letter])
        
        # Return words not in excluded set
        return [w for w in self.full_dictionary if w not in excluded]

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
        
        # ✨ 驗證: 檢查候選數量（在計算分數前）
        if not candidates or len(candidates) == 0:
            raise ValueError(
                "找不到符合條件的候選單字。\n"
                "這可能是因為顏色標記有誤，或答案不在詞庫中。"
            )
        
        # ✨ 驗證: 檢查約束條件合法性（在計算分數前）
        for letter, (min_count, max_count) in constraint.letter_counts.items():
            if max_count is not None and min_count > max_count:
                raise ValueError(
                    f"約束條件矛盾: 字母 '{letter}' 的 min={min_count} > max={max_count}。\n"
                    "這通常是因為顏色標記有誤。"
                )

        # Step 1: Identify definitely absent letters (max_count == 0)
        definitely_absent = constraint.get_definitely_absent()

        # Phase 2 Optimization: Use letter index for fast exploration pool filtering
        # OLD: O(N × L × M) iteration over all words
        # NEW: O(M × K) where K = avg words per letter (~3000 vs 15921)
        exploration_pool = self._get_exploration_pool(definitely_absent)
        
        # Step 2: Split into candidates and explorations
        candidates_set = set(candidates)  # Fast membership check
        
        # Candidates should also exclude gray letters (Phase 1 already filtered them)
        candidate_words = [w for w in candidates if w in candidates_set]
        
        # Explorations: words in pool but not in candidates
        exploration_words = [w for w in exploration_pool if w not in candidates_set]

        # Step 4: Get position frequencies (based on Phase 1 candidates)
        position_freqs = self.stats.get_position_frequencies(candidates)

        # Step 4.5: Trap Pattern Detection（陷阱模式偵測）
        trap_info = self._detect_trap_pattern(candidates, constraint)

        # Create ScoringContext (封裝所有評分所需資訊)
        green_letters = set(constraint.greens.values())
        yellow_letters = set(constraint.yellows.keys())
        gray_letters = constraint.grays
        known_letters = green_letters | yellow_letters | gray_letters
        
        context = ScoringContext(
            position_freqs=position_freqs,
            round_number=round_number,
            constraint=constraint,
            green_letters=green_letters,
            yellow_letters=yellow_letters,
            gray_letters=gray_letters,
            known_letters=known_letters,
            # Trap Pattern Detection
            is_trap_situation=trap_info['is_trap'],
            trap_variable_positions=trap_info['variable_positions'],
            trap_test_letters=trap_info['test_letters']
        )

        # Step 5: Score candidate words (Exploitation strategy - no exploration logic)
        scored_candidates: List[Tuple[str, float]] = []
        for word in candidate_words:
            score = self._score_word(
                word=word,
                context=context,
                is_exploration=False  # Candidates: 不啟用探索邏輯
            )
            scored_candidates.append((word, score))

        # Step 6: Score exploration words (Exploration strategy - always enable exploration logic)
        scored_explorations: List[Tuple[str, float]] = []
        for word in exploration_words:
            score = self._score_word(
                word=word,
                context=context,
                is_exploration=True  # Explorations: 永遠啟用探索邏輯
            )
            scored_explorations.append((word, score))

        # Phase 1 Optimization: Use heapq.nlargest instead of full sort
        # For N=10000, K=5: reduces from O(N log N) to O(N + K log N)
        # This is ~92% fewer comparisons for typical use case
        top_candidates = heapq.nlargest(
            top_n,
            scored_candidates,
            key=lambda x: (x[1], -sum(ord(c) for c in x[0]))  # score desc, word asc
        )
        
        top_explorations = heapq.nlargest(
            top_n,
            scored_explorations,
            key=lambda x: (x[1], -sum(ord(c) for c in x[0]))  # score desc, word asc
        )

        return {
            "candidates": top_candidates,
            "explorations": top_explorations
        }

    def _detect_trap_pattern(
        self,
        candidates: List[str],
        constraint: Constraint
    ) -> Dict[str, any]:
        """
        偵測是否處於陷阱模式情境。
        
        陷阱情境定義：
        - 綠色字母 ≥ 3 個時，候選詞可能共享同一模板（如 _IGHT）
        - 需要優先測試在非模板位置的差異字母
        
        Args:
            candidates: 當前候選詞列表
            constraint: 約束條件
            
        Returns:
            {
                'is_trap': bool,  # 是否處於陷阱情境
                'variable_positions': Set[int],  # 非綠色的位置
                'test_letters': Set[str]  # 候選詞在變動位置的所有可能字母
            }
        """
        green_count = len(constraint.greens)
        
        # 條件：綠色字母 < 3，不啟用陷阱偵測
        if green_count < 3:
            return {
                'is_trap': False,
                'variable_positions': set(),
                'test_letters': set()
            }
        
        # 找出非綠色位置（變動位置）
        all_positions = set(range(5))
        green_positions = set(constraint.greens.keys())
        variable_positions = all_positions - green_positions
        
        # 收集候選詞在變動位置的所有字母
        test_letters = set()
        for word in candidates:
            for pos in variable_positions:
                test_letters.add(word[pos])
        
        return {
            'is_trap': True,
            'variable_positions': variable_positions,
            'test_letters': test_letters
        }

    def _score_word(
        self,
        word: str,
        context: ScoringContext,
        is_exploration: bool = False
    ) -> float:
        """
        計算單字評分（Category-based exploration logic）。

        評分公式：
        score = position_score (× 2)
              + state_weight_score
              + exploration_bonus (if is_exploration)
              - duplicate_penalty (if is_exploration)

        Args:
            word: 待評分單字
            context: 評分上下文（封裝所有必要資訊）
            is_exploration: True 表示探索類別（Explorations），永遠啟用探索邏輯
                          False 表示候選類別（Candidates），不啟用探索邏輯

        Returns:
            加權分數（越高越好）
        """
        score = 0.0
        unique_letters = set(word)

        # Component 1: Position score (Optimization 1: × 2 multiplier)
        position_score = 0.0
        for pos, letter in enumerate(word):
            freq = context.position_freqs[pos].get(letter, 0.0)
            position_score += freq
        
        position_score *= POSITION_WEIGHT_MULTIPLIER  # × 2
        score += position_score

        # Component 2: State weight score
        state_score = 0.0
        for letter in unique_letters:
            if letter in context.green_letters:
                state_score += self.weights["green"]
            elif letter in context.yellow_letters:
                state_score += self.weights["yellow"]
            elif letter in context.gray_letters:
                state_score += self.weights["gray"]
            else:
                state_score += self.weights["unused"]
        score += state_score

        # Component 3 & 4: Exploration logic (Optimization 4: category-based)
        if is_exploration:
            # Component 3: Exploration bonus (always enabled for Explorations)
            unused_letters = unique_letters - context.known_letters
            exploration_bonus = len(unused_letters) * self.weights["exploration"]
            score += exploration_bonus

            # Component 4: Duplicate penalty (always enabled for Explorations)
            duplicate_count = 5 - len(unique_letters)  # 0 to 4
            
            # Optimization 2: 減免已知重複字母的懲罰
            for letter in unique_letters:
                if letter in context.constraint.letter_counts:
                    min_count, _ = context.constraint.letter_counts[letter]
                    if min_count > 1:
                        # 已知有重複：每個重複字母減少 1 次懲罰
                        duplicate_count = max(0, duplicate_count - 1)
            
            duplicate_penalty = duplicate_count * self.weights["duplicate_penalty"]
            score -= duplicate_penalty

        # Component 5: Trap Pattern Bonus (僅 Explorations + 陷阱情境啟用)
        if is_exploration and context.is_trap_situation:
            # 計算此單字在變動位置包含多少「需測試的字母」
            trap_coverage = 0
            for pos in context.trap_variable_positions:
                if word[pos] in context.trap_test_letters:
                    trap_coverage += 1
            
            # 獎勵：每覆蓋一個測試字母 +15 分
            # 例如：_IGHT 陷阱，FILMS 包含 4 個測試字母 → +60 分
            trap_bonus = trap_coverage * 20.0
            score += trap_bonus

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
