# System Architecture

## Overview

Wordle Solver is built with a clean **MVC (Model-View-Controller)** architecture, separating business logic from UI presentation. The system implements a **two-phase solving strategy** optimized for both accuracy and user experience.

```
┌─────────────────────────────────────────────────────────────┐
│                         UI Layer                            │
│  (ui.py - Tkinter GUI, Event Handling, Visual Updates)     │
└──────────────────┬──────────────────────────────────────────┘
                   │
          ┌────────▼─────────┐
          │   Controller     │
          │  (Event Loops)   │
          └────────┬─────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
┌───▼────────────┐      ┌────────▼─────────┐
│  Phase 1:      │      │  Phase 2:        │
│  Filtering     │      │  Scoring         │
│ (solver.py)    │      │ (recommender.py) │
└───┬────────────┘      └────────┬─────────┘
    │                            │
    │        ┌───────────────────┤
    │        │                   │
┌───▼────────▼───┐      ┌───────▼──────┐
│  Constraints   │      │   Statistics │
│ (constraints.py│      │   (stats.py) │
└────────────────┘      └──────────────┘
         │
         │
    ┌────▼────────┐
    │ Dictionary  │
    │(dictionary.py)
    └─────────────┘
```

## Architecture Layers

### 1. Data Layer

#### **dictionary.py** - Word List Management
```python
def get_word_list(filepath: str = "data/five_letter_words.txt") -> List[str]
```

**Responsibilities**:
- Load and validate 15,921 five-letter words
- Normalize to lowercase
- Filter non-ASCII and invalid entries
- Provide clean word list to upper layers

**Design Decisions**:
- Single source of truth for word list
- Lazy loading (loads on first import)
- Immutable after loading (prevents corruption)

---

#### **constraints.py** - Constraint and Feedback Logic

**Core Classes**:

```python
@dataclass
class Constraint:
    greens: Dict[int, str]                              # Position → letter (exact matches)
    yellows: Dict[str, Set[int]]                        # Letter → excluded positions
    letter_counts: Dict[str, Tuple[int, Optional[int]]] # Letter → (min, max)

    @property
    def grays(self) -> Set[str]:
        """Derived property: letters with max_count == 0"""
        return {letter for letter, (_, max_c) in self.letter_counts.items()
                if max_c == 0}
```

**Note**: `grays` is now a **derived property** computed from `letter_counts`, not a stored attribute. This avoids inconsistency between `grays` and `letter_counts`.

**Key Methods**:
- `merge(other: Constraint) -> Constraint`: Combine constraints from multiple rounds
- `get_definitely_absent() -> Set[str]`: Extract letters with `max_count == 0`

```python
@dataclass
class FeedbackRound:
    guess: str
    feedback: List[FeedbackColor]  # 5-element list of colors

    def to_constraint(self) -> Constraint:
        """Convert feedback to constraint representation"""
```

**Design Pattern**: **Builder Pattern**
- `FeedbackRound` represents raw Wordle feedback
- `to_constraint()` builds structured constraint
- `merge()` allows incremental constraint accumulation

**Duplicate Letter Handling**:
```python
# Example: Guess "SPEED", Answer "EMBER"
# Feedback: S=gray, P=gray, E=yellow (pos 2), E=gray (pos 3), D=gray
# Constraint: letter_counts['e'] = (1, 1)  # Exactly 1 E
```

Logic:
1. Count greens and yellows for each letter
2. If ANY instance is gray → set max_count
3. Result: `(min_count, max_count)` range

---

### 2. Business Logic Layer

#### **solver.py** - Phase 1: Candidate Filtering

```python
def filter_candidates(words: List[str], constraint: Constraint) -> List[str]
```

**Algorithm**:
```python
def _matches_constraint(word: str, constraint: Constraint) -> bool:
    # Rule 1: Check green positions (exact matches)
    for pos, letter in constraint.greens.items():
        if word[pos] != letter:
            return False

    # Precompute letter counts (Codex optimization)
    word_counts = Counter(word)

    # Rule 2: Check yellows (must exist, not at excluded positions)
    for letter, excluded_positions in constraint.yellows.items():
        if word_counts[letter] == 0:
            return False
        for pos in excluded_positions:
            if word[pos] == letter:
                return False

    # Rule 3: Check letter count constraints
    for letter, (min_count, max_count) in constraint.letter_counts.items():
        actual_count = word_counts[letter]
        if actual_count < min_count:
            return False
        if max_count is not None and actual_count > max_count:
            return False

    return True
```

**Complexity**: O(n × k) where n = dictionary size, k = word length (5)

**Performance Optimization**:
- Use `Counter()` once per word (avoid repeated `word.count()`)
- Early exit on first constraint violation
- Typical reduction: 15,921 → ~150 candidates after Round 1

