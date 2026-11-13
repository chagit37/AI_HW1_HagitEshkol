"""
אלגוריתם IDA*: חיפוש לעומק עם סף f שגדל מאיטרציה לאיטרציה.
"""

from search_algorithm import SearchAlgorithm
from search_constants import NO_SOLUTION, SUCCESS


class _SearchStopped(Exception):
    """נזרקת מתוך הרקורסיה של IDA* כשאחד מתנאי העצירה מתקיים."""

    def __init__(self, status):
        self.status = status


class IDAStar(SearchAlgorithm):
    """חיפוש עומק עם סף f שגדל מאיטרציה לאיטרציה. אין קבוצת Closed גלובלית.

    יומן החיפוש (trace): רשומה לכל איטרציה:
        number, threshold, expansions, prunes, next_threshold,
        expanded - המצבים שפותחו, pruned - דוגמאות לגיזום עקב חריגה מהסף.
        כל פריט בשתי הרשימות הוא (מצב, המצב הקודם, g, h, f).
    """

    PRUNE_EXAMPLES = 50  # כמה דוגמאות גיזום לשמור בכל איטרציה

    def search(self, heuristic=None):
        self._start(heuristic)
        problem = self.problem
        root = problem.initial_state
        threshold = self.heuristic(root, problem)  # הסף הראשון: האומדן של מצב ההתחלה
        # המסלול הרקורסיבי הנוכחי - מבנה יחיד: dict שומר את סדר ההכנסה (כמו רשימה)
        # ובודק שייכות ב-O(1) (כמו set). רק המפתחות חשובים, הערכים תמיד None
        path = {root: None}
        self.iterations_count = 0

        try:
            while True:
                self.iterations_count += 1
                self._iteration = {
                    "number": len(self.trace) + 1, "threshold": threshold,
                    "expansions": 0, "prunes": 0, "next_threshold": None,
                    "expanded": [], "pruned": [],
                }
                self.trace.append(self._iteration)

                found, value = self._dfs(path, root, None, 0, threshold)
                if found:
                    return self._result(SUCCESS, list(path), value)
                if value == float("inf"):
                    return self._result(NO_SOLUTION)
                self._iteration["next_threshold"] = value
                threshold = value  # ה-f הקטן ביותר שחרג מהסף הנוכחי
        except _SearchStopped as stop:
            return self._result(stop.status)

    def _dfs(self, path, state, parent, g, threshold):
        """מחזירה (True, עלות הפתרון) או (False, ה-f הקטן ביותר שחרג מהסף).

        state הוא המצב האחרון ב-path, ו-parent הוא המצב שלפניו (None בשורש).
        מעבירים אותם כפרמטרים כי ל-dict אין גישה לפי מיקום כמו path[-1].
        """
        problem = self.problem
        iteration = self._iteration
        h = self.heuristic(state, problem)
        f = g + h

        # גיזום: ערך ההערכה הכולל גדול מהסף
        if f > threshold:
            iteration["prunes"] += 1
            if len(iteration["pruned"]) < min(self.trace_limit, self.PRUNE_EXAMPLES):
                iteration["pruned"].append((state, parent, g, h, f))
            return False, f
        if problem.is_goal(state):
            return True, g

        status = self.check_stop_conditions()
        if status is not None:
            raise _SearchStopped(status)
        self.expansions_count += 1
        iteration["expansions"] += 1
        if len(iteration["expanded"]) < self.trace_limit:
            iteration["expanded"].append((state, parent, g, h, f))

        minimum = float("inf")
        for child, cost in problem.get_childs(state):
            self.generated_count += 1  # נוצר - לפני בדיקת כפילויות
            if child in path:          # מניעת מעגל: הילד כבר במסלול הנוכחי (O(1))
                continue
            path[child] = None         # הוספה לסוף המסלול
            found, value = self._dfs(path, child, state, g + cost, threshold)
            if found:
                return True, value
            path.popitem()             # הסרת האחרון שהוכנס - חזרה אחורה במסלול
            minimum = min(minimum, value)
        return False, minimum
