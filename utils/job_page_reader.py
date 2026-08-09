"""
Academic Job Bot
Job Page Reader - Version 1.9
"""

import io
import re

from bs4 import BeautifulSoup


# =========================================================
# HTML TO TEXT
# =========================================================

def html_to_text(
    html
):

    if not html:

        return ""

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Remove useless elements.
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
        ]
    ):

        tag.decompose()

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# TITLE FROM HTML
# =========================================================

def extract_title(
    html
):

    if not html:

        return ""

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # -----------------------------------------------------
    # H1
    # -----------------------------------------------------

    for tag in soup.find_all(
        ["h1", "h2"]
    ):

        text = tag.get_text(
            " ",
            strip=True
        )

        if len(text) < 8:

            continue

        lowered = text.lower()

        if lowered in {
            "read news post",
            "more info",
            "more information",
            "home",
            "careers",
        }:

            continue

        return text

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    if soup.title:

        text = soup.title.get_text(
            " ",
            strip=True
        )

        if text:

            return text

    return ""


# =========================================================
# PDF TEXT
# =========================================================

def extract_pdf_text(
    content
):

    if not content:

        return ""

    try:

        from pypdf import PdfReader

        reader = PdfReader(
            io.BytesIO(content)
        )

        pages = []

        for page in reader.pages:

            try:

                text = page.extract_text()

            except Exception:

                text = ""

            if text:

                pages.append(
                    text
                )

        result = "\n".join(
            pages
        )

        result = re.sub(
            r"\s+",
            " ",
            result
        )

        return result.strip()

    except Exception as exc:

        print(
            "  PDF text extraction failed: "
            f"{exc}"
        )

        return ""


# =========================================================
# FILENAME TITLE
# =========================================================

def filename_title(
    url
):

    if not url:

        return ""

    # Get last path component.
    filename = url.split(
        "/"
    )[-1]

    filename = filename.split(
        "?"
    )[0]

    filename = re.sub(
        r"\.pdf$",
        "",
        filename,
        flags=re.IGNORECASE
    )

    filename = filename.replace(
        "-",
        " "
    ).replace(
        "_",
        " "
    )

    filename = re.sub(
        r"\s+",
        " ",
        filename
    ).strip()

    return filename


# =========================================================
# UNB FILENAME MAPPING
# =========================================================

UNB_TITLE_MAP = {

    "25-29-business": (
        "Faculty of Business: Tenure-Track "
        "Assistant or Associate Professor in Strategy"
    ),

    "25-30-business": (
        "Faculty of Business: Tenure-Track "
        "Assistant Professor in Digital Business"
    ),

    "25-34-mgmt": (
        "Faculty of Management: Term Assistant "
        "Professor in Marketing"
    ),

}


def mapped_filename_title(
    url
):

    filename = filename_title(
        url
    ).lower()

    for key, title in UNB_TITLE_MAP.items():

        if key in filename:

            return title

    return ""


# =========================================================
# MAIN
# =========================================================

def read_job_page(
    page,
    url
):

    html = page.get(
        "html",
        ""
    )

    content = page.get(
        "content",
        b""
    )

    is_pdf = page.get(
        "is_pdf",
        False
    )

    title = ""

    text = ""

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    if is_pdf:

        text = extract_pdf_text(
            content
        )

        title = mapped_filename_title(
            url
        )

        if not title:

            title = filename_title(
                url
            )

    # -----------------------------------------------------
    # HTML
    # -----------------------------------------------------

    else:

        title = extract_title(
            html
        )

        text = html_to_text(
            html
        )

    # -----------------------------------------------------
    # URL text
    # -----------------------------------------------------

    url_text = str(
        page.get(
            "url",
            url
        )
    )

    # -----------------------------------------------------
    # If PDF extraction failed but HTML exists,
    # read HTML.
    # -----------------------------------------------------

    if not text and html:

        text = html_to_text(
            html
        )

    return {

        "title":
            title,

        "text":
            text,

        "url_text":
            url_text,

    }