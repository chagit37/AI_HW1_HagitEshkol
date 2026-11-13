"""
מחלקת הבסיס SearchAlgorithm, שממנה יורשים AStar ו-IDAStar:
יוריסטיקה, מגבלות ריצה, מונים, עצירה ויומן חיפוש.
"""

import threading
import time
from abc import ABC, abstractmethod

from search_constants import CANCELLED, EXPANSION_LIMIT, TIMEOUT
from search_result import SearchResult


class SearchAlgorithm(ABC):
    """מחלקת בסיס: יוריסטיקה, מגבלות, מונים, עצירה ויומן חיפוש."""

    def __init__(self, problem, heuristic=None, time_limit=None, expansion_limit=None,
                 cancel_event=None, trace_limit=0):
        self.problem = problem
        self.heuristic = heuristic
        self.time_limit = time_limit            # בשניות; None = ללא מגבלה
        self.expansion_limit = expansion_limit  # None = ללא מגבלה
        self.cancel_event = cancel_event or threading.Event()
        self.trace_limit = trace_limit          # כמה רשומות לשמור ביומן החיפוש; 0 = בלי יומן
        self.expansions_count = 0
        self.generated_count = 0
        self.trace = []
        self._start_time = None

    @abstractmethod
    def search(self, heuristic=None):
        """מריצה את החיפוש ומחזירה SearchResult.

        heuristic - פונקציית היוריסטיקה לריצה הזו. אם לא נמסרה, משתמשים בזו
        שנמסרה בבנאי.
        """

    def check_stop_conditions(self, include_expansions=True):
        """מחזירה סטטוס עצירה (בקשת עצירה / זמן / הרחבות), או None אם אפשר להמשיך.

        את מגבלת ההרחבות בודקים רק רגע לפני הרחבה נוספת (include_expansions=True),
        כדי שהיא לא תמנע זיהוי של מצב יעד שכבר נשלף.
        """
        if self.cancel_event.is_set():
            return CANCELLED
        if self.time_limit is not None and time.perf_counter() - self._start_time >= self.time_limit:
            return TIMEOUT
        if (include_expansions and self.expansion_limit is not None
                and self.expansions_count >= self.expansion_limit):
            return EXPANSION_LIMIT
        return None

    def _start(self, heuristic=None):
        if heuristic is not None:
            self.heuristic = heuristic
        if self.heuristic is None:
            raise ValueError("a heuristic function is required")
        self.expansions_count = 0
        self.generated_count = 0
        self.max_open_size = None
        self.improvements_count = None
        self.iterations_count = None
        self.trace = []
        self._start_time = time.perf_counter()

    def _result(self, status, path=None, cost=None):
        return SearchResult(
            status=status,
            algorithm=type(self).__name__,
            heuristic=self.heuristic.__name__,
            path=path or [],
            cost=cost,
            expansions_count=self.expansions_count,
            generated=self.generated_count,
            max_open_size=self.max_open_size,
            improvements=self.improvements_count,
            iterations=self.iterations_count,
            elapsed_time=time.perf_counter() - self._start_time,
            trace=self.trace,
        )
