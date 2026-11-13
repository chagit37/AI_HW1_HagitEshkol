"""
דוחות הניסוי ההשוואתי: קובץ HTML מעוצב (נפתח בכל דפדפן) וקובץ Markdown.

שני הדוחות מציגים את אותם נתונים, כך שאפשר לקרוא את התוצאות בלי להריץ את התוכנית:
  1. תנאי הניסוי
  2. רשימת זוגות המצבים שנבחרו (מצב התחלתי, מצב יעד, עלות הפתרון האופטימלי)
  3. טבלת הביצועים של כל שיטה: ממוצעים, סטיות תקן, הצלחות והגעה למגבלה
  4. ממוצעים לפי מספר הקוביות
  5. פירוט מספר הפיתוחים והזמן בכל זוג ובכל שיטה
"""

import datetime
import html
import statistics

from search_constants import EXPANSION_LIMIT, TIMEOUT

LIMIT_NAMES = {TIMEOUT: "מגבלת זמן", EXPANSION_LIMIT: "מגבלת פיתוחים"}


# ---------------------------------------------------------------------------
# הכנת הנתונים - משותפת לשני הדוחות
# ---------------------------------------------------------------------------
def _methods(runner):
    return [f"{a} {h}" for a, h in runner.METHODS]


def _pair_rows(runner):
    """שורה לכל זוג: (מספר, קוביות, מצב התחלתי, מצב יעד, עלות אופטימלית או None)."""
    rows = []
    for index, problem in enumerate(runner.pairs):
        costs = {runner.results[(index, a, h)].cost for a, h in runner.METHODS
                 if (index, a, h) in runner.results and runner.results[(index, a, h)].solved}
        cost = min(costs) if costs else None
        blocks = sum(len(stack) for stack in problem.initial_state)
        rows.append((index + 1, blocks, problem.initial_state, problem.goal_state, cost))
    return rows


def _by_size(runner):
    """ממוצעים לפי מספר הקוביות: {קוביות: [(שיטה, פיתוחים ממוצע, זמן ממוצע, הצלחות, ריצות)]}."""
    sizes = {}
    for index, problem in enumerate(runner.pairs):
        sizes.setdefault(sum(len(stack) for stack in problem.initial_state), []).append(index)
    table = {}
    for size in sorted(sizes):
        rows = []
        for algorithm, heuristic in runner.METHODS:
            results = [runner.results[(i, algorithm, heuristic)] for i in sizes[size]
                       if (i, algorithm, heuristic) in runner.results]
            if not results:
                rows.append((f"{algorithm} {heuristic}", None, None, 0, 0))
                continue
            rows.append((f"{algorithm} {heuristic}",
                         statistics.mean(r.expansions_count for r in results),
                         statistics.mean(r.elapsed_time for r in results),
                         sum(r.solved for r in results), len(results)))
        table[size] = (len(sizes[size]), rows)
    return table


def _limits_text(runner):
    time_limit = "ללא" if runner.time_limit is None else f"{runner.time_limit:g} שניות"
    expansion_limit = "ללא" if runner.expansion_limit is None else f"{runner.expansion_limit:,} פיתוחים"
    return time_limit, expansion_limit


def _fmt_time(value):
    if value is None:
        return "-"
    if value >= 1:
        return f"{value:.2f}"
    if value >= 0.01:
        return f"{value:.3f}"
    return f"{value:.5f}"


def _fmt_count(value):
    if value is None:
        return "-"
    return f"{value:,.0f}" if float(value).is_integer() or value >= 100 else f"{value:,.1f}"


def _best_index(values, lower_is_better=True):
    """המיקום של הערך הטוב ביותר בשורה (או None כשאין ערכים)."""
    present = [(v, i) for i, v in enumerate(values) if v is not None]
    if not present:
        return set()
    best = min(present)[0] if lower_is_better else max(present)[0]
    return {i for v, i in present if v == best}


def _run_cell(result):
    """(טקסט פיתוחים, טקסט זמן, סטטוס מקוצר) לריצה אחת."""
    if result is None:
        return "-", "-", "לא הורץ"
    if result.solved:
        return f"{result.expansions_count:,}", _fmt_time(result.elapsed_time), ""
    return (f"{result.expansions_count:,}", _fmt_time(result.elapsed_time),
            LIMIT_NAMES.get(result.status, "לא נפתר"))


