"""Browser harness wrapper — thin abstraction over browser-harness CLI."""
import subprocess
import json
import time
import sys
from typing import Optional


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
            timeout=30,
            env={**__import__("os").environ, "BU_CDP_URL": self.cdp_url},
        )
        if proc.returncode != 0:
            raise RuntimeError(f"browser-harness error: {proc.stderr.strip()}")
        return proc.stdout.strip()

    def navigate(self, url: str) -> dict:
        """Navigate to URL and return page info."""
        code = f"""
goto_url("{url}")
wait_for_load()
print(page_info())
"""
        out = self._run(code)
        return json.loads(out) if out else {}

    def click_text(self, text: str, tag: str = "*") -> dict:
        """Click element by visible text."""
        code = f"""
el = find_element_by_text("{text}", '{tag}')
if el:
    click_element(el)
    time.sleep(1)
print(page_info())
"""
        out = self._run(code)
        return json.loads(out) if out else {}

    def click_selector(self, selector: str) -> dict:
        """Click a CSS selector."""
        code = f"""
import time
el = js(f"document.querySelector('{selector}')")
if el:
    click_element(el)
    time.sleep(1)
print(page_info())
"""
        out = self._run(code)
        return json.loads(out) if out else {}

    def get_elements(self, selector: str) -> list:
        """Return all matching elements' properties."""
        code = f"""
els = js(f\"\"\"
    Array.from(document.querySelectorAll('{selector}')).map(el => ({{
        tag: el.tagName,
        text: el.innerText?.substring(0,200),
        id: el.id,
        class: el.className,
        rect: el.getBoundingClientRect(),
        visible: el.offsetParent !== null
    }}))
\"\"\")
print(json.dumps(els))
"""
        out = self._run(code)
        return json.loads(out) if out else []

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
        return json.loads(out) if out else {}

    def evaluate(self, js_code: str) -> str:
        """Run arbitrary JS and return result."""
        code = f"print(js({json.dumps(js_code)}))"
        return self._run(code)
