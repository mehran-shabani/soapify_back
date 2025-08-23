"""
Test suite for api_check/server_check_server/src/api_tests.py

Framework note:
- Authored using Python's standard library 'unittest' for maximum compatibility.
- If the project uses pytest, these tests will still run unmodified.

Initial focus:
- Safe import (no network side-effects, no stdout on import)
- HTTP-call best practices via static analysis (timeouts on requests/httpx)
- Sanity validation for URL-like constants
- Public function hygiene (docstrings)

Once the PR <diff> context is available, we will extend/target tests around the changed lines.
"""

import ast
import io
import inspect
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse
import importlib.util

# Resolve module path relative to this test file (../api_tests.py from src/tests/)
MODULE_RELATIVE_PATH = (Path(__file__).resolve().parents[1] / "api_tests.py")


def load_module():
    """Dynamically load the module under test from its file path without requiring package imports."""
    if not MODULE_RELATIVE_PATH.exists():
        raise FileNotFoundError(f"Module file not found at {MODULE_RELATIVE_PATH}")
    spec = importlib.util.spec_from_file_location("api_tests", str(MODULE_RELATIVE_PATH))
    module = importlib.util.module_from_spec(spec)
    # Execute the module code in its own namespace
    assert spec and spec.loader, "Failed to prepare a loader for api_tests module"
    spec.loader.exec_module(module)
    return module


class TestApiTestsModuleImport(unittest.TestCase):
    def test_module_file_exists(self):
        self.assertTrue(MODULE_RELATIVE_PATH.is_file(), f"Expected module file missing: {MODULE_RELATIVE_PATH}")

    def test_import_no_network_and_no_stdout(self):
        # Prevent any accidental network activity during import
        fake_out = io.StringIO()
        with patch("socket.create_connection", side_effect=AssertionError("Network used during import")), \
             redirect_stdout(fake_out):
            mod = load_module()
        self.assertIsNotNone(mod)
        self.assertEqual(
            fake_out.getvalue(), "",
            "Module import printed to stdout; avoid side effects at import time."
        )

    def test_public_functions_have_docstrings(self):
        mod = load_module()
        # Consider only functions actually defined in api_tests (not re-exported ones)
        funcs = [
            (name, obj)
            for name, obj in inspect.getmembers(mod, inspect.isfunction)
            if not name.startswith("_") and getattr(obj, "__module__", "").endswith("api_tests")
        ]
        if not funcs:
            self.skipTest("No public functions detected in api_tests.py")
        for name, func in funcs:
            with self.subTest(function=name):
                self.assertTrue(
                    func.__doc__ and func.__doc__.strip(),
                    f"Function '{name}' is missing a docstring"
                )


class TestStaticHttpCalls(unittest.TestCase):
    def _read_source(self) -> str:
        return MODULE_RELATIVE_PATH.read_text(encoding="utf-8")

    def test_requests_and_httpx_calls_have_timeouts(self):
        """
        Static AST check:
        Enforce that calls like requests.get/post/... or httpx.get/post/... include a timeout= keyword.
        Skips if no such calls are present.
        """
        source = self._read_source()
        tree = ast.parse(source)
        http_calls = []
        missing_timeout = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                lib = None
                method = None

                # Pattern: requests.get(...), httpx.post(...), etc.
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if func.value.id in {"requests", "httpx"} and func.attr in {"get","post","put","delete","head","options","patch"}:
                        lib = func.value.id
                        method = func.attr

                # Best-effort pattern: from requests import get ; get(...)
                elif isinstance(func, ast.Name) and func.id in {"get","post","put","delete","head","options","patch"} and (
                     "from requests import" in source or "from httpx import" in source
                ):
                    lib = "requests_or_httpx"
                    method = func.id

                if lib:
                    http_calls.append((lib, method, getattr(node, "lineno", -1)))
                    if not any(isinstance(kw, ast.keyword) and kw.arg == "timeout" for kw in (node.keywords or [])):
                        missing_timeout.append((lib, method, getattr(node, "lineno", -1)))

        if not http_calls:
            self.skipTest("No requests/httpx call sites detected in api_tests.py")
        self.assertFalse(
            missing_timeout,
            f"HTTP call(s) missing timeout=: {missing_timeout}"
        )


class TestUrlConstants(unittest.TestCase):
    def test_url_like_constants_are_valid(self):
        """
        Validate that any URL/URI/ENDPOINT-like constants are well-formed http(s) URLs.
        Skips if none are present.
        """
        mod = load_module()
        urlish = []
        for name in dir(mod):
            upper = name.upper()
            if any(marker in upper for marker in ("URL", "URI", "ENDPOINT")):
                val = getattr(mod, name)
                if isinstance(val, str):
                    urlish.append((name, val))
        if not urlish:
            self.skipTest("No URL/URI/ENDPOINT constants found to validate")

        for const_name, value in urlish:
            with self.subTest(constant=const_name):
                parsed = urlparse(value)
                self.assertIn(parsed.scheme, {"http", "https"}, f"{const_name} must start with http or https")
                self.assertTrue(parsed.netloc, f"{const_name} must include a non-empty host")


if __name__ == "__main__":
    unittest.main(verbosity=2)