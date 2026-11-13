"""
הממשק הגרפי: הזנת מצבים, הרצה, מסלול הפתרון, תהליך החיפוש, השוואת ריצות וניסוי השוואתי.
"""

import os
import re
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from blocks_world import (
    BLOCK_NAMES, EXAMPLE_GOAL, EXAMPLE_INITIAL, BlocksWorld, format_state, parse_state,
)
from experiment import ALGORITHMS, HEURISTICS, ExperimentRunner
from ida_star import IDAStar
from report import save_html_report
from search_constants import (
    CHILD_ADDED, CHILD_IMPROVED, CHILD_REJECTED, POP_EXPANDED, POP_GOAL, POP_STALE,
    POP_STOPPED, STATUS_MESSAGES,
)


class BlocksWorldApp:
    """מסך אחד: הזנת מצבים, הרצה, מסלול הפתרון, תהליך החיפוש והשוואת ריצות."""

    ALGORITHMS = ALGORITHMS
    HEURISTICS = HEURISTICS
    TRACE_LIMIT = 5000  # כמה רשומות של יומן החיפוש לשמור ולהציג

    POP_TEXT = {
        POP_EXPANDED: "פותח",
        POP_GOAL: "מצב היעד",
        POP_STALE: "רשומה ישנה - דילוג",
        POP_STOPPED: "לא פותח - הריצה נעצרה",
    }
    CHILD_TEXT = {CHILD_ADDED: "נוסף", CHILD_IMPROVED: "שופר", CHILD_REJECTED: "נדחה"}

    def __init__(self, root):
        self.root = root
        self.problem = None
        self.result = None
        self.solver = None
        self.thread = None
        self.error = None
        self.queue = []      # ריצות שממתינות (כפתור "הרץ את כל השיטות")
        self.runner = None                 # ה-ExperimentRunner של הניסוי האחרון
        self.shown_experiment_results = 0  # כמה תוצאות ניסוי כבר מוצגות בטבלאות
        self.astar_trace = []  # יומן החיפוש המוצג של A*
        self.ida_trace = []    # יומן החיפוש המוצג של IDA*
        self.path = []       # מסלול הפתרון המוצג
        self.steps = []      # הפעולות של המסלול
        self.step = 0        # הצעד המוצג כרגע

        root.title("בעיית הקוביות - A* ו-IDA*")
        # גודל החלון מותאם למסך, כדי ששום חלק ממנו לא ייחתך
        width = min(1180, root.winfo_screenwidth() - 60)
        height = min(760, root.winfo_screenheight() - 110)
        root.geometry(f"{width}x{height}+20+10")
        root.minsize(min(900, width), min(560, height))
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_input()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._build_solution_tab()
        self._build_search_tab()
        self._build_runs_tab()
        self._build_experiment_tab()

    # ----- בניית המסך -----
    def _build_input(self):
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill=tk.X)
        frame.columnconfigure(0, weight=1)

        self.initial_var = tk.StringVar(value=EXAMPLE_INITIAL)
        self.goal_var = tk.StringVar(value=EXAMPLE_GOAL)
        for row, (label, variable) in enumerate((("מצב התחלתי", self.initial_var),
                                                 ("מצב יעד", self.goal_var))):
            ttk.Entry(frame, textvariable=variable, justify=tk.RIGHT, font=("Segoe UI", 11)).grid(
                row=row, column=0, sticky="ew", pady=2)
            ttk.Label(frame, text=label, width=12, anchor="e").grid(row=row, column=1, padx=(8, 0))
        ttk.Label(
            frame, anchor="e", foreground="#555555",
            text="כל ערימה נכתבת מהקובייה התחתונה לעליונה. קוביות מופרדות בפסיק, ערימות מופרדות בקו אנכי",
        ).grid(row=2, column=0, columnspan=2, sticky="e", pady=(0, 6))

        controls = ttk.Frame(frame)
        controls.grid(row=3, column=0, columnspan=2, sticky="e")
        self.algorithm_var = tk.StringVar(value="A*")
        self.heuristic_var = tk.StringVar(value="h2")
        self.time_limit_var = tk.StringVar(value="30")
        self.expansion_limit_var = tk.StringVar(value="500000")

        def add(widget, label):
            ttk.Label(controls, text=label).pack(side=tk.RIGHT, padx=(10, 3))
            widget.pack(side=tk.RIGHT)

        add(ttk.Combobox(controls, textvariable=self.algorithm_var, state="readonly", width=6,
                         values=list(self.ALGORITHMS)), "אלגוריתם")
        add(ttk.Combobox(controls, textvariable=self.heuristic_var, state="readonly", width=5,
                         values=list(self.HEURISTICS)), "יוריסטיקה")
        add(ttk.Entry(controls, textvariable=self.time_limit_var, width=7), "מגבלת זמן בשניות")
        add(ttk.Entry(controls, textvariable=self.expansion_limit_var, width=10), "מגבלת פיתוחים")

        self.run_button = ttk.Button(controls, text="הרץ", command=self.run_selected)
        self.run_all_button = ttk.Button(controls, text="הרץ את כל השיטות", command=self.run_all)
        self.stop_button = ttk.Button(controls, text="עצור", command=self.stop, state=tk.DISABLED)
        for button in (self.run_button, self.run_all_button, self.stop_button):
            button.pack(side=tk.RIGHT, padx=(10, 0))

        self.status_var = tk.StringVar(value="הזינו מצב התחלתי ומצב יעד ולחצו על הרץ")
        self.stats_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.status_var, anchor="e",
                  font=("Segoe UI", 11, "bold")).grid(row=4, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Label(frame, textvariable=self.stats_var, anchor="e").grid(
            row=5, column=0, columnspan=2, sticky="e")

    @staticmethod
    def _make_tree(parent, columns, height=8):
        """טבלה עם פס גלילה. columns: רשימה של (מזהה, כותרת, רוחב, יישור)."""
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", height=height)
        for name, heading, width, anchor in columns:
            tree.heading(name, text=heading)
            tree.column(name, width=width, anchor=anchor, stretch=True)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return frame, tree

    @staticmethod
    def _fill(tree, rows):
        tree.delete(*tree.get_children())
        for index, row in enumerate(rows):
            tree.insert("", tk.END, iid=str(index), values=row)

    def _build_solution_tab(self):
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="מסלול הפתרון")
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(1, weight=1)

        self.cost_var = tk.StringVar()
        ttk.Label(tab, textvariable=self.cost_var, anchor="e",
                  font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="e")

        # צד שמאל: ציור הערימות וצעידה במצבים
        left = ttk.Frame(tab)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.canvas = tk.Canvas(left, background="#f1f6fb", highlightthickness=1, height=180,
                                highlightbackground="#c5d3e3")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda event: self._draw_state())
        self.step_var = tk.StringVar()
        ttk.Label(left, textvariable=self.step_var, anchor="center").pack(fill=tk.X, pady=4)
        navigation = ttk.Frame(left)
        navigation.pack()
        for text, command in (("סוף", lambda: self._go_to(len(self.path) - 1)),
                              ("הבא", lambda: self._go_to(self.step + 1)),
                              ("הקודם", lambda: self._go_to(self.step - 1)),
                              ("התחלה", lambda: self._go_to(0))):
            ttk.Button(navigation, text=text, command=command, width=8).pack(side=tk.LEFT, padx=2)

        # צד ימין: רצף הפעולות
        frame, self.steps_tree = self._make_tree(tab, [
            ("cost", "עלות מצטברת", 90, "center"),
            ("to", "יעד", 70, "center"),
            ("from", "מקור", 70, "center"),
            ("block", "קובייה", 70, "center"),
            ("step", "צעד", 50, "center"),
        ], height=6)
        frame.grid(row=1, column=1, sticky="nsew")
        self.steps_tree.bind("<<TreeviewSelect>>", self._on_step_selected)

    def _build_search_tab(self):
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="תהליך החיפוש")
        self.search_note_var = tk.StringVar(value="יומן החיפוש יוצג כאן אחרי הרצה")
        ttk.Label(tab, textvariable=self.search_note_var, anchor="e").pack(fill=tk.X)

        state_column = ("state", "מצב", 260, "e")
        action_column = ("action", "הפעולה שהובילה למצב", 170, "e")
        numbers = [("f", "f = g + h", 70, "center"), ("h", "h", 50, "center"), ("g", "g", 50, "center")]

        # --- A* ---
        self.astar_frame = ttk.Frame(tab)
        ttk.Label(self.astar_frame, anchor="e",
                  text="המצבים לפי סדר השליפה מתור המצבים הפתוחים (בחרו שורה כדי לראות את היורשים)").pack(fill=tk.X)
        frame, self.pops_tree = self._make_tree(self.astar_frame, [
            ("kind", "מה קרה", 150, "e"), action_column, ("open", "גודל התור", 80, "center"),
            *numbers, state_column, ("order", "שליפה", 60, "center"),
        ], height=7)
        frame.pack(fill=tk.BOTH, expand=True)
        self.pops_tree.bind("<<TreeviewSelect>>", self._on_pop_selected)
        self.children_title_var = tk.StringVar(value="היורשים של המצב שנבחר")
        ttk.Label(self.astar_frame, textvariable=self.children_title_var, anchor="e").pack(fill=tk.X, pady=(6, 0))
        frame, self.children_tree = self._make_tree(self.astar_frame, [
            ("outcome", "מה קרה ליורש", 150, "e"), ("action", "הפעולה", 170, "e"),
            *numbers, state_column,
        ], height=4)
        frame.pack(fill=tk.BOTH, expand=True)

        # --- IDA* ---
        self.ida_frame = ttk.Frame(tab)
        ttk.Label(self.ida_frame, anchor="e",
                  text="האיטרציות (בחרו שורה כדי לראות את המצבים שפותחו ודוגמאות לגיזום)").pack(fill=tk.X)
        frame, self.iterations_tree = self._make_tree(self.ida_frame, [
            ("next", "הסף הבא", 100, "center"), ("prunes", "מספר הגיזומים", 120, "center"),
            ("expansions", "מספר הפיתוחים", 120, "center"), ("threshold", "סף", 80, "center"),
            ("number", "איטרציה", 80, "center"),
        ], height=5)
        frame.pack(fill=tk.X)
        self.iterations_tree.bind("<<TreeviewSelect>>", self._on_iteration_selected)
        lower = ttk.Frame(self.ida_frame)
        lower.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        lower.columnconfigure(0, weight=1)
        lower.columnconfigure(1, weight=1)
        lower.rowconfigure(1, weight=1)
        ttk.Label(lower, text="דוגמאות לגיזום עקב חריגה מהסף", anchor="e").grid(row=0, column=0, sticky="ew")
        ttk.Label(lower, text="המצבים שפותחו באיטרציה, לפי הסדר", anchor="e").grid(row=0, column=1, sticky="ew")
        columns = [("action", "הפעולה", 140, "e"), *numbers, ("state", "מצב", 200, "e")]
        frame, self.pruned_tree = self._make_tree(lower, columns, height=5)
        frame.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        frame, self.expanded_tree = self._make_tree(lower, columns, height=5)
        frame.grid(row=1, column=1, sticky="nsew")

    def _build_runs_tab(self):
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="השוואת ריצות")
        frame, self.runs_tree = self._make_tree(tab, [
            ("iterations", "איטרציות", 70, "center"), ("improvements", "שיפורי עלות", 85, "center"),
            ("max_open", "גודל תור מרבי", 85, "center"), ("expansions", "מצבים שפותחו", 90, "center"),
            ("generated", "מצבים שנוצרו", 90, "center"), ("time", "זמן בשניות", 80, "center"),
            ("cost", "עלות", 45, "center"), ("status", "תוצאה", 190, "e"),
            ("heuristic", "יוריסטיקה", 70, "center"), ("algorithm", "אלגוריתם", 70, "center"),
            ("goal", "מצב יעד", 105, "e"), ("initial", "מצב התחלתי", 105, "e"),
        ], height=8)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(tab, text="נקה את הטבלה",
                   command=lambda: self.runs_tree.delete(*self.runs_tree.get_children())).pack(pady=6)

    def _build_experiment_tab(self):
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="ניסוי השוואתי")
        self.methods = ExperimentRunner.METHODS  # שש השיטות

        controls = ttk.Frame(tab)
        controls.pack(fill=tk.X)
        self.sizes_var = tk.StringVar(value=", ".join(str(s) for s in ExperimentRunner.DEFAULT_SIZES))
        self.seed_var = tk.StringVar(value="1")
        ttk.Label(controls, text="מספר הקוביות בכל זוג מצבים").pack(side=tk.RIGHT, padx=(10, 3))
        ttk.Entry(controls, textvariable=self.sizes_var, width=34).pack(side=tk.RIGHT)
        ttk.Label(controls, text="גרעין אקראי").pack(side=tk.RIGHT, padx=(10, 3))
        ttk.Entry(controls, textvariable=self.seed_var, width=6).pack(side=tk.RIGHT)
        self.experiment_button = ttk.Button(controls, text="הרץ ניסוי", command=self.run_experiment)
        self.experiment_button.pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(controls, text="שמור את הטבלאות לקובץ CSV",
                   command=self.save_experiment).pack(side=tk.RIGHT, padx=(10, 0))
        for note in ("כל זוג מצבים נוצר באקראי ומורץ בשש השיטות, עם המגבלות שהוגדרו למעלה",
                     "הממוצע וסטיית התקן מחושבים על כל הריצות של השיטה, כולל ריצות שנעצרו במגבלה"):
            ttk.Label(tab, anchor="e", foreground="#555555", text=note).pack(fill=tk.X)

        method_columns = [(f"{a} {h}", f"{a} {h}", 80, "center") for a, h in reversed(self.methods)]

        # טבלה 1: עמודה לכל שיטה, שורה לכל מדד
        ttk.Label(tab, text="טבלה 1 - השוואת ביצועי השיטות", anchor="e",
                  font=("Segoe UI", 10, "bold")).pack(fill=tk.X)
        frame, self.table1_tree = self._make_tree(
            tab, [*method_columns, ("measure", "מדד", 150, "e")], height=6)
        frame.pack(fill=tk.X)

        # טבלה 2: שורה לכל ריצה (זוג אחד בשיטה אחת). שש השורות של כל זוג צמודות
        # וצבועות באותו רקע, כך שקל לראות שהעלות זהה בכל השיטות שפתרו את הזוג
        ttk.Label(tab, text="טבלה 2 - פירוט כל הריצות לפי זוג מצבים", anchor="e",
                  font=("Segoe UI", 10, "bold")).pack(fill=tk.X, pady=(6, 0))
        self.agree_note_var = tk.StringVar()
        ttk.Label(tab, textvariable=self.agree_note_var, anchor="e", foreground="#555555").pack(fill=tk.X)
        frame, self.table2_tree = self._make_tree(tab, [
            ("expansions", "פיתוחים", 85, "center"), ("time", "זמן בשניות", 85, "center"),
            ("compare", "השוואת עלות", 95, "center"), ("cost", "עלות", 55, "center"),
            ("status", "תוצאה", 215, "e"), ("method", "שיטה", 75, "center"),
            ("goal", "מצב יעד", 165, "e"), ("initial", "מצב התחלתי", 165, "e"),
            ("blocks", "מספר קוביות", 85, "center"), ("pair", "זוג", 45, "center"),
        ], height=7)
        frame.pack(fill=tk.BOTH, expand=True)
        self.table2_tree.tag_configure("shaded", background="#e8eff7")
        self.table2_tree.tag_configure("different", foreground="#c00000")

    # ----- הרצה -----
    def run_selected(self):
        self.queue = [(self.algorithm_var.get(), self.heuristic_var.get())]
        self._run_next()

    def run_all(self):
        self.queue = list(ExperimentRunner.METHODS)
        self._run_next()

    def _set_running(self, running):
        for button in (self.run_button, self.run_all_button, self.experiment_button):
            button.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_button.configure(state=tk.NORMAL if running else tk.DISABLED)

    # ----- הניסוי ההשוואתי: המסך רק מפעיל את ExperimentRunner ומציג את הטבלאות שלו -----
    def run_experiment(self):
        try:
            sizes = [int(text) for text in re.split(r"[\s,]+", self.sizes_var.get().strip()) if text]
            seed = int(self.seed_var.get().strip())
        except ValueError:
            messagebox.showerror("קלט שגוי", "מספרי הקוביות והגרעין האקראי צריכים להיות מספרים שלמים",
                                 parent=self.root)
            return
        if not sizes or min(sizes) < 2 or max(sizes) > len(BLOCK_NAMES):
            messagebox.showerror("קלט שגוי", f"מספר הקוביות צריך להיות בין 2 ל-{len(BLOCK_NAMES)}",
                                 parent=self.root)
            return
        try:
            time_limit = self._read_limit(self.time_limit_var.get(), float, "מגבלת זמן")
            expansion_limit = self._read_limit(self.expansion_limit_var.get(), int, "מגבלת פיתוחים")
        except ValueError as error:
            messagebox.showerror("קלט שגוי", str(error), parent=self.root)
            return

        self.runner = ExperimentRunner(ExperimentRunner.generate_pairs(sizes, seed),
                                       time_limit=time_limit, expansion_limit=expansion_limit,
                                       seed=seed)
        self.error = None
        self._refresh_experiment()
        self._set_running(True)
        self.thread = threading.Thread(target=self._experiment_worker, args=(self.runner,), daemon=True)
        self.thread.start()
        self.root.after(50, self._poll_experiment)

    def _experiment_worker(self, runner):
        try:
            runner.run()
        except Exception as error:
            self.error = error

    def _poll_experiment(self):
        runner = self.runner
        if len(runner.results) != self.shown_experiment_results:
            self._refresh_experiment()
        if self.thread.is_alive():
            current, solver = runner.current, runner.current_solver
            if current is not None and solver is not None:
                pair_index, algorithm_name, heuristic_name = current
                self.status_var.set(f"הניסוי רץ: זוג {pair_index + 1} מתוך {len(runner.pairs)}")
                self.stats_var.set(f"{algorithm_name}  {heuristic_name}     "
                                   f"פיתוחים עד כה: {solver.expansions_count:,}")
            self.root.after(150, self._poll_experiment)
            return
        self._set_running(False)
        self.stats_var.set("")
        if self.error is not None:
            self.status_var.set("הניסוי נכשל")
            messagebox.showerror("שגיאה", str(self.error), parent=self.root)
        elif runner.cancel_event.is_set():
            self.status_var.set("הניסוי נעצר לבקשת המשתמש")
        else:
            self.status_var.set("הניסוי הסתיים")

    def _refresh_experiment(self):
        runner = self.runner
        self.shown_experiment_results = len(runner.results)

        def text(value, pattern):
            return "-" if value is None else format(value, pattern)

        # טבלה 1: שורה לכל מדד, עם תבנית התצוגה של המספרים שלו
        patterns = (".4f", ".4f", ",.1f", ",.1f", "d", "d")
        table1 = [(measure, *[text(value, pattern) for value in values])
                  for (measure, *values), pattern in zip(runner.performance_by_measure(), patterns)]
        self.agree_note_var.set(
            "בכל זוג, כל השיטות שמצאו פתרון מצאו אותה עלות" if runner.costs_agree()
            else "שימו לב: יש זוג שבו שיטות שונות מצאו עלויות שונות")
        # בטבלאות שעל המסך העמודות מסודרות מימין לשמאל, ולכן הופכים כל שורה
        self._fill(self.table1_tree, [tuple(reversed(row)) for row in table1])

        # טבלה 2: רקע מתחלף בין זוג לזוג, וצבע אדום לזוג שבו העלויות שונות
        tree = self.table2_tree
        tree.delete(*tree.get_children())
        for *start, elapsed_time, expansions in runner.runs_table():
            pair, comparison = start[0], start[7]
            tags = (["shaded"] if pair % 2 == 0 else []) + (["different"] if comparison == "שונה" else [])
            row = (*start, f"{elapsed_time:.4f}", f"{expansions:,}")
            tree.insert("", tk.END, values=tuple(reversed(row)), tags=tags)

    def save_experiment(self):
        """שומר את שתי הטבלאות לקובץ CSV ליד הסקריפט (נפתח באקסל)."""
        if self.runner is None:
            messagebox.showinfo("ניסוי השוואתי", "אין עדיין תוצאות. הריצו ניסוי קודם.", parent=self.root)
            return
        folder = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(folder, "experiment_results.csv")
        report_path = os.path.join(folder, "experiment_report.html")
        try:
            self.runner.save_csv(path)
            save_html_report(self.runner, report_path)
        except OSError as error:
            messagebox.showerror("שמירה נכשלה", str(error), parent=self.root)
            return
        messagebox.showinfo("ניסוי השוואתי",
                            f"הטבלאות נשמרו בקובץ:\n{path}\n\nדוח מעוצב לפתיחה בדפדפן:\n{report_path}",
                            parent=self.root)

    def stop(self):
        """עצירת ריצה מתמשכת: מדליקים את cancel_event, והחיפוש נעצר בבדיקה הבאה."""
        self.queue = []
        if self.solver is not None:
            self.solver.cancel_event.set()
        if self.runner is not None and self.thread is not None and self.thread.is_alive():
            self.runner.cancel_event.set()

    @staticmethod
    def _read_limit(text, convert, name):
        text = text.strip()
        if not text:
            return None
        try:
            value = convert(text)
        except ValueError:
            raise ValueError(f"{name}: יש להזין מספר, או להשאיר ריק")
        if value <= 0:
            raise ValueError(f"{name}: המספר צריך להיות חיובי")
        return value

    def _run_next(self):
        if not self.queue:
            return
        algorithm_name, heuristic_name = self.queue.pop(0)
        try:
            problem = BlocksWorld(parse_state(self.initial_var.get()), parse_state(self.goal_var.get()))
            time_limit = self._read_limit(self.time_limit_var.get(), float, "מגבלת זמן")
            expansion_limit = self._read_limit(self.expansion_limit_var.get(), int, "מגבלת פיתוחים")
        except ValueError as error:
            self.queue = []
            messagebox.showerror("קלט שגוי", str(error), parent=self.root)
            return

        self.problem = problem
        self.run_names = (algorithm_name, heuristic_name)
        self.result = None
        self.error = None
        self.solver = ALGORITHMS[algorithm_name](
            problem, time_limit=time_limit, expansion_limit=expansion_limit,
            trace_limit=self.TRACE_LIMIT)
        heuristic = HEURISTICS[heuristic_name]

        # החיפוש רץ בתהליכון נפרד, כדי שהמסך יישאר פעיל ואפשר יהיה ללחוץ על "עצור"
        self.thread = threading.Thread(target=self._worker, args=(self.solver, heuristic), daemon=True)
        self._set_running(True)
        self.status_var.set("החיפוש רץ...")
        self.thread.start()
        self.root.after(50, self._poll)

    def _worker(self, solver, heuristic):
        try:
            self.result = solver.search(heuristic)
        except Exception as error:  # למשל חריגה מעומק הרקורסיה
            self.error = error

    def _poll(self):
        if self.thread.is_alive():
            self.stats_var.set(f"{self.run_names[0]}  {self.run_names[1]}     "
                               f"פיתוחים עד כה: {self.solver.expansions_count:,}")
            self.root.after(100, self._poll)
            return
        self._set_running(False)
        if self.error is not None:
            self.queue = []
            self.status_var.set("החיפוש נכשל")
            messagebox.showerror("שגיאה", str(self.error), parent=self.root)
            return
        self._show_result()
        self._run_next()

    # ----- הצגת התוצאה -----
    def _place(self, place):
        return "שולחן" if place == BlocksWorld.TABLE else str(place)

    def _action_text(self, parent, state):
        if parent is None:
            return "-"
        block, source, destination = self.problem.get_action(parent, state)
        return f"{block}: {self._place(source)} -> {self._place(destination)}"

    def _show_result(self):
        result, problem = self.result, self.problem
        algorithm_name, heuristic_name = self.run_names
        self.status_var.set(STATUS_MESSAGES[result.status])
        cost = result.cost if result.solved else "-"

        def number(value):
            return "-" if value is None else f"{value:,}"

        # המדדים של הריצה
        stats = (f"{algorithm_name}  {heuristic_name}     עלות: {cost}     "
                 f"זמן ריצה: {result.elapsed_time:.3f} שניות     מצבים שנוצרו: {result.generated:,}     "
                 f"מצבים שפותחו: {result.expansions_count:,}")
        if algorithm_name == "A*":
            stats += (f"     גודל תור מרבי: {number(result.max_open_size)}     "
                      f"שיפורי עלות מסלול: {number(result.improvements)}")
        else:
            stats += f"     איטרציות: {number(result.iterations)}"
        self.stats_var.set(stats)
        self.runs_tree.insert("", tk.END, values=(
            number(result.iterations), number(result.improvements), number(result.max_open_size),
            f"{result.expansions_count:,}", f"{result.generated:,}", f"{result.elapsed_time:.3f}", cost,
            STATUS_MESSAGES[result.status], heuristic_name, algorithm_name,
            format_state(problem.goal_state), format_state(problem.initial_state)))

        # מסלול הפתרון
        self.path = result.path
        self.steps = problem.get_solution_steps(result.path)
        self.cost_var.set(f"עלות כוללת: {result.cost}" if result.solved
                          else STATUS_MESSAGES[result.status])
        self._fill(self.steps_tree, [
            (cumulative, self._place(destination), self._place(source), block, number)
            for number, (block, source, destination, cumulative) in enumerate(self.steps, start=1)])
        self.step = 0
        self._go_to(0)

        # תהליך החיפוש
        if algorithm_name == "A*":
            self._show_astar_trace()
        else:
            self._show_ida_trace()

    def _show_astar_trace(self):
        self.ida_frame.pack_forget()
        self.astar_frame.pack(fill=tk.BOTH, expand=True)
        trace = self.astar_trace = self.result.trace
        self._fill(self.pops_tree, [
            (self.POP_TEXT[record["kind"]], self._action_text(record["parent"], record["state"]),
             record["open_size"], record["f"], record["h"], record["g"],
             format_state(record["state"]), record["order"])
            for record in trace])
        self._fill(self.children_tree, [])
        note = f"מוצגות {len(trace):,} שליפות"
        if len(trace) >= self.TRACE_LIMIT:
            note += f" (היומן שומר רק את {self.TRACE_LIMIT:,} הראשונות)"
        self.search_note_var.set(note)
        if trace:
            self.pops_tree.selection_set("0")

    def _on_pop_selected(self, event=None):
        selection = self.pops_tree.selection()
        if not selection or int(selection[0]) >= len(self.astar_trace):
            return
        record = self.astar_trace[int(selection[0])]
        self.children_title_var.set(f"היורשים של המצב שנשלף בשליפה {record['order']}")
        self._fill(self.children_tree, [
            (self.CHILD_TEXT[outcome], self._action_text(record["state"], child),
             g + h, h, g, format_state(child))
            for child, g, h, outcome in record["children"]])

    def _show_ida_trace(self):
        self.astar_frame.pack_forget()
        self.ida_frame.pack(fill=tk.BOTH, expand=True)
        trace = self.ida_trace = self.result.trace
        self._fill(self.iterations_tree, [
            ("-" if iteration["next_threshold"] is None else iteration["next_threshold"],
             f"{iteration['prunes']:,}", f"{iteration['expansions']:,}",
             iteration["threshold"], iteration["number"])
            for iteration in trace])
        self.search_note_var.set(
            f"מספר האיטרציות: {len(trace)}. לכל איטרציה נשמרים עד {self.TRACE_LIMIT:,} מצבים "
            f"שפותחו ועד {IDAStar.PRUNE_EXAMPLES} דוגמאות לגיזום")
        if trace:
            self.iterations_tree.selection_set(str(len(trace) - 1))

    def _on_iteration_selected(self, event=None):
        selection = self.iterations_tree.selection()
        if not selection or int(selection[0]) >= len(self.ida_trace):
            return
        iteration = self.ida_trace[int(selection[0])]
        for tree, items in ((self.expanded_tree, iteration["expanded"]),
                            (self.pruned_tree, iteration["pruned"])):
            self._fill(tree, [
                (self._action_text(parent, state), f, h, g, format_state(state))
                for state, parent, g, h, f in items])

    # ----- צעידה במצבי הפתרון -----
    def _go_to(self, step):
        if not self.path:
            self.step_var.set("")
            self._draw_state()
            return
        self.step = max(0, min(step, len(self.path) - 1))
        if self.step == 0:
            self.step_var.set("המצב ההתחלתי")
            self.steps_tree.selection_remove(self.steps_tree.selection())
        else:
            block, source, destination, cumulative = self.steps[self.step - 1]
            self.step_var.set(f"צעד {self.step} מתוך {len(self.steps)}:   "
                              f"{block}: {self._place(source)} -> {self._place(destination)}")
            iid = str(self.step - 1)
            if self.steps_tree.selection() != (iid,):
                self.steps_tree.selection_set(iid)
            self.steps_tree.see(iid)
        self._draw_state()

    def _on_step_selected(self, event=None):
        selection = self.steps_tree.selection()
        if selection and int(selection[0]) + 1 != self.step:
            self._go_to(int(selection[0]) + 1)

    def _draw_state(self):
        """ציור הערימות של הצעד הנוכחי. הקובייה שהוזזה בצעד הזה מודגשת."""
        canvas = self.canvas
        canvas.delete("all")
        if not self.path:
            return
        state = self.path[self.step]
        moved = self.steps[self.step - 1][0] if self.step > 0 else None
        width, height = canvas.winfo_width(), canvas.winfo_height()
        gap = 14
        tallest = max(len(stack) for stack in state)
        size = max(14, min(60, (width - 40) / len(state) - gap, (height - 50) / tallest))
        total = len(state) * size + (len(state) - 1) * gap
        left, base = (width - total) / 2, height - 25
        canvas.create_line(15, base, width - 15, base, width=3, fill="#44546a")
        for index, stack in enumerate(state):
            x = left + index * (size + gap)
            for level, block in enumerate(stack):
                bottom = base - level * size
                canvas.create_rectangle(
                    x, bottom - size, x + size, bottom, width=2, outline="#44546a",
                    fill="#f6b26b" if block == moved else "#cfe2f3")
                canvas.create_text(x + size / 2, bottom - size / 2, text=str(block),
                                   font=("Segoe UI", max(8, int(size / 3)), "bold"))

    def _on_close(self):
        self.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    BlocksWorldApp(root)
    root.mainloop()