# ---------------------------------------------------------------------------
# דוח HTML
# ---------------------------------------------------------------------------
CSS = """
:root { --bg:#f7f7f5; --card:#ffffff; --ink:#1f2328; --muted:#5f6670; --line:#d9dce1;
        --head:#eef1f5; --best:#dff3e4; --best-ink:#14632e; --warn:#fde8e8; --warn-ink:#9b1c1c;
        --block:#4c7bd9; --block-ink:#ffffff; --table:#8a6d4b; --stripe:#fafbfc; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#16181b; --card:#1f2226; --ink:#e7e9ec; --muted:#a2a8b1; --line:#353a41;
          --head:#2a2e34; --best:#1d3b27; --best-ink:#8fe0a8; --warn:#4a2020; --warn-ink:#ffb4b4;
          --block:#5b8ae6; --table:#a0835f; --stripe:#23262b; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font-family:"Segoe UI", Arial, sans-serif; line-height:1.55; }
main { max-width:1150px; margin:0 auto; padding:24px 16px 48px; }
h1 { font-size:1.7rem; margin:0 0 4px; }
h2 { font-size:1.25rem; margin:0 0 10px; }
.sub { color:var(--muted); margin:0 0 20px; }
section { background:var(--card); border:1px solid var(--line); border-radius:10px;
          padding:18px 18px 14px; margin:0 0 18px; }
.note { color:var(--muted); font-size:.92rem; margin:8px 0 0; }
.facts { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:10px; }
.fact { background:var(--head); border-radius:8px; padding:10px 12px; }
.fact b { display:block; font-size:1.15rem; }
.fact span { color:var(--muted); font-size:.88rem; }
.scroll { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:.93rem; }
th, td { border:1px solid var(--line); padding:6px 9px; text-align:center; vertical-align:middle; }
th { background:var(--head); font-weight:600; }
tbody tr:nth-child(even) td { background:var(--stripe); }
td.name { text-align:right; font-weight:600; white-space:nowrap; }
td.best { background:var(--best) !important; color:var(--best-ink); font-weight:700; }
td.limit { background:var(--warn) !important; color:var(--warn-ink); }
td small { display:block; color:var(--muted); font-size:.8rem; }
td.limit small { color:var(--warn-ink); }
code { font-family:Consolas, monospace; direction:ltr; unicode-bidi:isolate; }
.state { display:flex; gap:5px; align-items:flex-end; justify-content:center;
         border-bottom:3px solid var(--table); padding:0 4px; min-height:24px; direction:rtl; }
.stack { display:flex; flex-direction:column-reverse; gap:2px; }
.block { width:22px; height:20px; border-radius:3px; background:var(--block);
         color:var(--block-ink); font-size:.8rem; font-weight:700; line-height:20px; }
.text-state { color:var(--muted); font-size:.82rem; margin-top:3px; }
.legend { display:flex; gap:16px; flex-wrap:wrap; font-size:.88rem; color:var(--muted); margin-top:8px; }
.legend i { display:inline-block; width:14px; height:14px; border-radius:3px; vertical-align:-2px;
            margin-left:5px; border:1px solid var(--line); }
"""


def _e(value):
    return html.escape(str(value))


def _state_html(state):
    """ציור המצב: כל ערימה היא עמודה של קוביות שעומדת על השולחן, והטקסט מתחת."""
    stacks = "".join(
        '<div class="stack">' + "".join(f'<div class="block">{_e(b)}</div>' for b in stack) + "</div>"
        for stack in state)
    text = " | ".join(", ".join(str(b) for b in stack) for stack in state)
    return f'<div class="state">{stacks}</div><div class="text-state">{_e(text)}</div>'


