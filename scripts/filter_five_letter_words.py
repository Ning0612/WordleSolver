#!/usr/bin/env python3
"""
Five-Letter Word Filter Script

This script filters word lists to extract only five-letter alphabetic English words.
It reads from an input word list file and outputs to 'data/five_letter_words.txt'.

Usage:
    python scripts/filter_five_letter_words.py <input_file_path>

Example:
    python scripts/filter_five_letter_words.py wordlist.txt
"""

import sys
from pathlib import Path


def is_valid_five_letter_word(word: str) -> bool:
    """
    Check if a word is a valid five-letter alphabetic English word.
    
    Args:
        word: The word to check
        
    Returns:
        True if word contains exactly 5 alphabetic characters, False otherwise
    """
    word = word.strip().lower()
    return len(word) == 5 and word.isalpha()


def filter_five_letter_words(input_path: str, output_path: str = "data/five_letter_words.txt") -> None:
    """
    Filter five-letter words from input file and write to output file.
    
    Args:
        input_path: Path to input word list file (one word per line)
        output_path: Path to output file (default: data/five_letter_words.txt)
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)
    
    if not input_file.is_file():
        print(f"Error: '{input_path}' is not a file.")
        sys.exit(1)
    
    print(f"Reading words from: {input_path}")
    
    five_letter_words = []
    total_words = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                total_words += 1
                
                if is_valid_five_letter_word(word):
                    five_letter_words.append(word.lower())
    
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    # Sort words alphabetically and remove duplicates
    five_letter_words = sorted(set(five_letter_words))
    
    # Write to output file
    output_file = Path(output_path)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for word in five_letter_words:
                f.write(word + '\n')
        
        print(f"\nFiltering complete:")
        print(f"  Total words processed: {total_words:,}")
        print(f"  Five-letter words found: {len(five_letter_words):,}")
        print(f"  Output written to: {output_path}")
    
    except Exception as e:
        print(f"Error writing file: {e}")
        sys.exit(1)


def main():
    """Main entry point for the script."""
    if len(sys.argv) != 2:
        print("Usage: python filter_five_letter_words.py <input_file_path>")
        print("\nExample:")
        print("  python filter_five_letter_words.py wordlist.txt")
        sys.exit(1)
    
    input_path = sys.argv[1]
    filter_five_letter_words(input_path)


if __name__ == "__main__":
    main()
