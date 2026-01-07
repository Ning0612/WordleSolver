"""
Dictionary module for Wordle Solver.

Loads and cleans the five_letter_words.txt word list.
"""

from pathlib import Path
from typing import List, Set


def load_dictionary(filepath: str | Path) -> List[str]:
    """
    Load and clean the word list from five_letter_words.txt.

    Cleaning steps:
    1. Strip whitespace
    2. Convert to lowercase
    3. Filter: length == 5 and all alphabetic
    4. Remove duplicates
    5. Sort alphabetically

    Args:
        filepath: Path to the word list file

    Returns:
        List of cleaned, deduplicated, sorted 5-letter words

    Raises:
        FileNotFoundError: If the word list file doesn't exist
        ValueError: If no valid words found after cleaning
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Word list file not found: {filepath}")

    # Load and clean
    words: Set[str] = set()

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip().lower()

            # Filter: must be exactly 5 letters and all alphabetic
            if len(word) == 5 and word.isalpha():
                words.add(word)

    if not words:
        raise ValueError(f"No valid 5-letter words found in {filepath}")

    # Sort and return as list
    return sorted(words)


def get_word_list(custom_path: str | Path | None = None) -> List[str]:
    """
    Get the word list, using custom path or default location.

    Args:
        custom_path: Optional custom path to word list file.
                     If None, uses ../five_letter_words.txt relative to this file.

    Returns:
        List of cleaned, sorted 5-letter words
    """
    if custom_path:
        return load_dictionary(custom_path)

    # Default: five_letter_words.txt in data folder
    default_path = Path(__file__).parent.parent / "data" / "five_letter_words.txt"
    return load_dictionary(default_path)


if __name__ == "__main__":
    # Test loading
    words = get_word_list()
    print(f"Loaded {len(words)} words")
    print(f"First 10: {words[:10]}")
    print(f"Last 10: {words[-10:]}")