def save_html_report(runner, path):
    methods = _methods(runner)
    time_limit, expansion_limit = _limits_text(runner)
    total_runs = len(runner.pairs) * len(methods)
    done_runs = len(runner.results)
    solved_runs = sum(r.solved for r in runner.results.values())
    limited_runs = sum(r.status in LIMIT_NAMES for r in runner.results.values())
    agree = runner.costs_agree()
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    parts = [f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>תוצאות הניסוי ההשוואתי</title>
<style>{CSS}</style>
</head>
<body><main>
<h1>תוצאות הניסוי ההשוואתי - A* ו-IDA* בעולם הקוביות</h1>
<p class="sub">שש שיטות (שני אלגוריתמים כפול שלוש יוריסטיקות) על {len(runner.pairs)} זוגות מצבים אקראיים. נוצר בתאריך {now}.</p>

<section>
<h2>תנאי הניסוי ותמונה כללית</h2>
<div class="facts">
  <div class="fact"><b>{len(runner.pairs)}</b><span>זוגות מצבים</span></div>
  <div class="fact"><b>{done_runs} / {total_runs}</b><span>ריצות שבוצעו</span></div>
  <div class="fact"><b>{solved_runs}</b><span>ריצות שמצאו פתרון</span></div>
  <div class="fact"><b>{limited_runs}</b><span>ריצות שנעצרו במגבלה</span></div>
  <div class="fact"><b>{_e(time_limit)}</b><span>מגבלת זמן לריצה</span></div>
  <div class="fact"><b>{_e(expansion_limit)}</b><span>מגבלת פיתוחים לריצה</span></div>
  <div class="fact"><b>{_e("-" if runner.seed is None else runner.seed)}</b><span>גרעין אקראי (seed)</span></div>
  <div class="fact"><b>{"כן" if agree else "לא"}</b><span>כל השיטות שפתרו זוג מצאו אותה עלות</span></div>
</div>
<p class="note">אותו גרעין אקראי מייצר תמיד את אותם זוגות, כך שאפשר לשחזר את הניסוי.
זמני הריצה תלויים במחשב; מספרי הפיתוחים אינם תלויים בו.</p>
</section>
"""]

    # --- 1. הזוגות ---
    parts.append("""<section>
<h2>1. זוגות המצבים שנבחרו</h2>
<p class="note" style="margin-top:0">כל ערימה מצוירת מלמטה (השולחן) למעלה. בטקסט: ערימות מופרדות ב-| וכל ערימה כתובה מהקובייה התחתונה לעליונה.</p>
<div class="scroll"><table>
<thead><tr><th>זוג</th><th>קוביות</th><th>מצב התחלתי</th><th>מצב יעד</th><th>עלות הפתרון האופטימלי</th></tr></thead>
<tbody>""")
    for number, blocks, initial, goal, cost in _pair_rows(runner):
        parts.append(f"<tr><td>{number}</td><td>{blocks}</td><td>{_state_html(initial)}</td>"
                     f"<td>{_state_html(goal)}</td><td><b>{'-' if cost is None else cost}</b></td></tr>")
    parts.append("</tbody></table></div></section>")

    # --- 2. טבלת הביצועים ---
    performance = runner.performance_table()
    columns = [  # (כותרת, מיקום בשורה, פונקציית תצוגה, האם נמוך יותר עדיף)
        ("זמן ממוצע (שניות)", 1, _fmt_time, True),
        ("סטיית תקן זמן", 2, _fmt_time, None),
        ("פיתוחים - ממוצע", 3, _fmt_count, True),
        ("פיתוחים - סטיית תקן", 4, _fmt_count, None),
        ("הצלחות", 5, str, False),
        ("הגעה למגבלה", 6, str, True),
    ]
    parts.append("""<section>
<h2>2. השוואת ביצועי השיטות - ממוצעים וסטיות תקן</h2>
<div class="scroll"><table>
<thead><tr><th>שיטה</th>""" + "".join(f"<th>{_e(title)}</th>" for title, *_ in columns) +
                 "</tr></thead><tbody>")
    best = {pos: _best_index([row[pos] for row in performance], lower)
            for _, pos, _, lower in columns if lower is not None}
    for row_index, row in enumerate(performance):
        cells = [f'<td class="name">{_e(row[0])}</td>']
        for _, pos, fmt, _ in columns:
            value = row[pos]
            cls = ' class="best"' if row_index in best.get(pos, ()) else ""
            if pos == 6 and value:
                cls = ' class="limit"'
            cells.append(f"<td{cls}>{'-' if value is None else _e(fmt(value))}</td>")
        parts.append("<tr>" + "".join(cells) + "</tr>")
    parts.append(f"""</tbody></table></div>
<div class="legend"><span><i style="background:var(--best)"></i>הערך הטוב ביותר בעמודה</span>
<span><i style="background:var(--warn)"></i>היו ריצות שנעצרו במגבלה</span></div>
<p class="note">הממוצעים וסטיות התקן מחושבים על כל {len(runner.pairs)} הריצות של השיטה, כולל ריצות שנעצרו במגבלה
(בהן נספרים הזמן והפיתוחים עד העצירה, ולכן אצל שיטות שנעצרו הממוצע האמיתי גבוה עוד יותר).
סטיית התקן היא של מדגם (חלוקה ב-n-1).</p>
</section>""")

    # --- 3. לפי מספר קוביות ---
    by_size = _by_size(runner)
    parts.append("""<section>
<h2>3. ממוצעים לפי מספר הקוביות</h2>
<p class="note" style="margin-top:0">בכל תא: מספר הפיתוחים הממוצע, ומתחתיו הזמן הממוצע בשניות. מתחת לזמן - כמה ריצות נפתרו.</p>
<div class="scroll"><table>
<thead><tr><th>קוביות</th><th>זוגות</th>""" + "".join(f"<th>{_e(m)}</th>" for m in methods) +
                 "</tr></thead><tbody>")
    for size, (pair_count, rows) in by_size.items():
        best_cells = _best_index([r[1] for r in rows])
        cells = [f"<td><b>{size}</b></td><td>{pair_count}</td>"]
        for i, (_, expansions, elapsed, solved, runs) in enumerate(rows):
            cls = []
            if i in best_cells:
                cls.append("best")
            if runs and solved < runs:
                cls = ["limit"]
            attr = f' class="{" ".join(cls)}"' if cls else ""
            cells.append(f"<td{attr}>{_e(_fmt_count(expansions))}<small>{_e(_fmt_time(elapsed))} שנ'</small>"
                         f"<small>נפתרו {solved}/{runs}</small></td>")
        parts.append("<tr>" + "".join(cells) + "</tr>")
    parts.append("</tbody></table></div></section>")

    # --- 4. פירוט ---
    parts.append("""<section>
<h2>4. פירוט כל הריצות</h2>
<p class="note" style="margin-top:0">בכל תא: מספר הפיתוחים, ומתחתיו זמן הריצה בשניות. תא אדום - הריצה נעצרה במגבלה ולא מצאה פתרון.</p>
<div class="scroll"><table>
<thead><tr><th>זוג</th><th>קוביות</th><th>עלות</th>""" + "".join(f"<th>{_e(m)}</th>" for m in methods) +
                 "</tr></thead><tbody>")
    for (number, blocks, _, _, cost), index in zip(_pair_rows(runner), range(len(runner.pairs))):
        results = [runner.results.get((index, a, h)) for a, h in runner.METHODS]
        best_cells = _best_index([r.expansions_count if r is not None and r.solved else None
                                  for r in results])
        cells = [f"<td><b>{number}</b></td><td>{blocks}</td><td>{'-' if cost is None else cost}</td>"]
        for i, result in enumerate(results):
            expansions, elapsed, note = _run_cell(result)
            if note:
                cells.append(f'<td class="limit">{_e(expansions)}<small>{_e(elapsed)} שנ\'</small>'
                             f"<small>{_e(note)}</small></td>")
            else:
                cls = ' class="best"' if i in best_cells else ""
                cells.append(f"<td{cls}>{_e(expansions)}<small>{_e(elapsed)} שנ'</small></td>")
        parts.append("<tr>" + "".join(cells) + "</tr>")
    parts.append("""</tbody></table></div>
<div class="legend"><span><i style="background:var(--best)"></i>הכי מעט פיתוחים בזוג</span>
<span><i style="background:var(--warn)"></i>נעצרה במגבלה</span></div>
</section>
</main></body></html>
""")
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(parts))


# ---------------------------------------------------------------------------
# דוח Markdown (נקרא יפה ב-GitHub וב-VS Code עם תצוגה מקדימה)
# ---------------------------------------------------------------------------
def _md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(" --- " for _ in headers) + "|"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def _md(text):
    """בורחים מהכוכבית של A*, כדי שלא תתפרש כהדגשה ב-Markdown."""
    return str(text).replace("*", "\*")


def _md_state(state):
    return "`" + " \\| ".join(", ".join(str(b) for b in stack) for stack in state) + "`"


def save_markdown_report(runner, path):
    methods = _methods(runner)
    time_limit, expansion_limit = _limits_text(runner)
    lines = [
        "# תוצאות הניסוי ההשוואתי - A\* ו-IDA\* בעולם הקוביות",
        "",
        f"שש שיטות (שני אלגוריתמים כפול שלוש יוריסטיקות) על {len(runner.pairs)} זוגות מצבים אקראיים.",
        "",
        "## תנאי הניסוי",
        "",
        f"- גרעין אקראי (seed): {'-' if runner.seed is None else runner.seed}",
        f"- מספר זוגות: {len(runner.pairs)}",
        f"- מגבלת זמן לריצה: {time_limit}",
        f"- מגבלת פיתוחים לריצה: {expansion_limit}",
        f"- ריצות שבוצעו: {len(runner.results)} מתוך {len(runner.pairs) * len(methods)}",
        f"- בכל זוג, כל השיטות שמצאו פתרון מצאו אותה עלות: {'כן' if runner.costs_agree() else 'לא'}",
        "",
        "## 1. זוגות המצבים שנבחרו",
        "",
        "ערימות מופרדות ב-`|`, וכל ערימה כתובה מהקובייה התחתונה לעליונה.",
        "",
        _md_table(["זוג", "קוביות", "מצב התחלתי", "מצב יעד", "עלות אופטימלית"],
                  [(n, b, _md_state(i), _md_state(g), "-" if c is None else c)
                   for n, b, i, g, c in _pair_rows(runner)]),
        "",
        "## 2. השוואת ביצועי השיטות - ממוצעים וסטיות תקן",
        "",
    ]
    perf_rows = []
    for method, t_mean, t_dev, e_mean, e_dev, solved, limited in runner.performance_table():
        perf_rows.append((f"**{_md(method)}**", _fmt_time(t_mean), _fmt_time(t_dev),
                          _fmt_count(e_mean), _fmt_count(e_dev), solved, limited))
    lines += [
        _md_table(["שיטה", "זמן ממוצע (שנ')", "סטיית תקן זמן", "פיתוחים - ממוצע",
                   "פיתוחים - סטיית תקן", "הצלחות", "הגעה למגבלה"], perf_rows),
        "",
        "הממוצעים כוללים גם ריצות שנעצרו במגבלה (נספרים הזמן והפיתוחים עד העצירה).",
        "",
        "## 3. ממוצעים לפי מספר הקוביות",
        "",
        "בכל תא: פיתוחים ממוצע / זמן ממוצע בשניות (ובסוגריים - כמה ריצות נפתרו).",
        "",
    ]
    size_rows = []
    for size, (pair_count, rows) in _by_size(runner).items():
        size_rows.append((size, pair_count, *[
            f"{_fmt_count(e)} / {_fmt_time(t)} ({s}/{r})" for _, e, t, s, r in rows]))
    lines += [_md_table(["קוביות", "זוגות", *map(_md, methods)], size_rows), "",
              "## 4. פירוט כל הריצות", "",
              "בכל תא: מספר פיתוחים / זמן בשניות. ריצה שנעצרה במגבלה מסומנת ב-⛔.", ""]
    detail_rows = []
    for (number, blocks, _, _, cost), index in zip(_pair_rows(runner), range(len(runner.pairs))):
        cells = []
        for a, h in runner.METHODS:
            expansions, elapsed, note = _run_cell(runner.results.get((index, a, h)))
            cells.append(f"⛔ {expansions} / {elapsed} ({note})" if note else f"{expansions} / {elapsed}")
        detail_rows.append((number, blocks, "-" if cost is None else cost, *cells))
    lines += [_md_table(["זוג", "קוביות", "עלות", *map(_md, methods)], detail_rows), ""]
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
