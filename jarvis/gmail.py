import re
from email.header import decode_header, make_header

MAX_EMAILS = 20


def decode_header_value(value):
    """Decode RFC 2047 encoded words like =?utf-8?q?Caf=C3=A9?= ."""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001 - malformed headers are common
        return value


def fetch_unread_emails(limit=MAX_EMAILS, service=None):
    """Return (emails, has_more). has_more is True if more unread mail exists."""
    if service is None:
        from auth import gmail_service
        service = gmail_service()
    ids, token = [], None
    while len(ids) < limit:
        kw = {
            "userId": "me",
            "q": "in:inbox is:unread",
            "maxResults": min(100, limit - len(ids)),
        }
        if token:
            kw["pageToken"] = token
        res = service.users().messages().list(**kw).execute()
        ids.extend(m["id"] for m in res.get("messages", []))
        token = res.get("nextPageToken")
        if not token:
            break
    has_more = bool(token)
    emails = []
    for msg_id in ids[:limit]:
        try:
            details = (
                service.users().messages()
                .get(userId="me", id=msg_id, format="metadata",
                     metadataHeaders=["Subject", "From", "Date"])
                .execute()
            )
        except Exception:  # noqa: BLE001 - message deleted since listing
            continue
        headers = {
            h["name"].lower(): h["value"]
            for h in details.get("payload", {}).get("headers", [])
        }
        emails.append({
            "id": msg_id,
            "subject": decode_header_value(headers.get("subject", "(no subject)")),
            "from": clean_sender(headers.get("from", "unknown")),
            "date": headers.get("date", ""),
            "snippet": details.get("snippet", ""),
        })
    return emails, has_more


def clean_sender(raw):
    raw = decode_header_value(raw or "").strip()
    match = re.match(r'^\s*"?(.*?)"?\s*<([^<>]+)>\s*$', raw)
    if match:
        return match.group(1).strip().strip('"').strip() or match.group(2).strip()
    return raw or "unknown"