---

#### **recommender.py** - Phase 2: Weighted Scoring

**Core Algorithm**:

```python
def recommend(
    candidates: List[str],
    constraint: Constraint,
    round_number: int,
    top_n: int = 5  # default changed from 10 to 5
) -> Dict[str, List[Tuple[str, float]]]  # Returns split categories
```

**Return Structure (v2)**:
```python
{
    "candidates": [(word, score), ...],     # Phase 1 candidates (blue in UI)
    "explorations": [(word, score), ...]    # Non-candidates (orange in UI)
}
```

**New Components**:

1. **ScoringContext Dataclass** - Encapsulates all scoring context:
   ```python
   @dataclass
   class ScoringContext:
       position_freqs: Dict[int, Dict[str, float]]
       round_number: int
       constraint: Constraint
       green_letters: Set[str]      # Precomputed
       yellow_letters: Set[str]     # Precomputed
       gray_letters: Set[str]       # Precomputed
       known_letters: Set[str]      # Precomputed
       # Trap Pattern Detection
       is_trap_situation: bool
       trap_variable_positions: Set[int]
       trap_test_letters: Set[str]
   ```

2. **Letter Index Optimization**:
   ```python
   def _build_letter_index(self) -> Dict[str, Set[str]]:
       """Map letter → set of words containing it"""
       # Enables O(M × K) filtering instead of O(N × L × M)
   ```

**Multi-Stage Scoring**:

1. **Build Exploration Pool** (optimized):
   ```python
   # OLD: O(N × L × M) - iterate all words, check each letter
   # NEW: O(M × K) - use letter index for fast exclusion
   excluded = set()
   for letter in definitely_absent:
       excluded.update(self._letter_index[letter])
   exploration_pool = [w for w in dictionary if w not in excluded]
   ```

2. **Compute Position Frequencies**:
   ```python
   position_freqs = stats.get_position_frequencies(candidates)
   ```
   - Uses Phase 1 candidates for frequency analysis
   - Adaptive: switches to full dictionary if candidates < 5 (lowered from 10)

3. **Detect Trap Patterns**:
   ```python
   if len(constraint.greens) >= 3:
       # Identify variable positions and test letters
       # Enable trap bonus for exploration words
   ```

4. **Score Each Word** (category-based):
   ```python
   def _score_word(word, context, is_exploration):
       score = position_score × 2.0     # POSITION_WEIGHT_MULTIPLIER
             + state_weight_score
       if is_exploration:
           score += exploration_bonus   # Explorations only
           score -= duplicate_penalty   # Explorations only
           if context.is_trap_situation:
               score += trap_bonus      # Trap pattern handling
       return score
   ```

5. **Select Top N** (optimized):
   ```python
   # Use heapq.nlargest instead of full sort
   # O(N + K log N) vs O(N log N)
   top_candidates = heapq.nlargest(top_n, scored_candidates, key=...)
   ```

**Scoring Components**:

| Component | Formula | Purpose |
|-----------|---------|---------|
| **Position Score** | `Σ freq[pos][letter] × 2.0` | Favor common letters (× 2 multiplier) |
| **State Weight** | `Σ weight[letter_state]` | Prioritize green > yellow > unused > gray |
| **Exploration Bonus** | `unused_count × 12.0` | Encourage new letters (Explorations only) |
| **Duplicate Penalty** | `dup_count × 15.0` | Discourage repeats (Explorations only) |
| **Trap Bonus** | `coverage × 20.0` | Handle trap patterns (Explorations + greens≥3) |

**Adaptive Behavior (v2 - Category-Based)**:
- **Candidates**: Pure exploitation (position + state weights only)
- **Explorations**: Pure exploration (full bonus/penalty logic)

**Design Pattern**: **Strategy Pattern**
- Category-based scoring strategies (not round-based)
- Configurable weights via `config/weights.json`
- Easy to add new scoring components

---

#### **stats.py** - Statistical Analysis and Caching

```python
class LetterStats:
    def __init__(self, full_dictionary: List[str]):
        self.full_dictionary = full_dictionary
        self._cache: Dict[FrozenSet[str], Dict[int, Dict[str, float]]] = {}
        self._full_dict_stats = self._compute_position_frequencies(full_dictionary)
```

**Caching Strategy**:

```python
def get_position_frequencies(
    candidates: List[str],
    min_candidates_threshold: int = 5  # Optimization 3: lowered from 10
) -> Dict[int, Dict[str, float]]:

    # Fallback to full dictionary if too few candidates
    if len(candidates) < min_candidates_threshold:
        return self._full_dict_stats

    # Use frozenset as cache key (Codex fix: avoids hash collisions)
    cache_key = frozenset(candidates)

    if cache_key in self._cache:
        return self._cache[cache_key]

    frequencies = self._compute_position_frequencies(candidates)
    self._cache[cache_key] = frequencies
    return frequencies
```

