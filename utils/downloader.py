"""
Simple webpage downloader.
"""

import requests


def download(url):

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        )
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            allow_redirects=True,
        )

        return {
            "success": response.ok,
            "status": response.status_code,
            "url": response.url,
            "html": response.text,
            "size": len(response.text),
            "error": None,
        }

    except Exception as ex:

        return {
            "success": False,
            "status": None,
            "url": url,
            "html": "",
            "size": 0,
            "error": str(ex),
        }