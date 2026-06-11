"""Browser harness wrapper — thin abstraction over browser-harness CLI."""
import ast
import subprocess
import json
import time
import os
from typing import Optional


def _parse(out: str):
    """Parse browser-harness output: JSON → Python literal → raw string."""
    if not out or not out.strip():
        return {}
    try:
        return json.loads(out)
    except (json.JSONDecodeError, ValueError):
        try:
            return ast.literal_eval(out)
        except (ValueError, SyntaxError):
            return {"raw": out}


class Browser:
    """Controls Chrome via browser-harness (CDP)."""

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        self.cdp_url = cdp_url

    def _run(self, code: str) -> str:
        """Pipe Python code to browser-harness, return stdout."""
        if not code.strip().endswith("\n"):
            code += "\n"
        proc = subprocess.run(
            ["browser-harness"],
            input=code,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={**os.environ, "BU_CDP_URL": self.cdp_url},
        )
        if proc.returncode != 0:
            raise RuntimeError(f"browser-harness error: {proc.stderr.strip()}")
        return proc.stdout.strip() if proc.stdout else ""

    def navigate(self, url: str) -> dict:
        """Navigate to URL and return page info."""
        code = f"""
goto_url("{url}")
wait_for_load()
time.sleep(2)
print(page_info())
"""
        out = self._run(code)
        return _parse(out)

    def click_text(self, text: str, tag: str = "*") -> dict:
        """Click element by visible text and return page info."""
        code = f"""
import time
el = find_element_by_text("{text}", '{tag}')
if el:
    click_element(el)
    time.sleep(1)
print(page_info())
"""
        out = self._run(code)
        return _parse(out)

    def click_selector(self, selector: str) -> dict:
        """Click a CSS selector and return page info."""
        code = f"""
import time
el = js(f"document.querySelector('{selector}')")
if el:
    click_element(el)
    time.sleep(1)
print(page_info())
"""
        out = self._run(code)
        return _parse(out)

    def get_elements(self, selector: str) -> list:
        """Return all matching elements' properties."""
        code = f"""
import json
sel = "{selector}"
js_code = '''
    Array.from(document.querySelectorAll(''' + json.dumps(sel) + ''')).map(function(el) {{
        return {{
            tag: el.tagName,
            text: (el.innerText || '').substring(0, 200),
            id: el.id || '',
            class: el.className || '',
            rect: el.getBoundingClientRect(),
            visible: el.offsetParent !== null
        }};
    }})
'''
els = js(js_code)
print(json.dumps(els))
"""
        out = self._run(code)
        parsed = _parse(out)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed] if parsed else []
        return []

    def get_text(self, selector: str) -> str:
        """Get text content of element."""
        code = f"""
txt = js(f"document.querySelector('{selector}')?.innerText || ''")
print(txt)
"""
        return self._run(code).strip()

    def screenshot(self, path: str) -> None:
        """Capture screenshot."""
        code = f'capture_screenshot("{path}")'
        self._run(code)

    def wait_for(self, selector: str, timeout_ms: int = 10000) -> bool:
        """Poll until selector appears or timeout."""
        code = f"""
import time
start = time.time()
while time.time() - start < {timeout_ms / 1000}:
    el = js(f"document.querySelector('{selector}')")
    if el:
        print("found")
        break
    time.sleep(0.5)
else:
    print("timeout")
"""
        return "found" in self._run(code)

    def page_info(self) -> dict:
        """Get current page info."""
        out = self._run("print(page_info())")
        return _parse(out)

    def evaluate(self, js_code: str) -> str:
        """Run arbitrary JS and return result."""
        code = f"print(js({json.dumps(js_code)}))"
        return self._run(code)

    def press_key(self, key: str) -> None:
        """Press a keyboard key (Escape, Enter, Tab, etc.)."""
        self._run(f'press_key("{key}")')

    def click_at(self, x: int, y: int) -> None:
        """Click at screen coordinates."""
        self._run(f"click_at_xy({x}, {y})")
