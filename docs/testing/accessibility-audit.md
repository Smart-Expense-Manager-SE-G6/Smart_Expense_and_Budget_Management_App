# Accessibility and responsive audit (S3-14, issue #76)

Covers **NFR7** (responsive on mobile, tablet and desktop) and **NFR8** (WCAG basics: labels, contrast,
keyboard). Run on 18 Nov 2026 against the dev stack (`docker compose up`) built from this branch.

## Method

[`tests/accessibility/a11y_audit.py`](../../tests/accessibility/a11y_audit.py) (Playwright + axe-core 4.14.1, WCAG 2.0/2.1 A and AA rules
plus best practices):

- every page (sign-in, register, dashboard, expenses, CSV import, recurring, budgets, categories, reports,
  alerts, profile, monitoring), the Add-expense and New-budget dialogs, and the mobile menu;
- at three widths: **360 px** (small phone), **768 px** (tablet), **1280 px** (desktop);
- checks for horizontal overflow (page wider than the screen) at each width;
- a keyboard-only pass: tab order, signing in with Enter, visible focus, dialog focus and Escape, skip link.

## Findings and fixes

| Finding (first run) | Where | Fix |
|:--|:--|:--|
| Text colour contrast below 4.5:1 | muted text, success, danger and primary badges, active nav item, report range pills | Darkened the light-theme tokens: `--muted` `#777d98`→`#62687f`, `--success` `#059669`→`#047857`, `--danger` `#e11d48`→`#be123c`, `--primary` `#5a5eed`→`#4f52e0`; pills use the theme tokens |
| `aria-label` on an SVG `<rect>` without a role | trend chart points | `role="img"` on each point; screen-reader list of the chart values (Shreya) |
| Unread dot announced without a role | alerts | `role="img"` + `aria-label="Unread"` (Shreya) |
| Visible text not part of the accessible name | Reports export buttons | Labels now "Export PDF report" / "Export Excel report" |
| Scrollable tables not reachable by keyboard | Reports tables | `tabIndex=0`, `role="region"` and a label on each table wrapper |
| Page wider than the screen (382 px at 360 px) | Alerts | Header actions wrap and stretch below 360 px (Shreya) |
| No skip link | every signed-in page | "Skip to content" link to `<main id="main-content">` (Shreya) |

## Result after the fixes

| Check | 360 px | 768 px | 1280 px |
|:--|:--|:--|:--|
| axe violations (all pages and dialogs) | 0 | 0 | 0 |
| Horizontal overflow | none | none | none |

| Keyboard check | Result |
|:--|:--|
| Tab order on sign-in reaches email, password and the button | Pass |
| Sign in with keyboard only (Enter submits) | Pass |
| Focused control has a visible focus style | Pass |
| Add-expense dialog opens with Enter, focus moves into it, Escape closes it | Pass |
| Skip-to-content link present | Pass |

No JavaScript errors were logged during the run.

## How to re-run

```bash
docker compose up -d --build
docker compose exec -e DJANGO_SUPERUSER_PASSWORD='Tr1cky-Passw0rd!' backend \
  python manage.py createsuperuser --noinput --email a11y.admin@example.com
pip install playwright && npm pack axe-core@4.14.1   # extract package/axe.min.js
python tests/accessibility/a11y_audit.py <output folder> <path to axe.min.js>
```

The script uses Microsoft Edge (`channel="msedge"`); change it to plain Chromium on Linux. Automated
checks find about half of WCAG issues, so the keyboard pass above is part of the audit, not optional.
