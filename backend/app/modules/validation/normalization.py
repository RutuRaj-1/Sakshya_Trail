"""
Module 3 — Normalization Utilities for Validation and Duplicate Detection

Provides deterministic, testable normalization functions used by cross-source
reconciliation, duplicate detection, and name similarity rules.

Design constraints
------------------
* Normalizations are safe, idempotent, and explicitly documented.
* No raw PII or financial accounts are manipulated or logged here.
* Normalization never modifies database records — used strictly for evaluation comparisons.
"""
import re
from difflib import SequenceMatcher
from typing import Optional, Tuple


def normalize_reference_number(ref: Optional[str]) -> str:
    """
    Normalize an FDR/instrument reference number for duplicate detection
    and cross-source comparison.

    Transformations:
    1. Strip leading and trailing whitespace.
    2. Remove common formatting delimiters: spaces, hyphens, slashes, backslashes,
       dots, underscores.
    3. Convert to uppercase.

    Examples:
    - ' FDR/2026-001 ' -> 'FDR2026001'
    - '123-456/AB'     -> '123456AB'
    - 'fdr_0099'       -> 'FDR0099'
    """
    if not ref:
        return ""
    # Remove whitespace, hyphens, slashes, dots, underscores
    cleaned = re.sub(r"[\s\-\/\\._]+", "", ref)
    return cleaned.upper()


def normalize_bank_name(bank: Optional[str]) -> str:
    """
    Normalize a bank name for comparison and duplicate detection.

    Transformations:
    1. Strip leading and trailing whitespace.
    2. Collapse internal whitespace to a single space.
    3. Convert to uppercase.
    4. Strip common legal entity suffixes where appropriate (e.g. 'LTD', 'LIMITED').

    Examples:
    - ' State  Bank of India ' -> 'STATE BANK OF INDIA'
    - 'HDFC Bank Ltd.'          -> 'HDFC BANK'
    """
    if not bank:
        return ""
    cleaned = re.sub(r"\s+", " ", bank.strip()).upper()
    # Normalize common bank corporate suffixes
    cleaned = re.sub(r"\b(LTD\.?|LIMITED)\b", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def normalize_name_string(name: Optional[str]) -> str:
    """
    Normalize a person, institution, or depositor name string for similarity checks.

    Transformations:
    1. Strip whitespace and convert to lowercase.
    2. Remove punctuation and non-alphanumeric characters (except spaces).
    3. Collapse multiple spaces.
    4. Remove common educational/institutional prefixes and honorifics that cause
       artificial mismatches between registered institution names and bank FDR depositor names:
       e.g., 'm/s', 'dr.', 'prof.', 'shri', 'smt', 'the'.
    """
    if not name:
        return ""
    norm = name.strip().lower()
    # Remove common honorific / business prefixes
    norm = re.sub(r"^(m\/s\.?|dr\.?|prof\.?|shri\.?|smt\.?|the)\s+", "", norm)
    # Remove punctuation
    norm = re.sub(r"[^\w\s]", "", norm)
    # Collapse multiple spaces
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def calculate_name_similarity(name_a: Optional[str], name_b: Optional[str]) -> Tuple[float, str, str]:
    """
    Calculate deterministic string similarity between two names using Python's
    standard library difflib.SequenceMatcher (Ratcliff-Obershelp / Gestalt pattern matching).

    Returns:
    --------
    (similarity_score: float [0.0 - 1.0], normalized_a: str, normalized_b: str)

    Properties:
    - 100% deterministic (no external network or LLM dependency).
    - Identical strings return 1.0.
    - Completely dissimilar strings return 0.0.
    - Captures minor spelling variations, typos, and token reorderings reliably.
    """
    norm_a = normalize_name_string(name_a)
    norm_b = normalize_name_string(name_b)

    if not norm_a or not norm_b:
        return 0.0, norm_a, norm_b

    if norm_a == norm_b:
        return 1.0, norm_a, norm_b

    # Exact token set match (e.g. "College of Engineering" vs "Engineering College")
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if tokens_a == tokens_b:
        return 0.98, norm_a, norm_b

    matcher = SequenceMatcher(None, norm_a, norm_b)
    score = round(matcher.ratio(), 3)
    return score, norm_a, norm_b
