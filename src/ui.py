"""
UI module for Wordle Solver.

Implements Wordle-style interface with keyboard interaction:
- Arrow key navigation (Up/Down/Left/Right) for focus movement
- Space to cycle colors (Gray → Yellow → Green)
- Letter input with auto-advance
- Enter to recalculate constraints from all complete rows
- 2×5 grid layout for recommendations with consistent width
"""

import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont
from dataclasses import dataclass, field
from typing import List, Tuple

from dictionary import get_word_list
from constraints import Constraint, FeedbackRound, FeedbackColor
from solver import filter_candidates
from stats import LetterStats
from recommender import WordRecommender


# Color scheme (tool-oriented, distinct from Wordle's official colors)
COLORS = {
    "bg_dark": "#0F172A",            # 主背景（深藍黑）
    "bg_frame": "#1E293B",           # 區塊 / 框線背景
    "letter_empty": "#334155",       # 尚未判定
    "letter_gray": "#475569",        # 不存在於答案中
    "letter_orange": "#F97316",      # 存在於答案中但位置錯誤（橘色）
    "letter_blue": "#3B82F6",        # 位置正確（藍色）
    "text": "#E5E7EB",               # 主要文字顏色
    "recommend_bg": "#020617",       # 推薦區背景
    "recommend_candidate": "#3B82F6",# 最佳候選（exploitation）
    "recommend_explore": "#F97316",  # 探索型猜測（exploration）
}


# Feedback color mapping (using blue/orange instead of green/yellow)
FEEDBACK_COLORS = {
    FeedbackColor.GRAY: COLORS["letter_gray"],
    FeedbackColor.YELLOW: COLORS["letter_orange"],  # Orange for present but wrong position
    FeedbackColor.GREEN: COLORS["letter_blue"],     # Blue for correct position
}


@dataclass
class AppState:
    """Centralized application state."""
    # Grid data: 6×5 for all rows (single source of truth)
    history_grid_letters: List[List[str]] = field(
        default_factory=lambda: [[""] * 5 for _ in range(6)]
    )
    history_grid_colors: List[List[FeedbackColor]] = field(
        default_factory=lambda: [[FeedbackColor.GRAY] * 5 for _ in range(6)]
    )

    # Focus position: row and column in grid (0-5 for row, 0-4 for col)
    focused_row: int = 0
    focused_col: int = 0

    # Legacy fields (kept for compatibility, but grid is source of truth)
    current_guess: List[str] = field(default_factory=lambda: [""] * 5)
    current_colors: List[FeedbackColor] = field(
        default_factory=lambda: [FeedbackColor.GRAY] * 5
    )
    current_position: int = 0  # Current input position (0-4)

    history: List[FeedbackRound] = field(default_factory=list)
    recommendations: List[Tuple[str, float]] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)
    current_constraint: Constraint = field(default_factory=Constraint)
    round_number: int = 1

    def reset(self):
        """Reset all state for new game."""
        self.history_grid_letters = [[""] * 5 for _ in range(6)]
        self.history_grid_colors = [[FeedbackColor.GRAY] * 5 for _ in range(6)]
        self.focused_row = 0
        self.focused_col = 0
        self.current_guess = [""] * 5
        self.current_colors = [FeedbackColor.GRAY] * 5
        self.current_position = 0
        self.history = []
        self.recommendations = []
        self.candidates = []
        self.current_constraint = Constraint()
        self.round_number = 1


