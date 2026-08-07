import requests
from requests.exceptions import RequestException


def download(url: str):

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/138.0 Safari/537.36"
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
            "headers": dict(response.headers),
        }

    except RequestException as ex:

        return {
            "success": False,
            "status": None,
            "error": str(ex),
        }