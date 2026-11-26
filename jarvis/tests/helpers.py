import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class Req:
    """Mimics a googleapiclient request: .execute() returns the response."""

    def __init__(self, resp=None, exc=None):
        self.resp, self.exc = resp, exc

    def execute(self):
        if self.exc:
            raise self.exc
        return self.resp


def paged(pages):
    """A list() function that serves `pages` one at a time via pageToken."""
    def list_(**kw):
        idx = int(kw.get("pageToken") or 0)
        resp = dict(pages[idx])
        if idx + 1 < len(pages):
            resp["nextPageToken"] = str(idx + 1)
        return Req(resp)
    return list_
