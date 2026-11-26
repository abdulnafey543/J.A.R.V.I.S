import datetime

QUIZ_TYPES = {"SHORT_ANSWER_QUESTION", "MULTIPLE_CHOICE_QUESTION"}
ASSIGNMENT_TYPES = {"ASSIGNMENT"}
# Submission states that mean "nothing left for the student to do".
DONE_STATES = {"TURNED_IN", "RETURNED"}


def _paginate(call, key, **kwargs):
    """Collect every page of a Google API list call."""
    items, token = [], None
    while True:
        kw = dict(kwargs)
        if token:
            kw["pageToken"] = token
        resp = call(**kw).execute()
        items.extend(resp.get(key, []))
        token = resp.get("nextPageToken")
        if not token:
            return items


def fetch_pending_work(service=None):
    """Return (pending, warnings). Pending work is sorted by due date.

    Warnings describe courses that could not be read, so one broken course
    never hides the rest (and the user is told about it).
    """
    if service is None:
        from auth import classroom_service
        service = classroom_service()
    pending, warnings = [], []
    courses = _paginate(service.courses().list, "courses", courseStates=["ACTIVE"])
    for course in courses:
        cid = course["id"]
        name = course.get("name", "Unknown course")
        try:
            work = _paginate(service.courses().courseWork().list, "courseWork", courseId=cid)
            if not work:
                continue
            # courseWorkId="-" returns this student's submissions for the
            # whole course in one request instead of one request per task.
            subs = _paginate(
                service.courses().courseWork().studentSubmissions().list,
                "studentSubmissions", courseId=cid, courseWorkId="-", userId="me",
            )
        except Exception as e:  # noqa: BLE001 - report and carry on
            warnings.append(f"couldn't read course '{name}': {e}")
            continue
        by_work = {}
        for s in subs:
            by_work.setdefault(s.get("courseWorkId"), s)
        for cw in work:
            sub = by_work.get(cw["id"])
            if sub is None:  # not assigned to this student
                continue
            state = sub.get("state", "NEW")
            if state in DONE_STATES:
                continue
            pending.append({
                "course": name,
                "title": cw.get("title", "Untitled"),
                "workType": cw.get("workType", "ASSIGNMENT"),
                "due": interpret_due(cw),
                "state": state,
                "link": cw.get("alternateLink", ""),
                "graded": sub.get("assignedGrade"),
            })
    pending.sort(key=lambda x: x["due"] or datetime.datetime.max)
    return pending, warnings


def interpret_due(cw, tz=None):
    """Due date as a naive datetime in local time (or in `tz`).

    Google sends dueTime in UTC, so it is converted. A due date with no
    dueTime at all means "end of that day".
    """
    d = cw.get("dueDate")
    if not d:
        return None
    try:
        year, month, day = int(d.get("year", 1)), int(d.get("month", 1)), int(d.get("day", 1))
        if "dueTime" not in cw:
            return datetime.datetime(year, month, day, 23, 59, 59)
        t = cw["dueTime"] or {}  # Google omits zero fields, so {} is 00:00 UTC
        utc = datetime.datetime(
            year, month, day,
            int(t.get("hours", 0)), int(t.get("minutes", 0)), int(t.get("seconds", 0)),
            tzinfo=datetime.timezone.utc,
        )
        return utc.astimezone(tz).replace(tzinfo=None)
    except (ValueError, TypeError, OverflowError):
        return None


def bucket(work, now):
    """Split work into overdue / today / upcoming / nodue with no overlap."""
    out = {"overdue": [], "today": [], "upcoming": [], "nodue": []}
    for w in work:
        due = w["due"]
        if due is None:
            out["nodue"].append(w)
        elif due < now:
            out["overdue"].append(w)
        elif due.date() == now.date():
            out["today"].append(w)
        else:
            out["upcoming"].append(w)
    return out


def is_quiz(item):
    return item["workType"] in QUIZ_TYPES


def is_assignment(item):
    return item["workType"] in ASSIGNMENT_TYPES
