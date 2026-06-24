"""
UI Template Loader — loads HTML blocks from ui/index.html by template ID.
"""
import os
import re

_templates = {}


def _load_templates():
    """Parse ui/index.html and extract all <template id="...">...</template> blocks."""
    global _templates
    if _templates:
        return

    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r'<template\s+id="([^"]+)">\s*(.*?)\s*</template>',
        re.DOTALL
    )
    for match in pattern.finditer(content):
        template_id = match.group(1)
        template_html = match.group(2).strip()
        _templates[template_id] = template_html


def get(template_id: str, **kwargs) -> str:
    """
    Get an HTML template by ID, optionally formatting with keyword arguments.

    Usage:
        html = templates.get("verdict-banner", css_class="verdict-true", verdict_value="TRUE")
    """
    _load_templates()
    html = _templates.get(template_id, "")
    if kwargs:
        html = html.format(**kwargs)
    return html
