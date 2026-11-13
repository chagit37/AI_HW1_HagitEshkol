"""
המחלקה SearchResult: התוצאה שכל אלגוריתם חיפוש מחזיר.
"""

from dataclasses import dataclass, field

from search_constants import SUCCESS


@dataclass
class SearchResult:
    """תוצאת ריצה: סטטוס, מסלול, עלות, נתונים סטטיסטיים ויומן החיפוש."""

    status: str
    algorithm: str
    heuristic: str
    path: list = field(default_factory=list)   # רשימת מצבים מההתחלה ועד היעד
    cost: float = None
    expansions_count: int = 0        # מצבים שפותחו: מצבים שהופקו מהם בנים
    generated: int = 0         # מצבים שנוצרו: כל בן שהופק, לפני בדיקת כפילויות
    max_open_size: int = None  # הגודל המרבי של תור העדיפויות (רק ב-A*)
    improvements: int = None   # מספר שיפורי עלות המסלול (רק ב-A*)
    iterations: int = None     # מספר האיטרציות (רק ב-IDA*)
    elapsed_time: float = 0.0
    trace: list = field(default_factory=list)  # יומן החיפוש (המבנה תלוי באלגוריתם)

    @property
    def solved(self):
        return self.status == SUCCESS
