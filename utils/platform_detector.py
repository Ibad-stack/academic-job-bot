def detect_platform(html: str, url: str):

    text = (html + " " + url).lower()

    if "myworkdayjobs" in text:
        return "Workday"

    if "dayforce" in text:
        return "Dayforce"

    if "pageup" in text:
        return "PageUp"

    if "peopleadmin" in text:
        return "PeopleAdmin"

    if "oracle" in text:
        return "Oracle"

    if "successfactors" in text:
        return "SuccessFactors"

    return "Custom"