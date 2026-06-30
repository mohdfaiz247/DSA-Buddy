"""
SM-2 Spaced Repetition Algorithm implementation.

The SM-2 algorithm computes the next review interval for a problem
based on how well the user recalled it (quality score 0-5).

Formula:
  EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
  EF  >= 1.3 (clamped)
  
  If q < 3:
    I = 1  (relearn tomorrow)
  Else:
    If n == 0: I = 1
    If n == 1: I = 6
    If n > 1:  I = round(I_prev * EF)

Reference: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class SMCard:
    """State for a single problem in the SM-2 system."""
    problem_slug: str
    user_id: str
    ef: float = 2.5          # Ease Factor — starts at 2.5
    interval: int = 1         # Days until next review
    repetitions: int = 0      # Number of successful reviews
    next_review: date = None  # Scheduled review date

    def __post_init__(self):
        if self.next_review is None:
            self.next_review = date.today()


def sm2_update(card: SMCard, quality: int) -> SMCard:
    """
    Update a card's SM-2 state given a quality rating (0-5).
    
    Quality scale:
      5 - Perfect response
      4 - Correct with slight hesitation
      3 - Correct with serious difficulty
      2 - Incorrect but answer was easy to recall
      1 - Incorrect, but answer seemed easy
      0 - Blackout, no memory at all
    """
    q = max(0, min(5, quality))

    # Update ease factor
    new_ef = card.ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = max(1.3, new_ef)

    if q < 3:
        # Failed recall → restart from beginning
        new_repetitions = 0
        new_interval = 1
    else:
        # Successful recall
        new_repetitions = card.repetitions + 1
        if card.repetitions == 0:
            new_interval = 1
        elif card.repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(card.interval * new_ef)

    next_review = date.today() + timedelta(days=new_interval)

    return SMCard(
        problem_slug=card.problem_slug,
        user_id=card.user_id,
        ef=new_ef,
        interval=new_interval,
        repetitions=new_repetitions,
        next_review=next_review,
    )


def quality_from_time(time_seconds: int, difficulty: str) -> int:
    """
    Heuristic: derive quality rating from solve time vs expected time.
    Used when we have no explicit quality score from the user.
    """
    expected = {"easy": 600, "medium": 1200, "hard": 2400}.get(difficulty, 1200)
    ratio = time_seconds / expected

    if ratio <= 0.5:   return 5  # Very fast — perfect
    if ratio <= 0.75:  return 4  # Fast — good
    if ratio <= 1.0:   return 3  # On-time — acceptable
    if ratio <= 1.5:   return 2  # Slow — struggled
    return 1                      # Very slow — struggled a lot
