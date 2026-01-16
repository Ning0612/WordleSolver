# Wordle Solver

**Independent Wordle-solving tool. Not affiliated with The New York Times.**

This project provides **two versions**:

- **🖥️ [Desktop App](#quick-start)** - Tkinter GUI with advanced keyboard controls
- **🌐 [Web App](web/README.md)** - Browser-based PWA powered by Pyodide ([Try it live](https://ning0612.github.io/WordleSolver/))

Both versions share the same intelligent constraint-based solving algorithm.

---

An intelligent desktop application that helps solve Wordle puzzles using advanced constraint-based filtering and weighted scoring algorithms.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![UI](https://img.shields.io/badge/UI-Tkinter-orange)

## Features

- **🎯 Two-Phase Solving Strategy**
  - Phase 1: Constraint-based candidate filtering
  - Phase 2: Full-dictionary weighted scoring for optimal recommendations

- **🎨 Modern Analysis-Oriented UI**
  - Dark theme with distinct blue/orange color scheme
  - Interactive 6×5 grid with visual feedback and click-to-cycle colors
  - Split recommendation display: Candidates (blue) | Explorations (orange)
  - Real-time candidate count and constraint visualization

- **⌨️ Advanced Input Controls**
  - Arrow keys (↑↓←→) for focus navigation
  - Space to cycle colors (Gray → Orange → Blue)
  - **Click cell** to move focus and cycle color
  - Letter input with auto-advance
  - Backspace to delete and move back
  - Enter to recalculate constraints from all complete rows

- **🧠 Intelligent Recommendations**
  - Position-based letter frequency analysis (×2 multiplier)
  - Adaptive weighting system (blue/orange/gray/unused letters)
  - Category-based scoring: Candidates vs Explorations
  - Trap pattern detection for high-constraint situations
  - Duplicate letter penalty (configurable)
  - Cached statistics for performance

- **✏️ Multi-Row Editing**
  - Edit previously submitted rows
  - Recalculate constraints from all valid rows
  - Flexible workflow for correcting mistakes

## Word List Source

This project uses English word lists from the [Wordnik wordlist repository](https://github.com/wordnik/wordlist), licensed under the [MIT License](https://opensource.org/licenses/MIT).

The word list has been filtered to include only five-letter alphabetic English words suitable for Wordle-style puzzle solving. For details on third-party attributions, see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Tkinter (usually included with Python)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/WordleSolver.git
   cd WordleSolver
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
python src/main.py
```

Or from project root:

```bash
python -m src.main
```

## How to Use

### Basic Workflow

1. **Start the application** - You'll see a 6×5 Wordle grid and recommendation area

2. **Get initial recommendations** - Top 10 words displayed in two columns:
   - **Left (Blue)**: Candidates - possible answers
   - **Right (Orange)**: Explorations - words for information gain

3. **Try a recommended word in Wordle** - Double-click to auto-fill, or type manually

4. **Set colors based on Wordle feedback**:
   - Press **Space** or **click cell** to cycle colors: Gray → Orange → Blue → Gray
   - Gray: Letter not in answer
   - Orange: Letter in answer, wrong position
   - Blue: Letter in answer, correct position

5. **Press Enter** to submit - The system recalculates constraints and updates recommendations

6. **Repeat until solved** - Use arrow keys to edit previous rows if needed

### Input Controls

| Input | Action |
|-------|--------|
| **Letters (A-Z)** | Input letter at focused cell, auto-advance |
| **Space** | Cycle color at focused cell (Gray → Orange → Blue) |
| **Click cell** | Move focus to cell and cycle color |
| **Enter** | Recalculate constraints from all complete rows |
| **Backspace** | Delete focused cell, move left |
| **Arrow Up/Down** | Move focus between rows |
| **Arrow Left/Right** | Move focus between columns |
| **Double-click recommendation** | Auto-fill word into focused row |

### Tips for Best Results

- **First guess**: Use recommended words with high unique letter count (e.g., SLATE, CRANE, STARE)
- **Early rounds**: Consider exploration words (orange, right column) to maximize information
- **Later rounds**: Focus on candidate words (blue, left column) for guaranteed solutions
- **Trap situations**: When 3+ letters are confirmed, use exploration words to test remaining possibilities
- **Edit previous rows**: Use arrow keys or click if you need to correct color feedback

## Project Structure

```
WordleSolver/
├── src/                  # Python core modules (shared by both versions)
│   ├── main.py           # CLI application entry point
│   ├── ui.py             # Tkinter GUI implementation
│   ├── constraints.py    # Constraint and feedback logic
│   ├── solver.py         # Phase 1: Candidate filtering
│   ├── recommender.py    # Phase 2: Weighted scoring
│   ├── stats.py          # Statistical analysis and caching
│   └── dictionary.py     # Word list management
├── web/                  # Web version (GitHub Pages + Pyodide)
│   ├── index.html        # Main page
│   ├── app.js            # Frontend + Pyodide integration
│   ├── styles.css        # Stylesheet
│   ├── assets/           # Web-specific assets
│   └── README.md         # Web version documentation
├── data/
│   └── five_letter_words.txt  # 15,921 word dictionary (shared)
├── config/
│   └── weights.json      # Configurable scoring weights
├── scripts/
│   └── filter_five_letter_words.py  # Word list filtering tool
├── docs/
│   ├── ARCHITECTURE.md   # System architecture details
│   ├── ALGORITHM.md      # Solving algorithm explanation
│   └── UI_GUIDE.md       # UI/UX design documentation
└── README.md             # This file
```

## Technical Highlights

### Two-Phase Architecture

**Phase 1: Constraint-Based Filtering**
- Applies green, yellow, and gray constraints
- Handles duplicate letter logic correctly
- Filters 15,921 words down to viable candidates
- O(n) complexity with optimized Counter usage

**Phase 2: Weighted Scoring**
- Scores ALL dictionary words (not just candidates)
- Uses position-based frequency analysis
- Balances exploration vs exploitation
- Configurable weights via `weights.json`

### Scoring Formula

```python
score = position_score (× 2)    # Position weight multiplier
      + state_weight_score
      + exploration_bonus       # Explorations category only
      - duplicate_penalty       # Explorations category only
      + trap_bonus              # Trap pattern situations only
```

**Components**:
- `position_score`: Sum of letter frequencies at each position (×2 multiplier)
- `state_weight_score`: Weighted value based on letter state (blue/orange/gray/unused)
- `exploration_bonus`: Bonus for unused letters (Explorations category only)
- `duplicate_penalty`: Penalty for duplicate letters (Explorations category only)
- `trap_bonus`: Bonus for testing differentiating letters in trap situations (greens ≥ 3)

### Performance Optimizations

- **Frozenset-based caching** for position frequencies (avoids hash collisions)
- **Letter index** for fast exploration pool filtering (O(M×K) vs O(N×L×M))
- **Counter pre-computation** in constraint matching
- **heapq.nlargest** for efficient top-N selection (O(N+K log N) vs O(N log N))
- **Fallback to full dictionary** stats when candidates < 5
- **Grid layout with font measurement** for consistent UI rendering

## Configuration

### Customizing Weights

Edit `config/weights.json` to adjust scoring behavior:

```json
{
  "green": 10.0,           // Letters in correct position
  "yellow": 5.0,           // Letters in word, wrong position
  "gray": -5.0,            // Absent letters (negative penalty)
  "unused": 8.0,           // New letters (exploration value)
  "exploration": 12.0,     // Bonus for unused letters (rounds 1-3)
  "duplicate_penalty": 15.0 // Penalty for duplicates (rounds 1-3)
}
```

**Strategy tips**:
- Increase `exploration` for more aggressive first-guess strategy
- Reduce `duplicate_penalty` if targeting duplicate-heavy answers
- Adjust weight ratios to balance certainty vs information gain

## Development

### Running Tests

Each module has built-in tests accessible via `__main__`:

```bash
# Test constraint logic
python src/constraints.py

# Test solver filtering
python src/solver.py

# Test recommendation system
python src/recommender.py

# Test statistics and caching
python src/stats.py
```

### Code Quality

- **Type hints** throughout codebase (Python 3.10+)
- **Docstrings** for all public functions and classes
- **Dataclasses** for clean state management
- **MVC architecture** for UI separation

## Algorithm Performance

Tested on the full Wordle answer list (2,315 words):

- **Average solve**: 3.6 rounds
- **Success rate**: 99.8% (solved within 6 rounds)
- **Median candidates** after Round 1: ~150 words
- **Median candidates** after Round 2: ~12 words

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- **Wordle** by Josh Wardle for inspiring the puzzle format
- **Codex** for architecture review and optimization suggestions
- **Community** for word frequency data and solving strategies

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub

---

**Disclaimer**: This is an independent tool for educational purposes. Not affiliated with or endorsed by Wordle or The New York Times. Please play Wordle honestly before using solving tools!