**Why Frozenset Instead of Hash?**
- Hash collisions possible (different lists → same hash)
- Frozenset guarantees unique key per candidate set
- Small memory overhead, large correctness benefit

**Position Frequency Structure**:
```python
{
    0: {'s': 0.15, 'c': 0.12, 'a': 0.10, ...},  # Position 0 frequencies
    1: {'a': 0.14, 'o': 0.11, 'r': 0.09, ...},  # Position 1 frequencies
    ...
    4: {'e': 0.18, 'y': 0.11, 's': 0.09, ...}   # Position 4 frequencies
}
```

---

### 3. UI Layer

#### **ui.py** - Tkinter GUI Implementation

**MVC Components**:

```python
@dataclass
class AppState:  # MODEL
    history_grid_letters: List[List[str]]        # 6×5 grid of letters
    history_grid_colors: List[List[FeedbackColor]]  # 6×5 grid of colors
    focused_row: int                             # Current focus (0-5)
    focused_col: int                             # Current focus (0-4)
    candidates: List[str]                        # Phase 1 results
    current_constraint: Constraint               # Merged constraints
    round_number: int                            # Current round (1-6)

class WordleSolverApp:  # VIEW + CONTROLLER
    def __init__(self, master: tk.Tk):
        self.state = AppState()  # Model
        self._create_widgets()   # View
        self._bind_events()      # Controller
```

**Event-Driven Architecture**:

```python
# Keyboard Event Routing
def _on_key_press(self, event):
    key = event.keysym

    if key.isalpha():
        self._input_letter(key.upper())  # Letter input
    elif key == "space":
        self._cycle_current_color()      # Color toggle
    elif key == "Return":
        self._submit_round()             # Submit & recalculate
    elif key == "BackSpace":
        self._delete_letter()            # Delete & move back
    elif key in ("Up", "Down", "Left", "Right"):
        self._move_focus(key)            # Arrow navigation
```

**UI Update Flow**:

```
User Action
    │
    ├─→ Update State (AppState)
    │
    ├─→ Update UI (Labels, Colors, Focus)
    │
    └─→ Trigger Recalculation (Phase 1 + Phase 2)
            │
            └─→ Update Recommendations Display
```

**Grid as Single Source of Truth**:
```python
# OLD (v1): Dual state (current_guess + history)
# PROBLEM: Sync issues between input row and history

# NEW (v2): Unified grid state
history_grid_letters[row][col]  # All rows editable
history_grid_colors[row][col]   # All rows have colors
```

Benefits:
- No sync issues
- Easy multi-row editing
- Simpler state management

---

## Design Patterns

### 1. **Two-Phase Architecture** (Pipeline Pattern)

```
Input (Feedback) → Phase 1 (Filter) → Phase 2 (Score) → Output (Top 10)
```

**Separation of Concerns**:
- Phase 1: Correctness (eliminate impossible words)
- Phase 2: Optimization (rank possible words)

**Benefits**:
- Independent testing
- Easy to tune (adjust weights without touching filter logic)
- Clear performance bottlenecks

---

### 2. **Builder Pattern** (Constraints)

```python
constraint1 = round1.to_constraint()  # Build from feedback
constraint2 = round2.to_constraint()
merged = constraint1.merge(constraint2)  # Incremental build
```

**Benefits**:
- Immutable constraint objects
- Composable via `merge()`
- Clear separation: feedback → constraint → filter

---

### 3. **Strategy Pattern** (Scoring)

```python
# Early rounds: Exploration strategy
if round_number <= 3:
    score += exploration_bonus
    score -= duplicate_penalty

# Late rounds: Exploitation strategy (position score only)
```

**Benefits**:
- Adaptive behavior
- Easy to add new strategies
- Configurable via `config/weights.json`

---

### 4. **Cache-Aside Pattern** (Statistics)

```python
def get_position_frequencies(candidates):
    cache_key = frozenset(candidates)
    if cache_key in self._cache:
        return self._cache[cache_key]  # Cache hit

    result = self._compute_position_frequencies(candidates)
    self._cache[cache_key] = result  # Cache write
    return result
```

**Benefits**:
- Lazy computation
- Automatic cache management
- Fallback to full dictionary stats

---

## Data Flow

### Complete Round Flow

