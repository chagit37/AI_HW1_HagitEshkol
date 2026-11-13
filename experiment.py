"""
הניסוי ההשוואתי: הרצת כל זוג מצבים בשש השיטות, איסוף התוצאות וחישוב הטבלאות.
"""

import csv
import random
import statistics
import threading

from astar import AStar
from blocks_world import format_state, generate_pair
from heuristics import h1, h2, h_zero
from ida_star import IDAStar
from search_constants import EXPANSION_LIMIT, STATUS_MESSAGES, TIMEOUT

ALGORITHMS = {"A*": AStar, "IDA*": IDAStar}
HEURISTICS = {"h0": h_zero, "h1": h1, "h2": h2}


class ExperimentRunner:
    """מריצה כל זוג מצבים בשש השיטות, אוספת את התוצאות ומחשבת ממוצעים וסטיות תקן.

    pairs   - רשימת הזוגות; כל זוג הוא אובייקט BlocksWorld (מצב התחלתי ומצב יעד).
    results - dict: (מספר הזוג, שם האלגוריתם, שם היוריסטיקה) -> SearchResult.
    """

    # שש השיטות: כל אלגוריתם עם כל יוריסטיקה
    METHODS = [(algorithm, heuristic) for algorithm in ALGORITHMS for heuristic in HEURISTICS]
    # ברירת המחדל: 12 זוגות - שלושה זוגות לכל אחד מהגדלים 3, 5, 7, 9
    DEFAULT_SIZES = (3, 3, 3, 5, 5, 5, 7, 7, 7, 9, 9, 9)

    def __init__(self, pairs, time_limit=None, expansion_limit=None, cancel_event=None, seed=None):
        self.pairs = list(pairs)
        self.seed = seed            # הגרעין שממנו נוצרו הזוגות - נשמר רק לצורך תיעוד
        self.time_limit = time_limit
        self.expansion_limit = expansion_limit
        self.cancel_event = cancel_event or threading.Event()  # עוצר את הניסוי כולו
        self.results = {}
        self.current = None         # הריצה שמתבצעת כרגע: (מספר הזוג, אלגוריתם, יוריסטיקה)
        self.current_solver = None  # האלגוריתם שרץ כרגע (להצגת התקדמות)

    @staticmethod
    def generate_pairs(sizes=DEFAULT_SIZES, seed=1):
        """זוג אקראי לכל מספר קוביות ברשימה. אותו גרעין נותן תמיד את אותם זוגות."""
        rng = random.Random(seed)
        return [generate_pair(size, rng) for size in sizes]

    def run(self):
        """מריצה את כל הזוגות בכל השיטות. בלי יומן תצוגה, כדי שלא ישפיע על מדידת הזמן."""
        for pair_index, problem in enumerate(self.pairs):
            for algorithm_name, heuristic_name in self.METHODS:
                if self.cancel_event.is_set():
                    return self.results
                solver = ALGORITHMS[algorithm_name](
                    problem, time_limit=self.time_limit, expansion_limit=self.expansion_limit,
                    cancel_event=self.cancel_event)
                self.current_solver = solver
                self.current = (pair_index, algorithm_name, heuristic_name)
                # גם ריצה שנעצרה במגבלה מחזירה SearchResult עם זמן ומספר הרחבות, ו-cost=None
                self.results[self.current] = solver.search(HEURISTICS[heuristic_name])
        self.current = None
        return self.results

    def method_results(self, algorithm_name, heuristic_name):
        """כל התוצאות שנאספו עד כה לשיטה אחת."""
        keys = ((index, algorithm_name, heuristic_name) for index in range(len(self.pairs)))
        return [self.results[key] for key in keys if key in self.results]

    @staticmethod
    def mean_and_deviation(values):
        """ממוצע וסטיית תקן של מדגם (חלוקה ב-n-1). לערך יחיד סטיית התקן היא 0."""
        deviation = statistics.stdev(values) if len(values) > 1 else 0.0
        return statistics.mean(values), deviation

    def costs_agree(self):
        """האם בכל זוג, כל השיטות שמצאו פתרון מצאו אותה עלות (כמצופה מפתרון אופטימלי)."""
        for index in range(len(self.pairs)):
            costs = {self.results[(index, a, h)].cost for a, h in self.METHODS
                     if (index, a, h) in self.results and self.results[(index, a, h)].solved}
            if len(costs) > 1:
                return False
        return True

    # המדדים של טבלה 1, לפי הסדר
    MEASURES = ("זמן ממוצע בשניות", "סטיית תקן זמן", "פיתוחים - ממוצע", "פיתוחים - סטיית תקן",
                "הצלחות", "הגעה למגבלת ריצה")

    def performance_table(self):
        """הביצועים של כל שיטה - שורה לכל שיטה:
        (שיטה, זמן ממוצע, סטיית תקן זמן, פיתוחים ממוצעים, סטיית תקן פיתוחים, הצלחות, הגעה למגבלה).

        הממוצעים מחושבים על כל הריצות של השיטה, כולל ריצות שנעצרו במגבלה.
        """
        rows = []
        for algorithm_name, heuristic_name in self.METHODS:
            method = f"{algorithm_name} {heuristic_name}"
            results = self.method_results(algorithm_name, heuristic_name)
            if not results:
                rows.append((method, None, None, None, None, 0, 0))
                continue
            time_mean, time_deviation = self.mean_and_deviation([r.elapsed_time for r in results])
            expansions_mean, expansions_deviation = self.mean_and_deviation(
                [r.expansions_count for r in results])
            rows.append((
                method, time_mean, time_deviation, expansions_mean, expansions_deviation,
                sum(r.solved for r in results),
                sum(r.status in (TIMEOUT, EXPANSION_LIMIT) for r in results)))
        return rows

    def performance_by_measure(self):
        """טבלה 1 - אותם נתונים, הפוך: שורה לכל מדד ועמודה לכל שיטה.

        כל שורה: (שם המדד, ואז הערך בכל אחת משש השיטות לפי הסדר של METHODS).
        """
        by_method = self.performance_table()
        return [(measure, *[row[position + 1] for row in by_method])
                for position, measure in enumerate(self.MEASURES)]

    def runs_table(self):
        """טבלה 2 - שורה לכל ריצה שבוצעה (זוג אחד בשיטה אחת), מקובצת לפי זוג:
        (זוג, מספר קוביות, מצב התחלתי, מצב יעד, שיטה, תוצאה, עלות, השוואת עלות,
         זמן ריצה, מספר פיתוחים).

        העלות ריקה כשלא התקבל פתרון, והריצה אינה משתתפת בהשוואת העלות.
        השוואת עלות: "זהה" אם כל השיטות שפתרו את הזוג הגיעו לאותה עלות, אחרת "שונה".
        """
        rows = []
        for pair_index, problem in enumerate(self.pairs):
            blocks = sum(len(stack) for stack in problem.initial_state)
            initial, goal = format_state(problem.initial_state), format_state(problem.goal_state)
            results = [(a, h, self.results.get((pair_index, a, h))) for a, h in self.METHODS]
            solved_costs = [r.cost for _, _, r in results if r is not None and r.solved]
            if len(solved_costs) < 2:
                comparison = "פתרון יחיד"   # אין מול מי להשוות
            else:
                comparison = "זהה" if len(set(solved_costs)) == 1 else "שונה"
            for algorithm_name, heuristic_name, result in results:
                if result is None:
                    continue  # הריצה עוד לא בוצעה
                rows.append((
                    pair_index + 1, blocks, initial, goal, f"{algorithm_name} {heuristic_name}",
                    STATUS_MESSAGES[result.status],
                    result.cost if result.solved else "", comparison if result.solved else "",
                    result.elapsed_time, result.expansions_count))
        return rows

    def save_csv(self, path):
        """שומרת את שתי הטבלאות לקובץ CSV (נפתח באקסל)."""
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)

            def rounded(value):
                return "" if value is None else round(value, 4)

            # תיעוד תנאי הניסוי
            writer.writerow(["גרעין אקראי (seed)", "" if self.seed is None else self.seed])
            writer.writerow(["מספר זוגות", len(self.pairs)])
            writer.writerow(["מגבלת זמן בשניות", "" if self.time_limit is None else self.time_limit])
            writer.writerow(["מגבלת פיתוחים",
                             "" if self.expansion_limit is None else self.expansion_limit])
            writer.writerow([])
            methods = [f"{a} {h}" for a, h in self.METHODS]
            writer.writerow(["טבלה 1 - השוואת ביצועי השיטות"])
            writer.writerow(["מדד", *methods])
            for measure, *values in self.performance_by_measure():
                writer.writerow([measure, *(rounded(value) for value in values)])
            writer.writerow([])
            writer.writerow(["טבלה 2 - פירוט כל הריצות לפי זוג מצבים"])
            writer.writerow(["זוג", "מספר קוביות", "מצב התחלתי", "מצב יעד", "שיטה", "תוצאה", "עלות",
                             "השוואת עלות בין השיטות שפתרו", "זמן בשניות", "פיתוחים"])
            for *start, elapsed_time, expansions in self.runs_table():
                writer.writerow([*start, f"{elapsed_time:.6f}", expansions])
            writer.writerow(["בכל זוג, כל השיטות שמצאו פתרון מצאו אותה עלות:",
                             "כן" if self.costs_agree() else "לא"])
