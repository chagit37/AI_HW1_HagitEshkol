"""
HW1 - חיפוש A* ו-IDA* על בעיית הקוביות (Blocks World). זה הקובץ שמריצים.

הרצה:
    python HW1_Hagit.py          - הממשק הגרפי
    python HW1_Hagit.py --demo   - הרצה של כל השיטות על דוגמת המטלה, עם פלט לטרמינל
    python HW1_Hagit.py --experiment - ניסוי 12 הזוגות, והתוצאות נשמרות בתיקייה outputs:
                                       experiment_report.html, experiment_report.md, experiment_results.csv

מבנה הקבצים:
    blocks_world.py      - בעיית הקוביות: BlocksWorld, קריאה והדפסה של מצבים
    heuristics.py        - שלוש היוריסטיקות: h_zero, h1, h2
    search_constants.py  - קבועי הסטטוס וההודעות למשתמש
    node.py              - המחלקה Node
    search_result.py     - המחלקה SearchResult
    search_algorithm.py  - מחלקת הבסיס SearchAlgorithm
    astar.py             - האלגוריתם AStar
    ida_star.py          - האלגוריתם IDAStar
    experiment.py        - ExperimentRunner: ניסוי 12 הזוגות והטבלאות שלו
    report.py            - דוחות הניסוי: HTML (לדפדפן) ו-Markdown
    gui.py               - הממשק הגרפי BlocksWorldApp
"""

import os
import signal
import sys

from astar import AStar
from blocks_world import EXAMPLE_GOAL, EXAMPLE_INITIAL, BlocksWorld, format_state, parse_state
from experiment import ExperimentRunner
from gui import main
from heuristics import h1, h2, h_zero
from ida_star import IDAStar
from report import save_html_report, save_markdown_report
from search_constants import STATUS_MESSAGES


# ---------------------------------------------------------------------------
# הרצה לטרמינל (python HW1_Hagit.py --demo)
# ---------------------------------------------------------------------------
def run_search(solver, heuristic):
    """מריצה חיפוש ומאפשרת למשתמש לעצור ריצה מתמשכת בלחיצה על Ctrl+C.

    הלחיצה רק מדליקה את cancel_event; החיפוש רואה אותו בבדיקת תנאי העצירה הבאה
    ומחזיר תוצאה מסודרת בסטטוס CANCELLED, עם הנתונים שנאספו עד אותו רגע.
    """
    previous_handler = signal.signal(signal.SIGINT,
                                     lambda signum, frame: solver.cancel_event.set())
    try:
        return solver.search(heuristic)
    finally:
        signal.signal(signal.SIGINT, previous_handler)


def print_solution(result, problem):
    """מסלול הפתרון: עלות כוללת, ולכל פעולה - הקובייה, המקור, היעד והעלות המצטברת."""
    if not result.solved:
        print(STATUS_MESSAGES[result.status])
        return
    print(f"Total cost: {result.cost}")
    print(f"{'step':>4}  {'block':<6}{'from':<8}{'to':<8}{'cumulative cost':<17}state after the move")
    steps = problem.get_solution_steps(result.path)
    for number, (block, source, destination, cumulative_cost) in enumerate(steps, start=1):
        print(f"{number:>4}  {block!s:<6}{source!s:<8}{destination!s:<8}{cumulative_cost!s:<17}"
              f"{format_state(result.path[number])}")


def print_result(result):
    cost = result.cost if result.solved else "-"
    line = (f"{result.algorithm:8} {result.heuristic:7} status={result.status:16} "
            f"cost={cost!s:3} time={result.elapsed_time:.3f}s generated={result.generated:<8} "
            f"expanded={result.expansions_count:<8}")
    if result.iterations is None:
        line += f" max_queue={result.max_open_size:<7} cost_improvements={result.improvements}"
    else:
        line += f" iterations={result.iterations}"
    print(line)
    if not result.solved:
        print(f"   -> {STATUS_MESSAGES[result.status]}")


def run_demo():
    sys.stdout.reconfigure(encoding="utf-8")  # כדי שהעברית תודפס תקין
    problem = BlocksWorld(parse_state(EXAMPLE_INITIAL), parse_state(EXAMPLE_GOAL))

    print("initial:", format_state(problem.initial_state))
    print("goal:   ", format_state(problem.goal_state))
    print()

    # ערכי שלוש היוריסטיקות במצב ההתחלתי
    for heuristic in (h_zero, h1, h2):
        print(f"{heuristic.__name__}(initial) = {heuristic(problem.initial_state, problem)}")
    print()

    # כל ריצה אפשר לעצור באמצע עם Ctrl+C
    for algorithm in (AStar, IDAStar):
        for heuristic in (h_zero, h1, h2):
            solver = algorithm(problem, time_limit=30, expansion_limit=500_000)
            print_result(run_search(solver, heuristic))

    print()
    print("Solution path (AStar, h2):")
    print_solution(run_search(AStar(problem), h2), problem)


def run_experiment():
    """מריצה את ניסוי 12 הזוגות ושומרת את התוצאות בתיקייה outputs בשלושה קבצים:
    experiment_report.html (לפתיחה בדפדפן), experiment_report.md, experiment_results.csv (לאקסל).
    """
    sys.stdout.reconfigure(encoding="utf-8")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    seed = 1
    runner = ExperimentRunner(ExperimentRunner.generate_pairs(seed=seed),
                              time_limit=30, expansion_limit=500_000, seed=seed)
    signal.signal(signal.SIGINT, lambda signum, frame: runner.cancel_event.set())
    print(f"Running {len(runner.pairs)} pairs x {len(runner.METHODS)} methods (Ctrl+C to stop)...")
    runner.run()
    paths = {name: os.path.join(output_dir, name)
             for name in ("experiment_report.html", "experiment_report.md", "experiment_results.csv")}
    save_html_report(runner, paths["experiment_report.html"])
    save_markdown_report(runner, paths["experiment_report.md"])
    runner.save_csv(paths["experiment_results.csv"])
    for path in paths.values():
        print("saved:", path)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    elif "--experiment" in sys.argv:
        run_experiment()
    else:
        main()