```
1. User inputs "CRANE" with colors [Blue, Orange, Orange, gray, gray]
   │
   ├─→ Create FeedbackRound("crane", [GREEN, YELLOW, YELLOW, GRAY, GRAY])
   │
   ├─→ Convert to Constraint:
   │     greens: {0: 'c'}
   │     yellows: {'r': {1}, 'a': {2}}
   │     letter_counts: {'c': (1, None), 'r': (1, None), 'a': (1, None), 'n': (0, 0), 'e': (0, 0)}
   │     grays: (derived) {'n', 'e'}
   │
   ├─→ Merge with previous constraints (if any)
   │
   ├─→ PHASE 1: filter_candidates(words, constraint)
   │     15,921 words → ~150 candidates
   │
   ├─→ PHASE 2: recommender.recommend(candidates, constraint, round=2)
   │     │
   │     ├─→ Build exploration pool via letter index (exclude 'n', 'e')
   │     │
   │     ├─→ Get position frequencies from candidates
   │     │
   │     ├─→ Detect trap patterns (if greens >= 3)
   │     │
   │     ├─→ Score candidates (no exploration bonus)
   │     │
   │     ├─→ Score explorations (with exploration bonus)
   │     │
   │     └─→ Return split results:
   │           {"candidates": [("cargo", 40.0), ...],
   │            "explorations": [("stork", 78.4), ...]}
   │
   └─→ Update UI:
       - Display 5 Candidates (blue, left column)
       - Display 5 Explorations (orange, right column)
       - Move focus to next row
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Typical Time |
|-----------|------------|--------------|
| Load dictionary | O(n) | ~50ms (15,921 words) |
| Create constraint | O(k) | <1ms (k=5 letters) |
| Filter candidates | O(n × k) | ~10ms (n=15,921) |
| Compute position freq | O(n × k) | ~5ms |
| Score single word | O(k) | <0.01ms |
| Score all words | O(m × k) | ~20ms (m≈10,000) |
| **Total per round** | **O(n × k)** | **~35ms** |

### Space Complexity

| Component | Space | Notes |
|-----------|-------|-------|
| Dictionary | O(n) | 15,921 words × ~5 bytes ≈ 80KB |
| Constraint | O(k²) | Small (5×5 positions) |
| Candidates | O(n) | Worst case: full dictionary |
| Position freq cache | O(c × k × 26) | c = unique candidate sets |
| UI state | O(36) | 6×5 grid + metadata |
| **Total** | **O(n)** | **~2MB** |

### Caching Performance

**Cache Hit Rate**: ~40% in typical game
- Round 1: No cache (compute)
- Round 2-6: Often reuse similar candidate sets

**Cache Memory**: ~1MB for 100 cached sets
- Acceptable for desktop application
- Can be cleared anytime via `stats.clear_cache()`

---

## Scalability Considerations

### Current Limits

- **Dictionary size**: 15,921 words (Wordle standard)
- **Grid size**: 6 rounds × 5 letters (Wordle rules)
- **Recommendation count**: 10 words (UI constraint)

### Potential Extensions

1. **Larger Dictionaries**
   - Current: O(n) filter works up to ~100K words
   - Optimization: Index by first letter (26× speedup)

2. **Different Word Lengths**
   - Generalize `k=5` to variable length
   - Update UI grid dynamically

3. **Hard Mode Support**
   - Add constraint: must use all known letters
   - Filter Phase 2 to only include greens/yellows

4. **Multi-Language**
   - Language-specific dictionaries
   - Unicode support (currently ASCII only)

---

## Testing Strategy

Each module includes `if __name__ == "__main__"` tests:

```bash
python src/constraints.py  # Test constraint logic
python src/solver.py       # Test filtering
python src/recommender.py  # Test scoring
python src/stats.py        # Test caching
```

**Test Coverage**:
- ✅ Duplicate letter handling
- ✅ Constraint merging
- ✅ Cache correctness (frozenset)
- ✅ Position frequency calculations
- ✅ Scoring components

**Integration Test**: Run full game simulation via UI

---

## Future Improvements

### Architecture

1. **Dependency Injection** for `WordRecommender`
   - Easier testing with mock `LetterStats`
   - Plug different scoring strategies

2. **Observer Pattern** for UI updates
   - Decouple state changes from UI updates
   - Enable undo/redo functionality

3. **Command Pattern** for user actions
   - Record action history
   - Implement replay/analysis mode

### Algorithms

1. **Information Theory Scoring**
   - Expected information gain per guess
   - Optimal worst-case guarantees

2. **Machine Learning Weights**
   - Train on actual Wordle answer distribution
   - Adaptive weights based on user performance

3. **Monte Carlo Tree Search**
   - Explore full game tree
   - Find provably optimal guesses

---

## Conclusion

The architecture balances:
- **Simplicity**: Clear separation of concerns
- **Performance**: Sub-50ms per round on consumer hardware
- **Maintainability**: Well-documented, testable components
- **Extensibility**: Easy to add features (new scoring, different rules)

The two-phase design is the key insight:
- Phase 1 ensures correctness (no false negatives)
- Phase 2 optimizes user experience (best guesses first)

This separation allows independent tuning and testing of each component.
