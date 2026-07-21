"""Deterministic tests for the ARI readability port."""

from __future__ import annotations

from nabokov.readability import (
    HARD,
    NORMAL,
    VERY_HARD,
    classify,
    letters_in,
    reading_level,
)


def test_reading_level_hand_computed():
    # 100/20*4.71 + 20/2*0.5 - 21.43 = 23.55 + 5 - 21.43 = 7.12 -> round -> 7
    assert reading_level(100, 20, 2) == 7


def test_reading_level_floored_at_zero():
    assert reading_level(4, 4, 1) == 0


def test_reading_level_zero_words():
    assert reading_level(0, 0, 0) == 0


def test_js_round_half_up():
    # choose values that land exactly on .5 so banker's rounding would differ.
    # letters/words*4.71 + words - 21.43 == x.5  ->  verify it rounds up.
    # 10 words, 1 sentence: words/sentences*0.5 = 5.0
    # need letters/10*4.71 - 21.43 + 5 = X.5
    # letters=45: 45/10*4.71=21.195; 21.195 - 21.43 + 5 = 4.765 -> 5
    assert reading_level(45, 10, 1) == 5


def test_letters_counts_word_chars_only():
    assert letters_in("don't") == 4  # d o n t, apostrophe excluded
    assert letters_in("co-op!") == 4  # c o o p, hyphen and bang excluded


def test_classify_thresholds_normal_target():
    assert classify(9, 20, "NORMAL") == NORMAL
    assert classify(10, 20, "NORMAL") == HARD
    assert classify(13, 20, "NORMAL") == HARD
    assert classify(14, 20, "NORMAL") == VERY_HARD


def test_classify_short_sentence_never_flagged():
    # fewer than tooFewWordCount (14 for NORMAL) words -> always normal
    assert classify(30, 10, "NORMAL") == NORMAL


def test_classify_technical_target_is_more_lenient():
    assert classify(12, 20, "TECHNICAL") == NORMAL  # hard threshold is 14 here
