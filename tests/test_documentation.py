# NOTE: Testing library and framework
# This test suite uses Python's built-in unittest framework for maximum compatibility.
# It is also compatible with pytest, which can discover and run unittest.TestCase tests.
#
# Focus note:
# The pull request diff (<diff>) was not provided in this context, so these tests focus on
# robust documentation integrity checks that are generally valuable and will exercise
# changes made to Markdown documentation files in the PR.

import re
import unittest
from pathlib import Path
from urllib.parse import urlparse, unquote


# Directories commonly excluded from documentation validation to avoid scanning generated or vendored content.
_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "site",
    "coverage",
    "htmlcov",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
    "target",
    "bin",
    "obj",
    "public",
    "out",
}


def _get_repo_root() -> Path:
    # tests/test_documentation.py -> repo root
    return Path(__file__).resolve().parents[1]


def _is_excluded(path: Path) -> bool:
    # Exclude if any path component is in the excluded set
    return any(part in _EXCLUDED_DIRS for part in path.parts)


def _iter_markdown_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for p in repo_root.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".md" and not _is_excluded(p):
            files.append(p)
    return files


def _split_front_matter_start_index(lines: list[str]) -> int:
    """
    Returns the index of the first content line after YAML front matter, if present.
    If no front matter, returns 0 (start from beginning).
    """
    i = 0
    n = len(lines)
    # Skip initial blank lines
    while i < n and lines[i].strip() == "":
        i += 1
    # YAML front matter starts with '---' and ends with the next '---'
    if i < n and lines[i].strip() == "---":
        j = i + 1
        while j < n and lines[j].strip() != "---":
            j += 1
        if j < n:
            return j + 1
    return 0


def _normalize_local_target(md_file: Path, target: str, repo_root: Path) -> Path | None:
    """
    Convert a Markdown link target into a local filesystem candidate path if it's a local reference.
    Returns None if it's an external URL or an anchor-only link.
    """
    target = unquote(target.strip())

    # Empty or pure anchor link
    if not target or target.startswith("#"):
        return None

    # Strip fragment and query
    if "#" in target:
        target = target.split("#", 1)[0]
    if "?" in target:
        target = target.split("?", 1)[0]

    # External URLs (or data URIs etc.)
    parsed = urlparse(target)
    if parsed.scheme not in ("", "file") or parsed.netloc:
        return None

    if parsed.scheme == "file":
        target = parsed.path

    # Absolute path from repo root (e.g., /docs/file.md)
    if target.startswith("/"):
        candidate = (repo_root / target.lstrip("/")).resolve()
    else:
        candidate = (md_file.parent / target).resolve()

    return candidate


def _candidate_exists(candidate: Path) -> bool:
    """
    Determine if the candidate path exists. Also allow common Markdown conventions:
    - Directories containing README.md or index.md
    - Targets without an extension where appending .md (case-insensitive) would exist
    """
    if candidate.exists():
        return True

    # If candidate looks like a directory, check for README/index files
    if candidate.is_dir():
        for name in ("README.md", "readme.md", "INDEX.md", "index.md"):
            if (candidate / name).exists():
                return True

    # If candidate has no suffix, try adding .md
    if candidate.suffix == "":
        for ext in (".md", ".MD"):
            if Path(str(candidate) + ext).exists():
                return True

    return False


def _extract_links_and_images(md_file: Path) -> tuple[list[str], list[tuple[int, str]], list[tuple[int, str, str]]]:
    """
    Extract content lines, inline links and images outside of fenced code blocks.
    Returns:
      - lines: raw text lines
      - links: list of (line_number, href)
      - images: list of (line_number, alt_text, src)
    """
    lines = md_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    in_fence = False
    fence_re = re.compile(r"^\s*```")
    # Exclude images via negative lookbehind for plain links; parse images separately
    link_re = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+?)\)")
    image_re = re.compile(r"!\[([^\]]*)\]\(([^)\s]+?)\)")

    links: list[tuple[int, str]] = []
    images: list[tuple[int, str, str]] = []

    for idx, line in enumerate(lines, 1):
        if fence_re.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for m in image_re.finditer(line):
            alt = m.group(1) or ""
            src = m.group(2)
            images.append((idx, alt, src))

        for m in link_re.finditer(line):
            href = m.group(1)
            links.append((idx, href))

    return lines, links, images


class TestMarkdownDocumentationIntegrity(unittest.TestCase):
    """
    Validates Markdown documentation quality across the repository:
      - No broken relative links or images
      - Each Markdown file has a top-level title (ATX '# ' or Setext '===='/'----')
      - All images have non-empty alt text
    """

    @classmethod
    def setUpClass(cls):
        cls.repo_root = _get_repo_root()
        cls.md_files = _iter_markdown_files(cls.repo_root)

    def test_no_broken_relative_links_in_markdown(self):
        """
        Happy path: All local links and images resolve to existing files.
        Edge cases: Links to directories, links without extension, README/index conventions, absolute repo-root links.
        Failure conditions: Any relative link or image that cannot be resolved.
        """
        broken: list[str] = []
        for md in self.md_files:
            _, links, images = _extract_links_and_images(md)

            # Validate standard links
            for ln, href in links:
                candidate = _normalize_local_target(md, href, self.repo_root)
                if candidate is None:
                    # External or anchor link - skip
                    continue
                if not _candidate_exists(candidate):
                    broken.append(f"{md}:{ln} -> {href} (resolved: {candidate})")

            # Validate image sources
            for ln, _alt, src in images:
                candidate = _normalize_local_target(md, src, self.repo_root)
                if candidate is None:
                    # External or anchor image (rare) - skip
                    continue
                if not _candidate_exists(candidate):
                    broken.append(f"{md}:{ln} -> image {src} (resolved: {candidate})")

        if broken:
            self.fail("Broken relative Markdown links/images found:\n" + "\n".join(sorted(broken)))

    def test_all_markdown_have_title_or_front_matter(self):
        """
        Ensures each Markdown file begins with a top-level heading,
        allowing for optional YAML front matter and Setext-style headings.
        """
        failures: list[str] = []
        for md in self.md_files:
            lines = md.read_text(encoding="utf-8", errors="ignore").splitlines()
            start = _split_front_matter_start_index(lines)

            # Skip blank lines after front matter
            i = start
            while i < len(lines) and lines[i].strip() == "":
                i += 1

            if i >= len(lines):
                failures.append(f"{md}: file is empty or whitespace only")
                continue

            first = lines[i].rstrip()

            # ATX heading
            if first.startswith("#"):
                continue

            # Setext-style heading: next line all '=' or '-' characters
            if i + 1 < len(lines):
                underline = lines[i + 1].strip()
                if underline and all(c == "=" for c in underline):
                    continue
                if underline and all(c == "-" for c in underline):
                    continue

            failures.append(f"{md}: missing top-level heading")

        if failures:
            self.fail("Markdown files missing a top-level heading:\n" + "\n".join(sorted(failures)))

    def test_all_images_have_alt_text(self):
        """
        Ensures images include descriptive alt text for accessibility.
        """
        missing_alt: list[str] = []
        for md in self.md_files:
            _, _links, images = _extract_links_and_images(md)
            for ln, alt, src in images:
                if alt.strip() == "":
                    missing_alt.append(f"{md}:{ln} -> {src}")

        if missing_alt:
            self.fail("Images missing alt text:\n" + "\n".join(sorted(missing_alt)))