class WordleSolverApp:
    """
    Wordle Solver with redesigned UI.

    Layout:
    - Top: Recommendations (simple word list with color coding)
    - Middle: Wordle grid (5×6 boxes for input/history)
    - Bottom: RESET button

    Keyboard interaction:
    - Letter keys: Input and auto-advance (uppercase)
    - Space: Cycle color of current letter
    - Enter: Submit round
    - Backspace: Delete last letter
    """

    def __init__(self, master: tk.Tk):
        """Initialize application."""
        self.master = master
        self.master.title("Wordle Solver - Independent Analysis Tool")
        # Codex fix: Increase height to show full 6 rows + RESET button
        self.master.geometry("500x1000")
        self.master.configure(bg=COLORS["bg_dark"])

        # Set minimum size
        self.master.minsize(500, 850)

        # Disable window resizing for consistent layout
        self.master.resizable(False, False)

        # Initialize model
        try:
            self.words = get_word_list()
            self.stats = LetterStats(self.words)
            self.recommender = WordRecommender(
                self.words,
                self.stats,
                weights_file="config/weights.json"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load resources: {e}")
            self.master.destroy()
            return

        # Initialize state
        self.state = AppState()
        self.state.candidates = self.words.copy()

        # UI widgets storage
        self.history_labels = []  # History grid labels (6×5 for all rounds)
        self.recommend_labels = []  # Recommendation labels
        # Codex fix: letter_labels will point to current history row (no separate row 7)

        # Create UI
        self._create_widgets()

        # Bind keyboard events (Codex fix: use bind_all to capture globally)
        self.master.bind_all("<Key>", self._on_key_press)

        # Set initial focus to master (Codex fix: ensure keyboard events work)
        self.master.focus_set()

        # Initial recommendations
        self._update_recommendations()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container
        main_frame = tk.Frame(self.master, bg=COLORS["bg_dark"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Top: Recommendations
        self._create_recommend_area(main_frame)

        # Middle: Wordle grid
        self._create_wordle_grid(main_frame)

        # Bottom: RESET button
        self._create_controls(main_frame)

    def _create_recommend_area(self, parent):
        """
        Create recommendation area (top half).

        2×5 grid layout with numbered recommendations:
        - Green: Phase 1 candidate
        - Yellow/Orange: Phase 2 exploration
        """
        frame = tk.Frame(parent, bg=COLORS["recommend_bg"], relief=tk.RAISED, bd=2)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Disclaimer
        disclaimer = tk.Label(
            frame,
            text="Independent Wordle-solving tool. Not affiliated with The New York Times.",
            font=("Helvetica Neue", 10),
            bg=COLORS["recommend_bg"],
            fg="#9CA3AF"
        )
        disclaimer.pack(pady=(5, 0))

        # Title
        title = tk.Label(
            frame,
            text="Word Analysis & Recommendations",
            font=("Helvetica Neue", 18, "bold"),
            bg=COLORS["recommend_bg"],
            fg="#E5E7EB"
        )
        title.pack(pady=(5, 5))

        # Legend
        legend_frame = tk.Frame(frame, bg=COLORS["recommend_bg"])
        legend_frame.pack(pady=(0, 5))

        legend_candidate = tk.Label(
            legend_frame,
            text="● Candidate",
            font=("Helvetica Neue", 12),
            bg=COLORS["recommend_bg"],
            fg=COLORS["recommend_candidate"]
        )
        legend_candidate.pack(side=tk.LEFT, padx=10)

        legend_explore = tk.Label(
            legend_frame,
            text="● Exploration",
            font=("Helvetica Neue", 12),
            bg=COLORS["recommend_bg"],
            fg=COLORS["recommend_explore"]
        )
        legend_explore.pack(side=tk.LEFT, padx=10)

        # Grid container for recommendations (2 columns × 5 rows)
        grid_frame = tk.Frame(frame, bg=COLORS["recommend_bg"])
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 15))

        # Configure grid columns for equal width
        grid_frame.grid_columnconfigure(0, weight=1, uniform="rec")
        grid_frame.grid_columnconfigure(1, weight=1, uniform="rec")

        # Store reference for updates
        self.recommend_frame = grid_frame

    def _create_wordle_grid(self, parent):
        """
        Create Wordle-style grid (6×5).

        All 6 rows are history rows.
        Current input uses the active history row (round_number - 1).
        Codex fix: Removed separate row 7 for input.
        """
        grid_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        grid_frame.pack(pady=10)

        # History grid (6 rows × 5 columns) - All rows are history
        for row in range(6):
            row_labels = []
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
                row_labels.append(label)
            self.history_labels.append(row_labels)

    def _create_controls(self, parent):
        """Create control buttons (bottom)."""
        control_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        control_frame.pack(pady=10)

        reset_btn = tk.Button(
            control_frame,
            text="RESET",
            font=("Helvetica Neue", 14, "bold"),
            bg=COLORS["bg_frame"],
            fg=COLORS["text"],
            width=12,
            height=2,
            command=self._reset_game,
            cursor="hand2"
        )
        reset_btn.pack()

    # === Keyboard Event Handlers ===

    def _on_key_press(self, event):
        """
        Handle keyboard input.

        - Letter (a-z): Input letter and advance
        - Space: Cycle color of current letter
        - Enter: Submit round (recalculate from all complete rows)
        - BackSpace: Delete last letter
        - Arrow keys: Move focus (Up/Down/Left/Right)
        """
        key = event.keysym

        # Letter input (a-z or A-Z)
        if key.isalpha() and len(key) == 1:
            self._input_letter(key.upper())

        # Space: Cycle color
        elif key == "space":
            self._cycle_current_color()

        # Enter: Submit (recalculate all complete rows)
        elif key == "Return":
            self._submit_round()

        # Backspace: Delete
        elif key == "BackSpace":
            self._delete_letter()

        # Arrow keys: Move focus
        elif key in ("Left", "Right", "Up", "Down"):
            self._move_focus(key)

    def _move_focus(self, direction: str):
        """
        Move focus in grid using arrow keys.

        Args:
            direction: "Left", "Right", "Up", or "Down"
        """
        if direction == "Left":
            self.state.focused_col = max(0, self.state.focused_col - 1)
        elif direction == "Right":
            self.state.focused_col = min(4, self.state.focused_col + 1)
        elif direction == "Up":
            self.state.focused_row = max(0, self.state.focused_row - 1)
        elif direction == "Down":
            self.state.focused_row = min(5, self.state.focused_row + 1)

        # Update visual focus indicator
        self._update_input_focus()

    def _input_letter(self, letter: str):
        """
        Input a letter at current focused position.

        Uses focused_row and focused_col for input.
        Advances focus to right after input.

        Args:
            letter: Letter to input (uppercase)
        """
        row = self.state.focused_row
        col = self.state.focused_col

        # Update grid state (source of truth)
        self.state.history_grid_letters[row][col] = letter.lower()

        # Update UI - show letter and current color
        current_color = self.state.history_grid_colors[row][col]
        self.history_labels[row][col].config(
            text=letter,
            bg=FEEDBACK_COLORS[current_color]
        )

        # Advance focus to right (only if not last column)
        if self.state.focused_col < 4:
            self.state.focused_col += 1

        # Update visual focus
        self._update_input_focus()

    def _cycle_current_color(self):
        """
        Cycle color of current focused cell.

        User flow: Set color first → then input letter.
        Gray → Orange (present) → Blue (correct) → Gray
        """
        row = self.state.focused_row
        col = self.state.focused_col

        current_color = self.state.history_grid_colors[row][col]

        # Cycle: Gray → Orange → Blue → Gray
        if current_color == FeedbackColor.GRAY:
            next_color = FeedbackColor.YELLOW
        elif current_color == FeedbackColor.YELLOW:
            next_color = FeedbackColor.GREEN
        else:
            next_color = FeedbackColor.GRAY

        # Update grid state
        self.state.history_grid_colors[row][col] = next_color

        # Update UI (apply color even if cell is empty)
        self.history_labels[row][col].config(bg=FEEDBACK_COLORS[next_color])

    def _delete_letter(self):
        """
        Delete letter at current focused cell and move left.

        Deletes current cell, then moves focus left.
        """
        row = self.state.focused_row
        col = self.state.focused_col

        # Clear current cell
        self.state.history_grid_letters[row][col] = ""
        self.state.history_grid_colors[row][col] = FeedbackColor.GRAY
        self.history_labels[row][col].config(
            text="",
            bg=COLORS["letter_empty"]
        )

        # Move focus left (unless already at leftmost column)
        if self.state.focused_col > 0:
            self.state.focused_col -= 1

        # Update visual focus
        self._update_input_focus()

    def _submit_round(self):
        """
        Recalculate constraints from all complete rows.

        Scans all 6 rows, finds complete 5-letter rows,
        rebuilds constraints and candidates from scratch.
        """
        try:
            # Scan all 6 rows and collect complete rounds
            rounds = []
            for row in range(6):
                guess = "".join(self.state.history_grid_letters[row])

                # Check if row is complete (5 letters, all alphabetic)
                if len(guess) == 5 and guess.isalpha() and guess.isascii():
                    rounds.append(FeedbackRound(
                        guess=guess,
                        feedback=self.state.history_grid_colors[row].copy()
                    ))

            # If no complete rows, show warning
            if not rounds:
                messagebox.showwarning("No Complete Rows", "Please fill at least one complete 5-letter row")
                return

            # Rebuild constraint from all complete rounds
            merged_constraint = Constraint()
            for round_feedback in rounds:
                round_constraint = round_feedback.to_constraint()
                merged_constraint = merged_constraint.merge(round_constraint)

            # Update state
            self.state.history = rounds
            self.state.current_constraint = merged_constraint
            self.state.round_number = len(rounds) + 1

            # Recalculate candidates
            self.state.candidates = filter_candidates(self.words, merged_constraint)

            # Update UI
            self._update_recommendations()

            # Move focus to next row after submit (Requirement 1)
            # Find next empty row or stay at current if all rows complete
            next_row = self.state.round_number - 1  # round_number is already incremented
            if next_row < 6:
                self.state.focused_row = next_row
                self.state.focused_col = 0
                self._update_input_focus()

            # Check if solved or no candidates
            if len(self.state.candidates) == 1:
                messagebox.showinfo("Solved!", f"Answer: {self.state.candidates[0].upper()}")
            elif len(self.state.candidates) == 0:
                messagebox.showwarning("No Candidates", "Check your feedback colors")

        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")

    def _reset_game(self):
        """Reset game to initial state."""
        self.state.reset()
        self.state.candidates = self.words.copy()

        # Clear all UI
        self._clear_input()
        self._clear_history()
        self._update_recommendations()

    def _fill_guess(self, word: str):
        """
        Fill focused row with selected word from recommendations.

        Auto-fills on double-click, using focused_row.

        Args:
            word: Word to fill (lowercase)
        """
        row = self.state.focused_row

        # Clear focused row first
        for col in range(5):
            self.state.history_grid_letters[row][col] = ""
            self.state.history_grid_colors[row][col] = FeedbackColor.GRAY
            self.history_labels[row][col].config(
                text="",
                bg=COLORS["letter_empty"]
            )

        # Fill each letter
        for col, letter in enumerate(word):
            self.state.history_grid_letters[row][col] = letter
            self.history_labels[row][col].config(
                text=letter.upper(),
                bg=FEEDBACK_COLORS[FeedbackColor.GRAY]
            )

        # Set focus to start of row
        self.state.focused_col = 0

        # Update focus indicator
        self._update_input_focus()

        # Return focus to master (avoid keyboard loss)
        self.master.focus_set()

    # === UI Update Methods ===

    def _update_input_focus(self):
        """
        Update visual focus indicator for full 6×5 grid.

        Highlights focused_row and focused_col cell with SUNKEN relief.
        """
        for row in range(6):
            for col in range(5):
                label = self.history_labels[row][col]
                if row == self.state.focused_row and col == self.state.focused_col:
                    label.config(relief=tk.SUNKEN, bd=4)
                else:
                    label.config(relief=tk.FLAT, bd=2)

    def _clear_input(self):
        """
        Clear focused row.

        Clears the row at focused_row position.
        """
        row = self.state.focused_row

        # Clear grid data
        for col in range(5):
            self.state.history_grid_letters[row][col] = ""
            self.state.history_grid_colors[row][col] = FeedbackColor.GRAY

        # Clear UI
        for col in range(5):
            self.history_labels[row][col].config(
                text="",
                bg=COLORS["letter_empty"],
                relief=tk.FLAT,
                bd=2
            )

        # Reset focus to start of row
        self.state.focused_col = 0
        self._update_input_focus()

    def _clear_history(self):
        """Clear entire history grid."""
        # Clear grid data
        self.state.history_grid_letters = [[""] * 5 for _ in range(6)]
        self.state.history_grid_colors = [[FeedbackColor.GRAY] * 5 for _ in range(6)]

        # Clear UI
        for row in range(6):
            for col in range(5):
                self.history_labels[row][col].config(
                    text="",
                    bg=COLORS["letter_empty"],
                    relief=tk.FLAT,
                    bd=2
                )

        # Reset focus to top-left
        self.state.focused_row = 0
        self.state.focused_col = 0
        self._update_input_focus()

    def _update_history(self):
        """
        Update history grid with submitted rounds.

        Codex fix: Only update submitted rows, not current input row.
        """
        # Only update rows that have been submitted (history)
        for row_idx, round_data in enumerate(self.state.history):
            if row_idx >= 6:
                break

            for col_idx, (letter, color) in enumerate(zip(round_data.guess, round_data.feedback)):
                self.history_labels[row_idx][col_idx].config(
                    text=letter.upper(),
                    bg=FEEDBACK_COLORS[color],
                    relief=tk.FLAT,
                    bd=2
                )

    def _update_recommendations(self):
        """
        Update recommendation list with split layout.

        Left column: Candidate words (blue)
        Right column: Exploration words (orange)
        Each column shows top 5 by score.
        """
        # Clear existing recommendations
        for widget in self.recommend_frame.winfo_children():
            widget.destroy()

        self.recommend_labels.clear()

        try:
            # Get recommendations (top 5 each category)
            recs = self.recommender.recommend(
                candidates=self.state.candidates,
                constraint=self.state.current_constraint,
                round_number=self.state.round_number,
                top_n=5
            )

            # Extract candidates and explorations
            candidates_list = recs["candidates"]
            explorations_list = recs["explorations"]

            # Measure font to calculate consistent width
            measure_font = tkfont.Font(family="Helvetica Neue", size=16, weight="bold")

            # Calculate max width from both lists
            all_words = [(w, i) for i, (w, _) in enumerate(candidates_list, 1)] + \
                        [(w, i) for i, (w, _) in enumerate(explorations_list, 1)]

            if all_words:
                max_word_width = max(measure_font.measure(f"{i}. {w.upper()}") for w, i in all_words)
            else:
                max_word_width = measure_font.measure("1. XXXXX")  # Fallback

            col_width = max_word_width + 40  # Add padding

            # Set minimum column width for consistency
            self.recommend_frame.grid_columnconfigure(0, minsize=col_width, uniform="rec")
            self.recommend_frame.grid_columnconfigure(1, minsize=col_width, uniform="rec")

            # Display LEFT column: Candidates (Blue)
            if candidates_list:
                for i, (word, score) in enumerate(candidates_list[:5], 1):
                    row = i - 1  # 0-4
                    col = 0      # Left column

                    # Container frame for colored background
                    item_frame = tk.Frame(
                        self.recommend_frame,
                        bg=COLORS["recommend_candidate"],  # Blue
                        relief=tk.FLAT,
                        bd=1
                    )
                    item_frame.grid(row=row, column=col, padx=8, pady=4, sticky="nsew")

                    # Label with number and word
                    label = tk.Label(
                        item_frame,
                        text=f"{i}. {word.upper()}",
                        font=("Helvetica Neue", 16, "bold"),
                        bg=COLORS["recommend_candidate"],
                        fg=COLORS["text"],
                        anchor="center",
                        justify="center",
                        padx=20,
                        pady=5
                    )
                    label.pack(fill=tk.BOTH, expand=True)

                    # Add double-click event to auto-fill
                    label.bind("<Double-Button-1>", lambda e, w=word: self._fill_guess(w))
                    item_frame.bind("<Double-Button-1>", lambda e, w=word: self._fill_guess(w))

                    self.recommend_labels.append(label)
            else:
                # Show empty state message for candidates
                empty_label = tk.Label(
                    self.recommend_frame,
                    text="No candidates\n(Check feedback)",
                    font=("Helvetica Neue", 12),
                    bg=COLORS["recommend_bg"],
                    fg="#9CA3AF",
                    anchor="center",
                    justify="center"
                )
                empty_label.grid(row=0, column=0, rowspan=5, padx=8, pady=20, sticky="nsew")

            # Display RIGHT column: Explorations (Orange)
            if explorations_list:
                for i, (word, score) in enumerate(explorations_list[:5], 1):
                    row = i - 1  # 0-4
                    col = 1      # Right column

                    # Container frame for colored background
                    item_frame = tk.Frame(
                        self.recommend_frame,
                        bg=COLORS["recommend_explore"],  # Orange
                        relief=tk.FLAT,
                        bd=1
                    )
                    item_frame.grid(row=row, column=col, padx=8, pady=4, sticky="nsew")

                    # Label with number and word
                    label = tk.Label(
                        item_frame,
                        text=f"{i}. {word.upper()}",
                        font=("Helvetica Neue", 16, "bold"),
                        bg=COLORS["recommend_explore"],
                        fg=COLORS["text"],
                        anchor="center",
                        justify="center",
                        padx=20,
                        pady=5
                    )
                    label.pack(fill=tk.BOTH, expand=True)

                    # Add double-click event to auto-fill
                    label.bind("<Double-Button-1>", lambda e, w=word: self._fill_guess(w))
                    item_frame.bind("<Double-Button-1>", lambda e, w=word: self._fill_guess(w))

                    self.recommend_labels.append(label)
            else:
                # Show empty state message for explorations
                empty_label = tk.Label(
                    self.recommend_frame,
                    text="No exploration words\n(All words are candidates)",
                    font=("Helvetica Neue", 12),
                    bg=COLORS["recommend_bg"],
                    fg="#9CA3AF",
                    anchor="center",
                    justify="center"
                )
                empty_label.grid(row=0, column=1, rowspan=5, padx=8, pady=20, sticky="nsew")

        except Exception as e:
            error_label = tk.Label(
                self.recommend_frame,
                text=f"Error: {e}",
                font=("Helvetica Neue", 12),
                bg=COLORS["recommend_bg"],
                fg="red"
            )
            error_label.grid(row=0, column=0, columnspan=2, pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = WordleSolverApp(root)
    root.mainloop()
