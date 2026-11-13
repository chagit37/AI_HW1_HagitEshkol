"""
אלגוריתם A*: חיפוש בגרף באמצעות תור עדיפויות.
"""

import heapq

from node import Node
from search_algorithm import SearchAlgorithm
from search_constants import (
    CHILD_ADDED, CHILD_IMPROVED, CHILD_REJECTED, NO_SOLUTION, POP_EXPANDED, POP_GOAL,
    POP_STALE, POP_STOPPED, SUCCESS,
)


class AStar(SearchAlgorithm):
    """חיפוש A* בגרף, באמצעות תור עדיפויות (heapq).

    יומן החיפוש (trace): רשומה לכל שליפה מ-Open, לפי סדר השליפה:
        order, state, g, h, f, open_size (גודל התור ברגע השליפה), parent (המצב הקודם),
        kind (מה קרה לרשומה), children (רשימת (מצב, g, h, מה קרה ליורש)).
    """

    def search(self, heuristic=None):
        self._start(heuristic)
        problem, heuristic = self.problem, self.heuristic

        # 1. אתחול: Node התחלתי (g=0, parent=None), nodes ו-Open מכילים אותו,
        #    Closed ריקה - המצב ההתחלתי התגלה אבל עדיין לא הורחב
        initial_state = problem.initial_state
        root = Node(initial_state, 0, heuristic(initial_state, problem), None)
        nodes = {initial_state: root}   # dict: state -> ה-Node הטוב ביותר שהתגלה
        # רשומה ב-Open היא (f, -g, state). סדר ההשוואה: f קטן קודם; בשוויון - g גדול
        # קודם (ערימת מינימום, לכן מינוס); בשוויון נוסף - לפי הייצוג הקנוני של המצב
        open_heap = [(root.f, -root.g, initial_state)]
        closed = set()                  # set של מצבים שכבר הורחבו
        self.max_open_size = 1          # הגודל המרבי של Open (כולל רשומות ישנות שעוד בתור)
        self.improvements_count = 0     # כמה פעמים נמצא מסלול זול יותר למצב מוכר
        pops = 0

        while open_heap:
            # 2. בדיקת תנאי עצירה: בקשת המשתמש ומגבלת הזמן
            status = self.check_stop_conditions(include_expansions=False)
            if status is not None:
                return self._result(status)

            # 3. שליפת הרשומה המינימלית מ-Open
            open_size = len(open_heap)
            _, neg_g, state = heapq.heappop(open_heap)
            node = nodes[state]
            pops += 1

            record = None
            if len(self.trace) < self.trace_limit:
                record = {
                    "order": pops, "state": state, "g": -neg_g, "h": node.h,
                    "f": -neg_g + node.h, "open_size": open_size,
                    "parent": node.parent.state if node.parent else None,
                    "kind": POP_EXPANDED, "children": [],
                }
                self.trace.append(record)

            # 4. רשומה ישנה (מחיקה עצלה): ה-g שלה אינו ה-g הטוב ביותר שב-nodes.
            #    מדלגים ושולפים את הבאה - בלי להרחיב ובלי להגדיל את המונה
            # 5. וכך גם אם המצב כבר הורחב
            if -neg_g != node.g or state in closed:
                if record:
                    record["kind"] = POP_STALE
                    record["parent"] = None  # האב של הרשומה הישנה כבר לא שמור
                continue

            # 6. בדיקת יעד - רק כאן, אחרי השליפה, ולא כשהילד נוצר
            if problem.is_goal(state):
                if record:
                    record["kind"] = POP_GOAL
                return self._result(SUCCESS, self.reconstruct_path(node), node.g)

            # 7. מגבלת ההרחבות נבדקת רגע לפני ההרחבה, ואז מרחיבים
            status = self.check_stop_conditions()
            if status is not None:
                if record:
                    record["kind"] = POP_STOPPED
                return self._result(status)
            closed.add(state)
            self.expansions_count += 1

            # 8. טיפול בכל ילד: קודם בודקים מול nodes, ורק אחר כך מול Closed.
            #    h מחושבת ו-Node נוצר רק אם המסלול חדש או משפר
            for child_state, cost in problem.get_childs(state):
                self.generated_count += 1                 # נוצר - לפני בדיקת כפילויות
                g_new = node.g + cost
                known = nodes.get(child_state)
                if known is None:
                    h = heuristic(child_state, problem)   # מצב חדש
                    outcome = CHILD_ADDED
                elif known.g <= g_new:
                    if record:                            # המסלול החדש לא משפר
                        record["children"].append((child_state, g_new, known.h, CHILD_REJECTED))
                    continue
                else:
                    h = known.h                           # מסלול זול יותר למצב מוכר
                    outcome = CHILD_IMPROVED
                    self.improvements_count += 1
                    # אם המצב כבר הורחב - פותחים אותו מחדש (תמיכה ביוריסטיקה לא עקבית)
                    closed.discard(child_state)
                nodes[child_state] = Node(child_state, g_new, h, node)
                # הרשומה הישנה של המצב (אם יש) נשארת ב-Open ותידחה בשלב 4
                heapq.heappush(open_heap, (g_new + h, -g_new, child_state))
                if record:
                    record["children"].append((child_state, g_new, h, outcome))
            if len(open_heap) > self.max_open_size:
                self.max_open_size = len(open_heap)

        # Open התרוקנה בלי שנמצא יעד - תוצאה תקינה, לא שגיאה
        return self._result(NO_SOLUTION)

    @staticmethod
    def reconstruct_path(node):
        """שחזור המסלול מהיעד להתחלה דרך parent, והפיכתו לסדר מההתחלה ליעד."""
        path = []
        while node is not None:
            path.append(node.state)
            node = node.parent
        path.reverse()
        return path
