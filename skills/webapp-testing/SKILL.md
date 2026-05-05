---
name: webapp-testing
description: Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and reviewing browser logs.
---

# Web Application Testing

To test local web applications, write native Python Playwright scripts.

**Available helper scripts**:
- `scripts/with_server.py` — manages the server lifecycle (supports multiple servers)

**Always run scripts with `--help` first** to see usage. Do NOT read the source until you have tried running the script and discovered that a custom solution is absolutely necessary. These scripts can be very large and would otherwise pollute the context window. They are designed to be invoked directly as black-box scripts, not absorbed into context.

## Decision tree: choosing an approach

```
User task → Is it static HTML?
    ├─ Yes → Read HTML file directly to identify selectors
    │         ├─ Success → Write Playwright script using selectors
    │         └─ Fails/Incomplete → Treat as dynamic (below)
    │
    └─ No (dynamic webapp) → Is the server already running?
        ├─ No → Run: python scripts/with_server.py --help
        │        Then use the helper + write simplified Playwright script
        │
        └─ Yes → Reconnaissance-then-action:
            1. Navigate and wait for networkidle
            2. Take screenshot or inspect DOM
            3. Identify selectors from rendered state
            4. Execute actions with discovered selectors
```

## Example: using with_server.py

To launch a server, run `--help` first, then use the helper:

**Single server:**
```bash
python scripts/with_server.py --server "npm run dev" --port 5173 -- python your_automation.py
```

**Multiple servers (e.g., backend + frontend):**
```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

To create the automation script, include only Playwright logic (servers are managed automatically):
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) # Always launch chromium in headless mode
    page = browser.new_page()
    page.goto('http://localhost:5173') # Server already running and ready
    page.wait_for_load_state('networkidle') # CRITICAL: Wait for JS to execute
    # ... your automation logic
    browser.close()
```

## Reconnaissance-Then-Action pattern

1. **Inspect the rendered DOM**:
   ```python
   page.screenshot(path='/tmp/inspect.png', full_page=True)
   content = page.content()
   page.locator('button').all()
   ```

2. **Identify selectors** from inspection results

3. **Execute actions** using the discovered selectors

## Common pitfall

❌ **Do not** inspect the DOM before waiting for `networkidle` on dynamic apps
✅ **Do** wait with `page.wait_for_load_state('networkidle')` before inspection

## Best practices

- **Use bundled scripts as a black box** — To accomplish a task, consider whether one of the scripts in `scripts/` can help. These scripts reliably handle common complex workflows without polluting the context window. Use `--help` to see usage, then invoke directly.
- Use `sync_playwright()` for synchronous scripts
- Always close the browser when finished
- Use descriptive selectors: `text=`, `role=`, CSS selectors, or IDs
- Add appropriate waits: `page.wait_for_selector()` or `page.wait_for_timeout()`

## Reference files

- **examples/** — Examples showing common patterns:
  - `element_discovery.py` — Discovering buttons, links, and input fields on a page
  - `static_html_automation.py` — Using a file:// URL for local HTML
  - `console_logging.py` — Capturing console logs during automation
