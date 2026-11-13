"""
הקבועים המשותפים לאלגוריתמי החיפוש: סטטוס התוצאה, ההודעות למשתמש, וערכי יומן החיפוש.
"""

# סטטוסים אפשריים של תוצאת חיפוש
SUCCESS = "success"
NO_SOLUTION = "no_solution"
TIMEOUT = "timeout"
EXPANSION_LIMIT = "expansion_limit"
CANCELLED = "cancelled"

# הודעה למשתמש לכל סיבת עצירה
STATUS_MESSAGES = {
    SUCCESS: "נמצא פתרון",
    NO_SOLUTION: "לא קיים פתרון",
    TIMEOUT: "הריצה הופסקה במגבלה (מגבלת הזמן)",
    EXPANSION_LIMIT: "הריצה הופסקה במגבלה (מגבלת מספר הפיתוחים)",
    CANCELLED: "הריצה נעצרה לבקשת המשתמש",
}

# יומן החיפוש של A*: מה קרה לרשומה שנשלפה מ-Open
POP_EXPANDED = "expanded"   # המצב פותח
POP_GOAL = "goal"           # המצב הוא היעד
POP_STALE = "stale"         # רשומה ישנה - דילוג
POP_STOPPED = "stopped"     # הריצה נעצרה לפני הפיתוח

# יומן החיפוש של A*: מה קרה ליורש של מצב שפותח
CHILD_ADDED = "added"         # מצב חדש - נוסף ל-Open
CHILD_IMPROVED = "improved"   # נמצא מסלול זול יותר למצב מוכר
CHILD_REJECTED = "rejected"   # המסלול החדש אינו משפר - נדחה
