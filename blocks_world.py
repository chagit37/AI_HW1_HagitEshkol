"""
בעיית הקוביות (Blocks World): המצבים, חוקי המשחק, וקריאה והדפסה של מצבים.

ייצוג מצב: tuple של tuple. כל tuple פנימי הוא ערימה אחת, מהקובייה התחתונה (על השולחן)
ועד העליונה. הערימות ממוינות לפי הקובייה התחתונה, כך ששני סידורים שנבדלים רק בסדר
הערימות על השולחן מקבלים את אותו ייצוג (ייצוג קנוני).
"""

import re

# דוגמת המטלה
EXAMPLE_INITIAL = "ד, א, ב, ג"
EXAMPLE_GOAL = "ד | א, ב, ג"


class BlocksWorld:
    """חוקי המשחק: ייצוג קנוני, תמיכה, פעולות חוקיות, יורשים ובדיקת מטרה."""

    MOVE_COST = 1  # שתי הפעולות עולות 1
    TABLE = "table"

    def __init__(self, initial_state, goal_state):
        self.initial_state = self.canonicalize(initial_state)
        self.goal_state = self.canonicalize(goal_state)

        initial_blocks = sorted(b for stack in self.initial_state for b in stack)
        goal_blocks = sorted(b for stack in self.goal_state for b in stack)
        if len(set(initial_blocks)) != len(initial_blocks) or len(set(goal_blocks)) != len(goal_blocks):
            raise ValueError("כל קובייה צריכה להופיע פעם אחת בלבד בכל מצב")
        if initial_blocks != goal_blocks:
            raise ValueError("המצב ההתחלתי ומצב היעד צריכים להכיל בדיוק אותן קוביות")

        # תמיכה במצב היעד - מחושבת פעם אחת ומשמשת את היוריסטיקות:
        # goal_support[b] = הקובייה שמתחת ל-b ביעד (None אם b על השולחן)
        self.goal_support = self.get_support(self.goal_state)

    @staticmethod
    def canonicalize(stacks):
        """ייצוג קנוני: מסירים ערימות ריקות וממיינים את הערימות לפי הקובייה התחתונה.

        הסדר בתוך כל ערימה נשמר כמו שהוא - הוא חלק מהמצב עצמו.
        """
        return tuple(sorted((tuple(stack) for stack in stacks if stack),
                            key=lambda stack: stack[0]))

    @staticmethod
    def get_support(state):
        """תמיכה ישירה: dict של קובייה -> הקובייה שמתחתיה (None אם היא על השולחן)."""
        support = {}
        for stack in state:
            below = None
            for block in stack:
                support[block] = below
                below = block
        return support

    def is_goal(self, state):
        return state == self.goal_state

    def move_to_table(self, state, src):
        """העברת הקובייה העליונה של ערימה src לערימה חדשה על השולחן.

        מחזירה None אם הקובייה כבר לבדה על השולחן - לא נוצר מצב חדש.
        """
        stack = state[src]
        if len(stack) == 1:
            return None
        stacks = list(state)
        stacks[src] = stack[:-1]
        stacks.append((stack[-1],))
        return self.canonicalize(stacks)

    def move_onto_block(self, state, src, dst):
        """העברת הקובייה העליונה של ערימה src אל ראש ערימה dst."""
        if src == dst:
            return None
        stacks = list(state)
        stacks[dst] = state[dst] + (state[src][-1],)
        stacks[src] = state[src][:-1]  # אם התרוקנה - canonicalize מסירה אותה
        return self.canonicalize(stacks)

    def get_action(self, state, next_state):
        """מזהה את הפעולה שהובילה מ-state ל-next_state: (קובייה, מקור, יעד).

        בין שני מצבים עוקבים יש בדיוק קובייה אחת שמה שמתחתיה השתנה - זו הקובייה
        שהוזזה. המקור והיעד הם הקובייה שמתחתיה לפני ואחרי, או TABLE.
        """
        before = self.get_support(state)
        after = self.get_support(next_state)
        for block, below in before.items():
            if after[block] != below:
                source = self.TABLE if below is None else below
                destination = self.TABLE if after[block] is None else after[block]
                return block, source, destination
        raise ValueError("the two states are identical")

    def get_solution_steps(self, path):
        """רשימת הפעולות של מסלול לפי סדרן: (קובייה, מקור, יעד, עלות מצטברת)."""
        steps = []
        cumulative_cost = 0
        for state, next_state in zip(path, path[1:]):
            block, source, destination = self.get_action(state, next_state)
            cumulative_cost += self.MOVE_COST
            steps.append((block, source, destination, cumulative_cost))
        return steps

    def get_childs(self, state):
        """כל המצבים שאפשר להגיע אליהם בהעברה חוקית אחת: רשימה של (מצב, עלות)."""
        successors = []
        for src in range(len(state)):
            child = self.move_to_table(state, src)
            if child is not None:
                successors.append((child, self.MOVE_COST))
            for dst in range(len(state)):
                child = self.move_onto_block(state, src, dst)
                if child is not None:
                    successors.append((child, self.MOVE_COST))
        return successors


# ---------------------------------------------------------------------------
# קלט ופלט של מצבים, ויצירת מצבים אקראיים
# ---------------------------------------------------------------------------
def parse_state(text):
    """הופכת טקסט למצב. ערימות מופרדות בקו | , קוביות מופרדות בפסיק או ברווח.

    כל ערימה נכתבת מהקובייה התחתונה לעליונה. לדוגמה: "ד | א, ב, ג".
    """
    stacks = []
    for part in re.split(r"[|;\n]", text):
        blocks = [block for block in re.split(r"[\s,]+", part.strip()) if block]
        if blocks:
            stacks.append(blocks)
    if not stacks:
        raise ValueError("יש להזין לפחות קובייה אחת")
    return stacks


def format_state(state):
    return " | ".join(", ".join(str(block) for block in stack) for stack in state)


BLOCK_NAMES = "אבגדהוזחטיכלמנסעפצקרשת"


def random_state(blocks, rng):
    """סידור אקראי של הקוביות בערימות."""
    blocks = list(blocks)
    rng.shuffle(blocks)
    stacks = [[]]
    for block in blocks:
        if stacks[-1] and rng.random() < 0.4:
            stacks.append([])  # מתחילים ערימה חדשה
        stacks[-1].append(block)
    return stacks


def generate_pair(block_count, rng):
    """זוג אקראי של מצב התחלתי ומצב יעד שונים, עם block_count קוביות."""
    blocks = BLOCK_NAMES[:block_count]
    while True:
        problem = BlocksWorld(random_state(blocks, rng), random_state(blocks, rng))
        if problem.initial_state != problem.goal_state:
            return problem
