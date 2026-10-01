import xml.etree.ElementTree as ET


def _local_name(tag):
    return str(tag).split("}", 1)[-1]


def _first_text(root, names):
    wanted = set(names)
    for element in root.iter():
        if _local_name(element.tag) in wanted and (element.text or "").strip():
            return element.text.strip()
    return ""


def _unique(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def parse_caaml_bulletin(payload):
    """Estrae una sintesi stabile dal bollettino AINEVA CAAML 5."""
    root = ET.fromstring(payload)
    ratings = []
    problems = []
    regions = []
    for element in root.iter():
        name = _local_name(element.tag)
        text = (element.text or "").strip()
        if name in ("mainValue", "dangerLevel"):
            try:
                value = int(float(text))
                if 1 <= value <= 5:
                    ratings.append(value)
            except (TypeError, ValueError):
                pass
        elif name in ("problemType", "avalancheProblemType") and text:
            problems.append(text)
        elif name in ("locRef", "region", "regionRef", "areaRef"):
            reference = next((value for key, value in element.attrib.items() if _local_name(key) in ("href", "ref")), "")
            if reference:
                regions.append(reference.rsplit("/", 1)[-1].lstrip("#"))

    bulletin_id = next((value for key, value in root.attrib.items() if _local_name(key) == "id"), "")
    ratings = sorted(set(ratings))
    return {
        "bulletin_id": bulletin_id,
        "published_at": _first_text(root, ("dateTimeReport", "publicationTime", "issueTime")),
        "valid_from": _first_text(root, ("beginPosition", "validFrom")),
        "valid_to": _first_text(root, ("endPosition", "validTo")),
        "danger_levels": ratings,
        "max_danger": max(ratings) if ratings else None,
        "problems": _unique(problems),
        "regions": _unique(regions),
    }
