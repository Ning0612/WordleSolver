"""
Main entry point for Wordle Solver application.
"""

import tkinter as tk
import sys
from pathlib import Path

# Add src to path if running from project root
sys.path.insert(0, str(Path(__file__).parent))

from ui import WordleSolverApp


def main():
    """Launch Wordle Solver GUI application."""
    root = tk.Tk()
    app = WordleSolverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
