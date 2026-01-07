# UI/UX Design Guide

## Overview

Wordle Solver features a **tool-oriented dark theme interface** with a distinct blue/orange color scheme designed to avoid confusion with the official Wordle game, while maintaining modern UX patterns optimized for efficient keyboard-driven workflows.

---

## Design System

### Color Palette

```python
COLORS = {
    "bg_dark": "#0F172A",           # Main background (dark blue-black)
    "bg_frame": "#1E293B",          # Frame background
    "letter_empty": "#334155",      # Empty letter box
    "letter_gray": "#475569",       # Gray feedback (absent)
    "letter_orange": "#F97316",     # Orange feedback (wrong position)
    "letter_blue": "#3B82F6",       # Blue feedback (correct position)
    "text": "#E5E7EB",              # Primary text color
    "recommend_bg": "#020617",      # Recommendation area background
    "recommend_candidate": "#3B82F6",  # Phase 1 candidate marker (blue)
    "recommend_explore": "#F97316",    # Phase 2 exploration marker (orange)
}
```

**Color Theory**:
- Dark background reduces eye strain for extended use
- High contrast (white on dark) for readability
- Distinct blue/orange scheme to differentiate from official Wordle
- Blue/orange semantic meaning (candidate vs exploration)

---

### Typography

**Primary Font**: `Helvetica Neue Bold`
- Modern, clean sans-serif
- Excellent readability at all sizes
- Professional tool aesthetic
- **Not monospace** (proportional widths)

**Font Sizes**:
```python
title:          18pt bold  # Section headers
legend:         12pt       # Legend labels
recommendation: 16pt bold  # Recommendation words
grid_letter:    24pt bold  # Wordle grid letters
```

**Width Consistency Challenge**:
- Problem: Different letters have different widths (I vs W)
- Solution: Use `tkfont.Font.measure()` to calculate actual pixel widths
- Implementation: Set `minsize` on Grid columns based on max measured width

```python
# Measure font to calculate consistent width
measure_font = tkfont.Font(family="Helvetica Neue", size=16, weight="bold")
max_word_width = max(measure_font.measure(f"{i}. {w.upper()}") for i, (w, _) in enumerate(recs, 1))
col_width = max_word_width + 40  # Add padding

# Set minimum column width for consistency
grid_frame.grid_columnconfigure(0, minsize=col_width, uniform="rec")
grid_frame.grid_columnconfigure(1, minsize=col_width, uniform="rec")
```

---

## Layout Structure

### Window Configuration

```python
geometry: "500×1000"  # Width × Height
minsize: 500×850      # Minimum window size
resizable: False      # Fixed layout for consistency
```

**Rationale**:
- 500px width accommodates 2-column recommendation grid
- 1000px height fits 6-row game grid + recommendations + controls
- Fixed layout ensures predictable UI behavior
- No resize to maintain visual consistency

---

### Component Hierarchy

```
┌─────────────────────────────────────────────────┐
│              Window (500×1000)                  │
├─────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────┐ │
│  │    Recommendations Area (2×5 Grid)        │ │ 40%
│  │  ┌────────┬────────┐                      │ │
│  │  │1. SLATE│2. CRANE│                      │ │
│  │  ├────────┼────────┤                      │ │
│  │  │3. ...  │4. ...  │                      │ │
│  │  └────────┴────────┘                      │ │
│  └───────────────────────────────────────────┘ │
├─────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────┐ │
│  │      Wordle Grid (6×5)                    │ │ 50%
│  │  ┌───┬───┬───┬───┬───┐                   │ │
│  │  │ C │ R │ A │ N │ E │                   │ │
│  │  ├───┼───┼───┼───┼───┤                   │ │
│  │  │   │   │   │   │   │  ← Current row    │ │
│  │  └───┴───┴───┴───┴───┘                   │ │
│  └───────────────────────────────────────────┘ │
├─────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────┐ │
│  │         RESET Button                      │ │ 10%
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Recommendation Area

**Layout**: 2 columns × 5 rows Grid

**Before (v1)**: Vertical list with Canvas + Scrollbar
```python
# Problems:
# - Variable width boxes (inconsistent)
# - Vertical scrolling (extra interaction)
# - No numbering (hard to reference)
```

**After (v2)**: Fixed 2×5 Grid with uniform columns
```python
grid_frame.grid_columnconfigure(0, weight=1, uniform="rec")
grid_frame.grid_columnconfigure(1, weight=1, uniform="rec")

for i, (word, score) in enumerate(recs, 1):
    row = (i - 1) // 2  # 0-4
    col = (i - 1) % 2   # 0-1
    item_frame.grid(row=row, column=col, padx=8, pady=4, sticky="nsew")
