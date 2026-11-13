"""
שלוש היוריסטיקות. כולן מקבלות (state, problem) ומחזירות הערכה לעלות שנותרה עד היעד.
"""


def h_zero(state, problem):
    """h0 - יוריסטיקת האפס. A* מתנהג איתה כמו Uniform Cost Search."""
    return 0


def h1(state, problem):
    """h1 = X: מספר הקוביות שנמצאות במקום שגוי.

    קובייה במקום שגוי אם התמיכה הישירה שלה (הקובייה שמתחתיה, או השולחן) שונה
    מהתמיכה הישירה שלה ביעד.
    כל קובייה כזו חייבת לזוז לפחות פעם אחת, וכל פעולה מזיזה קובייה אחת,
    ולכן היוריסטיקה קבילה (וגם עקבית).
    """
    goal_support = problem.goal_support
    misplaced = 0
    for stack in state:
        below = None
        for block in stack:
            if goal_support[block] != below:
                misplaced += 1
            below = block
    return misplaced


def h2(state, problem):
    """h2 = X + 2Y.

    X - מספר הקוביות במקום שגוי (כמו ב-h1).
    Y - מספר הקוביות שנמצאות במקום תקין (מונחות על מה שצריך להיות מתחתיהן ביעד),
        אבל אי שם מתחתיהן באותה ערימה יש קובייה במקום שגוי. כדי להוציא את הקובייה
        השגויה חייבים לפנות אותן: פעם אחת למקום לא תקין, ופעם שנייה בחזרה למקומן.
    מתקיים h2 >= h1, והיא עדיין קבילה ועקבית.
    """
    goal_support = problem.goal_support
    total = 0
    for stack in state:
        misplaced_below = False  # האם כבר ראינו בערימה הזו קובייה במקום שגוי
        below = None
        for block in stack:
            if goal_support[block] != below:
                total += 1          # שייכת ל-X
                misplaced_below = True
            elif misplaced_below:
                total += 2          # שייכת ל-Y
            below = block
    return total
