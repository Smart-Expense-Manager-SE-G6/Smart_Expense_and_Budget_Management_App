"""
S3-14 / #76 accessibility audit (NFR7, NFR8): axe-core on every page and main dialog at 360, 768 and 1280 px,
plus a keyboard-only pass. Writes JSON results and prints a summary. Usage: a11y_audit.py <out_dir> <axe.min.js>
"""
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
AXE = Path(sys.argv[2]).read_text(encoding="utf-8")
BASE, PW, EMAIL = "http://localhost:5174", "Tr1cky-Passw0rd!", "a11y.admin@example.com"
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"]
PAGES = ["/", "/expenses", "/expenses/import", "/recurring", "/budgets", "/categories", "/reports", "/alerts",
         "/profile", "/monitoring"]
WIDTHS = [(360, 740), (768, 1024), (1280, 900)]
results, overflow, errors = [], [], []


def axe(pg, label, width):
    pg.add_script_tag(content=AXE)
    found = pg.evaluate("async (tags) => (await axe.run(document, {runOnly: {type: 'tag', values: tags}})).violations", TAGS)
    for v in found:
        results.append({"where": label, "width": width, "id": v["id"], "impact": v["impact"], "help": v["help"],
                        "nodes": len(v["nodes"]), "example": v["nodes"][0]["target"] if v["nodes"] else None,
                        "summary": (v["nodes"][0].get("failureSummary") or "")[:300] if v["nodes"] else ""})


def sign_in(ctx):
    pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/login"); pg.get_by_label("Email").fill(EMAIL); pg.get_by_label("Password").fill(PW)
    pg.get_by_role("button", name="Sign in").click(); pg.wait_for_url(BASE + "/", timeout=10000)
    return pg


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)

    # Some data so tables, cards and charts are not empty.
    pg = sign_in(b.new_context())
    tok = next(c["value"] for c in pg.context.cookies() if c["name"] == "csrftoken")
    h = {"X-CSRFToken": tok, "Origin": BASE}
    cats = pg.context.request.get(BASE + "/api/v1/categories/").json()
    cats = cats.get("results", cats) if isinstance(cats, dict) else cats
    food = next(c["id"] for c in cats if c["name"] == "Food")
    today = date.today()
    for i, amt in enumerate(("120.00", "860.00", "45.50")):
        pg.context.request.post(BASE + "/api/v1/expenses/", data={"amount": amt, "date": today.isoformat(), "category": food,
                                                                    "description": f"Audit {i}", "merchant": "Shop", "payment_method": "upi"}, headers=h)
    end = (today.replace(day=28) + __import__("datetime").timedelta(days=4)).replace(day=1) - __import__("datetime").timedelta(days=1)
    pg.context.request.post(BASE + "/api/v1/budgets/", data={"name": "Audit food", "category": food, "limit_amount": "1000.00", "period": "monthly",
                                                              "start_date": today.replace(day=1).isoformat(), "end_date": end.isoformat()}, headers=h)

    # Signed-out pages
    for w, ht in WIDTHS:
        c = b.new_context(viewport={"width": w, "height": ht}); q = c.new_page()
        for path in ("/login", "/register"):
            q.goto(BASE + path); q.wait_for_timeout(800); axe(q, path, w)
            sw = q.evaluate("document.documentElement.scrollWidth")
            if sw > w: overflow.append(f"{path} @{w}: {sw}px")
        c.close()

    # Signed-in pages and dialogs
    for w, ht in WIDTHS:
        c = b.new_context(viewport={"width": w, "height": ht}); q = sign_in(c)
        for path in PAGES:
            q.goto(BASE + path); q.wait_for_timeout(1500); axe(q, path, w)
            sw = q.evaluate("document.documentElement.scrollWidth")
            if sw > w: overflow.append(f"{path} @{w}: {sw}px")
        for path, button, label in (("/expenses", "Add expense", "dialog: add expense"),
                                    ("/budgets", "New budget", "dialog: new budget")):
            q.goto(BASE + path); q.wait_for_timeout(1200)
            q.get_by_role("button", name=button).first.click(); q.get_by_role("dialog").wait_for(timeout=5000)
            q.wait_for_timeout(400); axe(q, label, w)
            q.keyboard.press("Escape")
        if w < 900:
            q.goto(BASE + "/"); q.wait_for_timeout(800)
            q.get_by_label("Open menu").click(); q.wait_for_timeout(400); axe(q, "mobile menu open", w)
        c.close()

    # Keyboard-only pass
    kb = []
    c = b.new_context(viewport={"width": 1280, "height": 900}); q = c.new_page()
    q.goto(BASE + "/login"); q.wait_for_timeout(800)
    order = []
    for _ in range(6):
        q.keyboard.press("Tab")
        order.append(q.evaluate("(() => { const e = document.activeElement; return (e.getAttribute('aria-label') || e.labels?.[0]?.innerText || e.innerText || e.tagName).trim().slice(0, 30); })()"))
    outline = q.evaluate("(() => { const s = getComputedStyle(document.activeElement); return s.outlineStyle !== 'none' || s.boxShadow !== 'none'; })()")
    kb.append(("Tab order on sign-in reaches email, password and the button", order))
    q.goto(BASE + "/login"); q.get_by_label("Email").focus(); q.keyboard.type(EMAIL); q.keyboard.press("Tab"); q.keyboard.type(PW)
    q.keyboard.press("Enter"); q.wait_for_url(BASE + "/", timeout=10000)
    kb.append(("Sign in with keyboard only (Enter submits)", q.url == BASE + "/"))
    kb.append(("Focused control has a visible focus style", outline))
    q.goto(BASE + "/expenses"); q.wait_for_timeout(1200)
    q.get_by_role("button", name="Add expense").first.focus(); q.keyboard.press("Enter"); q.get_by_role("dialog").wait_for(timeout=5000)
    inside = q.evaluate("document.querySelector('dialog[open]')?.contains(document.activeElement)")
    q.keyboard.press("Escape"); q.wait_for_timeout(400)
    closed = q.evaluate("!document.querySelector('dialog[open]')")
    kb.append(("Add-expense dialog opens with Enter, focus moves into it, Escape closes it", bool(inside and closed)))
    q.goto(BASE + "/"); q.wait_for_timeout(800)
    skip = q.evaluate("[...document.querySelectorAll('a')].some(a => /skip/i.test(a.innerText))")
    kb.append(("Skip-to-content link present", skip))
    c.close()
    try:
        b.close()
    except Exception:
        pass

(OUT / "axe_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
(OUT / "keyboard_results.json").write_text(json.dumps(kb, indent=1, default=str), encoding="utf-8")
by_impact = Counter(r["impact"] for r in results)
print("axe violations by impact:", dict(by_impact) or "none")
groups = defaultdict(set)
for r in results:
    groups[(r["impact"], r["id"], r["help"])].add(f"{r['where']}@{r['width']}")
for (impact, rid, helptext), where in sorted(groups.items(), key=lambda x: ["critical", "serious", "moderate", "minor", None].index(x[0][0])):
    print(f"  [{impact}] {rid}: {helptext} | {len(where)} places, e.g. {sorted(where)[:4]}")
print("horizontal overflow:", overflow or "none")
for name, val in kb:
    print("keyboard:", name, "->", val)
print("JS errors:", errors[:3] or "none")
