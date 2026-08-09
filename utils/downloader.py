"""
Academic Job Bot
Downloader - Version 1.9

Handles:
- normal HTML
- PDFs
- university document URLs that return HTML
- redirects
- Workday pages
- content-type detection
- basic browser-like headers
"""

import io
import re

import requests


TIMEOUT = 30


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "application/pdf;q=0.8,*/*;q=0.7"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
    "Connection": "keep-alive",
}


# =========================================================
# HTML TEST
# =========================================================

def looks_like_html(content):

    if not content:

        return False

    sample = content[:1000].lower()

    return (
        b"<html" in sample
        or b"<!doctype" in sample
        or b"<head" in sample
        or b"<body" in sample
    )


# =========================================================
# PDF TEST
# =========================================================

def looks_like_pdf(content):

    if not content:

        return False

    return content[:5] == b"%PDF-"


# =========================================================
# CLEAN HTML
# =========================================================

def clean_html_bytes(content):

    if not content:

        return ""

    try:

        return content.decode(
            "utf-8",
            errors="replace"
        )

    except Exception:

        return content.decode(
            errors="replace"
        )


# =========================================================
# EXTRACT REAL PDF LINK
# =========================================================

def find_pdf_links(
    html,
    base_url
):

    if not html:

        return []

    links = []

    # Absolute PDF links.
    pattern = re.compile(
        r"""(?:href|src)=["']([^"']+\.pdf(?:\?[^"']*)?)["']""",
        re.IGNORECASE
    )

    for match in pattern.finditer(
        html
    ):

        links.append(
            match.group(1)
        )

    return links


# =========================================================
# REQUEST
# =========================================================

def _request(
    url
):

    try:

        response = requests.get(

            url,

            headers=HEADERS,

            timeout=TIMEOUT,

            allow_redirects=True,

        )

        return response

    except Exception as exc:

        return exc


# =========================================================
# DOWNLOAD
# =========================================================

def download(
    url
):

    url = str(
        url or ""
    ).strip()

    if not url:

        return {

            "success": False,

            "status": None,

            "url": "",

            "html": "",

            "content": b"",

            "content_type": "",

            "is_pdf": False,

            "is_html": False,

            "error": "Empty URL",

        }

    # -----------------------------------------------------
    # mailto links are not jobs.
    # -----------------------------------------------------

    if url.lower().startswith(
        "mailto:"
    ):

        return {

            "success": False,

            "status": None,

            "url": url,

            "html": "",

            "content": b"",

            "content_type": "",

            "is_pdf": False,

            "is_html": False,

            "error": "Email link",

        }

    response = _request(
        url
    )

    # -----------------------------------------------------
    # Request failure.
    # -----------------------------------------------------

    if isinstance(
        response,
        Exception
    ):

        return {

            "success": False,

            "status": None,

            "url": url,

            "html": "",

            "content": b"",

            "content_type": "",

            "is_pdf": False,

            "is_html": False,

            "error": str(response),

        }

    content = response.content

    content_type = (
        response.headers
        .get(
            "Content-Type",
            ""
        )
        .lower()
    )

    final_url = str(
        response.url
    )

    is_pdf = (
        "application/pdf"
        in content_type
        or looks_like_pdf(
            content
        )
    )

    is_html = (
        "text/html"
        in content_type
        or "application/xhtml"
        in content_type
        or looks_like_html(
            content
        )
    )

    # -----------------------------------------------------
    # HTTP error.
    # -----------------------------------------------------

    if response.status_code >= 400:

        return {

            "success": False,

            "status":
                response.status_code,

            "url":
                final_url,

            "html":
                clean_html_bytes(
                    content
                ) if is_html else "",

            "content":
                content,

            "content_type":
                content_type,

            "is_pdf":
                is_pdf,

            "is_html":
                is_html,

            "error":
                f"HTTP {response.status_code}",

        }

    # -----------------------------------------------------
    # PDF.
    # -----------------------------------------------------

    if is_pdf:

        return {

            "success": True,

            "status":
                response.status_code,

            "url":
                final_url,

            "html":
                "",

            "content":
                content,

            "content_type":
                content_type,

            "is_pdf":
                True,

            "is_html":
                False,

            "error":
                None,

        }

    # -----------------------------------------------------
    # HTML.
    # -----------------------------------------------------

    if is_html:

        html = clean_html_bytes(
            content
        )

        return {

            "success": True,

            "status":
                response.status_code,

            "url":
                final_url,

            "html":
                html,

            "content":
                content,

            "content_type":
                content_type,

            "is_pdf":
                False,

            "is_html":
                True,

            "error":
                None,

        }

    # -----------------------------------------------------
    # Unknown content.
    #
    # Treat textual content as HTML-ish so the reader
    # still has a chance to extract useful information.
    # -----------------------------------------------------

    html = clean_html_bytes(
        content
    )

    return {

        "success": True,

        "status":
            response.status_code,

        "url":
            final_url,

        "html":
            html,

        "content":
            content,

        "content_type":
            content_type,

        "is_pdf":
            False,

        "is_html":
            False,

        "error":
            None,

    }