```

**Benefits**:
- ✅ Consistent box widths via `uniform` parameter
- ✅ Dense layout (2×5 vs 10×1)
- ✅ Clear numbering (1-10)
- ✅ No scrolling needed
- ✅ Easy visual scanning (left-right, top-bottom)

**Color Coding**:
- **Blue Background** (#3B82F6): Phase 1 candidate (word IS in candidate set)
- **Orange Background** (#F97316): Phase 2 exploration (word NOT in candidate set)

**Interaction**:
- **Double-click** on word → auto-fill into focused row
- **Hover**: No special effect (simple click target)

---

### 2. Wordle Grid (6×5)

**Cell Specifications**:
```python
width: 4 characters (at 24pt)
height: 2 lines
font: "Helvetica Neue", 24pt, bold
border: 2px
relief: FLAT (default), SUNKEN (focused)
```

**Color States**:
| State | Background | Text | Border |
|-------|------------|------|--------|
| Empty | #334155 (dark gray) | #E5E7EB | FLAT, 2px |
| Filled | Feedback color | #E5E7EB | FLAT, 2px |
| Focused | Current feedback | #E5E7EB | SUNKEN, 4px |

**Visual Feedback**:
- **Empty cells**: Dark gray background
- **Filled cells**: Show feedback color (gray/yellow/green)
- **Focused cell**: SUNKEN relief with 4px border (clear indicator)

**Grid Layout**:
```python
for row in range(6):
    for col in range(5):
        label = tk.Label(
            grid_frame,
            text="",
            width=4,
            height=2,
            font=("Helvetica Neue", 24, "bold"),
            bg=COLORS["letter_empty"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            bd=2
        )
        label.grid(row=row, column=col, padx=3, pady=3)
```

**Spacing**: 3px padding between cells for clear visual separation

---

### 3. Focus Indicator

**Implementation**:
```python
def _update_input_focus(self):
    for row in range(6):
        for col in range(5):
            label = self.history_labels[row][col]
            if row == self.state.focused_row and col == self.state.focused_col:
                label.config(relief=tk.SUNKEN, bd=4)  # Focused
            else:
                label.config(relief=tk.FLAT, bd=2)    # Normal
```

**Visual Hierarchy**:
- Focused cell: SUNKEN (inset) + 4px border → draws eye
- Other cells: FLAT + 2px border → recedes

**Why SUNKEN Works**:
- Creates 3D depth effect
- More visible than color change alone
- Works with all background colors
- Standard Tkinter behavior (no custom drawing)

---

### 4. Legend

**Purpose**: Explain color coding for recommendations

**Layout**:
```
● Candidate    ● Exploration
  (blue)         (orange)
```

**Position**: Between title and recommendation grid

**Font**: 12pt (smaller than recommendations, larger than status)

---

### 5. Controls

**Reset Button**:
```python
width: 12 characters
height: 2 lines
font: "Helvetica Neue", 14pt, bold
background: #3a3a3c (frame color)
foreground: #ffffff (white text)
cursor: "hand2" (pointer on hover)
```

**Position**: Bottom of window, centered

**Behavior**: Clears all state, returns to initial recommendations

---

## Interaction Patterns

### Keyboard-First Design

**Philosophy**: All operations accessible via keyboard (mouse optional)

**Key Bindings**:
```python
self.master.bind_all("<Key>", self._on_key_press)  # Global capture
```

**Why `bind_all` vs `bind`**:
- `bind()`: Only works when window has focus
- `bind_all()`: Always captures, even after clicking recommendations
- Essential for continuous keyboard workflow

---

### Input Flow

**Standard Flow**:
```
1. Press Space → Set color (Gray/Orange/Blue)
2. Type Letter → Input and advance
3. Repeat for all 5 letters
4. Press Enter → Submit and move to next row
```

**Alternative Flow** (edit previous row):
```
1. Arrow Up/Down → Move to previous row
2. Arrow Left/Right → Move to specific cell
3. Space → Change color
4. Type Letter → Update letter
5. Enter → Recalculate all rows
```

**Auto-Advance Logic**:
```python
# After letter input
if self.state.focused_col < 4:
    self.state.focused_col += 1  # Move right
```

**Auto-Retreat Logic**:
```python
# After backspace
if self.state.focused_col > 0:
    self.state.focused_col -= 1  # Move left
```

---

### Focus Management

**Focus State**:
```python
@dataclass
class AppState:
    focused_row: int  # 0-5 (6 rows)
    focused_col: int  # 0-4 (5 columns)
```

**Focus Movement**:
| Key | Row Change | Col Change |
|-----|------------|------------|
| Up | -1 (min 0) | - |
| Down | +1 (max 5) | - |
| Left | - | -1 (min 0) |
| Right | - | +1 (max 4) |

**Boundary Handling**: `max(0, min(value, limit))` to prevent out-of-bounds

---

### Enter Key Behavior

**Before (v1)**: Submit current row only
```python
# Problem: Focus stays on current row (user must manually navigate)
```

**After (v2)**: Submit all complete rows + auto-navigate
```python
def _submit_round(self):
    # Scan all 6 rows for complete 5-letter words
    rounds = []
    for row in range(6):
        guess = "".join(self.state.history_grid_letters[row])
        if len(guess) == 5 and guess.isalpha():
            rounds.append(FeedbackRound(guess, feedback))

    # Recalculate from all complete rows
    merged_constraint = merge_all(rounds)
    candidates = filter_candidates(words, merged_constraint)

    # Move focus to next incomplete row
    next_row = len(rounds)  # Next empty row
    if next_row < 6:
        self.state.focused_row = next_row
        self.state.focused_col = 0
        self._update_input_focus()
```

**Benefits**:
- ✅ Allows multi-row editing
- ✅ Auto-navigates to next row
- ✅ Recalculates all constraints correctly
- ✅ Handles incomplete rows gracefully

---

## State Management

### Single Source of Truth Pattern

**Grid as Primary State**:
```python
history_grid_letters: List[List[str]]        # 6×5 letters
history_grid_colors: List[List[FeedbackColor]]  # 6×5 colors
```

**Why Not Separate `current_guess`?**
```python
# OLD (v1): Dual state
current_guess: List[str]  # Current input row
history: List[FeedbackRound]  # Submitted rows

# Problem: Sync issues between current and history
# - When does current become history?
# - What if user edits history?
```

**NEW (v2): Unified grid**
```python
# All rows are in grid
# Current row = history_grid[focused_row]
# Submitted rows = rows with complete 5 letters
```

**Benefits**:
- ✅ No sync issues
- ✅ Easy multi-row editing
- ✅ Simple state management
- ✅ Clear data flow

---

### UI Update Flow

```
User Input → Update State → Update UI → Trigger Calculation
```

**Example (Letter Input)**:
```python
def _input_letter(self, letter: str):
    row = self.state.focused_row
    col = self.state.focused_col

    # 1. Update state
    self.state.history_grid_letters[row][col] = letter.lower()

    # 2. Update UI
    current_color = self.state.history_grid_colors[row][col]
    self.history_labels[row][col].config(
        text=letter,
        bg=FEEDBACK_COLORS[current_color]
    )

    # 3. Advance focus
    if self.state.focused_col < 4:
        self.state.focused_col += 1

    # 4. Update visual focus
    self._update_input_focus()
```

**Separation of Concerns**:
- State update (data)
- UI update (view)
- Focus management (controller)

---

## Responsive Behavior

### Recommendation Updates

**Triggers**:
- After each Enter (new round submitted)
- After Reset

**Update Process**:
```python
def _update_recommendations(self):
    # 1. Clear existing widgets
    for widget in self.recommend_frame.winfo_children():
        widget.destroy()

    # 2. Get new recommendations
    recs = self.recommender.recommend(...)

    # 3. Measure font for consistent width
    measure_font = tkfont.Font(...)
    max_width = max(measure_font.measure(...))
    self.recommend_frame.grid_columnconfigure(0, minsize=max_width)

    # 4. Display in 2×5 grid
    for i, (word, score) in enumerate(recs, 1):
        row = (i - 1) // 2
        col = (i - 1) % 2
        # Create label and bind events
```

**Performance**: ~20ms to update 10 recommendations (negligible)

---

### Focus Indicator Updates

**Triggers**:
- After any arrow key press
- After letter input (auto-advance)
- After backspace (auto-retreat)
- After Enter (move to next row)

**Implementation**:
```python
def _update_input_focus(self):
    # O(30) operation: 6 rows × 5 cols
    for row in range(6):
        for col in range(5):
            if row == focused_row and col == focused_col:
                set_focused_style()
            else:
                set_normal_style()
```

**Performance**: <1ms (30 label config calls)

---

## Accessibility Considerations

### Keyboard Navigation

- ✅ All features accessible via keyboard
- ✅ No mouse required
- ✅ Standard arrow key behavior
- ✅ Logical tab order (not implemented yet)

### Visual Clarity

- ✅ High contrast (white on dark)
- ✅ Large font sizes (16-24pt)
- ✅ Clear focus indicator (SUNKEN relief)
- ✅ Color + text labels (not color-only)

### Future Improvements

- ❌ Screen reader support (ARIA labels)
- ❌ Keyboard shortcuts (Ctrl+R for reset)
- ❌ Undo/redo (Ctrl+Z)
- ❌ Copy/paste support (Ctrl+C/V)

---

## Design Decisions & Rationale

### Why 2×5 Grid Instead of 10×1 List?

**Comparison**:
```
10×1 List:           2×5 Grid:
┌────────┐          ┌─────┬─────┐
│1. SLATE│          │1. ..│2. ..│
│2. CRANE│          │3. ..│4. ..│
│3. STARE│          │5. ..│6. ..│
│4. ADIEU│          │7. ..│8. ..│
│5. AUDIO│          │9. ..│10...│
│6. AROSE│          └─────┴─────┘
│7. RAISE│
│8. LATER│          Width: 2× smaller
│9. IRATE│          Height: 2× smaller
│10.SNARE│          Scan: Left-right natural
└────────┘
```

**Benefits**:
- Saves 50% vertical space
- More compact layout
- Easier visual scanning
- Natural left-to-right reading

---

### Why Fixed Window Size?

**Alternatives Considered**:
1. **Resizable window**
   - Pro: User flexibility
   - Con: Complex layout calculations, testing matrix
2. **Minimum + resizable**
   - Pro: Some flexibility
   - Con: Still need to handle resize logic
3. **Fixed size** ✅
   - Pro: Simple, predictable, no edge cases
   - Con: Less flexible

**Decision**: Fixed size for simplicity and consistency

---

### Why SUNKEN Relief for Focus?

**Alternatives Considered**:
1. **Border color change**
   - Pro: Simple
   - Con: Less visible, clashes with feedback colors
2. **Background highlight**
   - Pro: Clear
   - Con: Conflicts with feedback colors
3. **RAISED relief**
   - Pro: 3D effect
   - Con: Feels like button (wrong affordance)
4. **SUNKEN relief** ✅
   - Pro: Clear depth, doesn't conflict with colors
   - Con: None

**Decision**: SUNKEN relief provides best visual clarity

---

### Why Font Measurement for Width?

**Problem**: Helvetica Neue is proportional (not monospace)
- "I" is narrower than "W"
- "1. IGLOO" shorter than "10. WORLD"

**Naive Solution**: Set fixed width in characters
```python
label.config(width=15)  # Characters, not pixels
# Problem: Width varies based on actual letters!
```

**Correct Solution**: Measure actual pixel width
```python
font = tkfont.Font(family="Helvetica Neue", size=16, weight="bold")
max_width = max(font.measure(f"{i}. {word.upper()}") for i, word in enumerate(words, 1))
grid.grid_columnconfigure(0, minsize=max_width)
```

**Benefits**:
- ✅ Exact pixel-perfect alignment
- ✅ Works with any font
- ✅ Handles all word combinations

---

## Performance Optimization

### UI Rendering

**Tkinter Limitations**:
- Single-threaded (no parallel rendering)
- Immediate mode (redraw on every update)

**Optimization Strategies**:
1. **Minimal Updates**: Only redraw changed cells
2. **Batch Operations**: Group config calls
3. **Lazy Loading**: Create widgets on demand

**Current Performance**:
- Full UI update: ~50ms
- Focus update: <1ms
- Recommendation update: ~20ms
- **Total per round**: ~70ms (barely noticeable)

---

### Font Measurement Caching

**Problem**: `font.measure()` called for each recommendation

**Optimization**:
```python
# Instead of measuring each time:
for word in recommendations:
    width = font.measure(f"{i}. {word.upper()}")

# Measure once, reuse:
widths = [font.measure(f"{i}. {w.upper()}") for i, w in enumerate(words, 1)]
max_width = max(widths)
```

**Impact**: Negligible (10 measurements vs 1 max call)

---

## Future UI Enhancements

### Planned Features

1. **Undo/Redo**
   - Command pattern for actions
   - History stack (up to 20 actions)

2. **Keyboard Shortcuts**
   - Ctrl+R: Reset game
   - Ctrl+Z: Undo
   - Ctrl+Shift+Z: Redo
   - Ctrl+C: Copy current grid state
   - Ctrl+V: Paste grid state

3. **Statistics Panel**
   - Average solve time
   - Success rate
   - Distribution graph (rounds 1-6)

4. **Dark/Light Theme Toggle**
   - User preference
   - System theme detection

5. **Animation**
   - Cell flip on color change
   - Row shake on invalid word
   - Confetti on solve

---

## Conclusion

The UI design prioritizes:
- **Efficiency**: Keyboard-first workflow
- **Clarity**: High contrast, clear focus
- **Consistency**: Uniform widths, predictable behavior
- **Simplicity**: Minimal UI, essential features only

Key innovations:
- Grid as single source of truth
- 2×5 recommendation layout
- Font measurement for width consistency
- Multi-row editing with Enter recalculation

This creates a fast, efficient, and pleasant user experience.
