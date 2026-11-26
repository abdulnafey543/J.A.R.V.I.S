import unittest

from tests.helpers import Req, paged
import gmail


class FakeGmail:
    def __init__(self, pages, broken=()):
        self.pages, self.broken, self.list_calls = pages, broken, []

    def users(self):
        return self

    def messages(self):
        return self

    def list(self, **kw):
        self.list_calls.append(kw)
        return paged(self.pages)(**kw)

    def get(self, **kw):
        if kw["id"] in self.broken:
            return Req(exc=RuntimeError("404"))
        return Req({"snippet": "snip " + kw["id"], "payload": {"headers": [
            {"name": "subject", "value": "S" + kw["id"]},
            {"name": "FROM", "value": '"Doe, Jane" <j@x.com>'},
            {"name": "Date", "value": "today"}]}})


class SenderTests(unittest.TestCase):
    def test_clean_sender(self):
        cases = {
            '"Doe, Jane" <j@x.com>': "Doe, Jane",
            "Jane <j@x.com>": "Jane",
            "<j@x.com>": "j@x.com",
            "j@x.com": "j@x.com",
            "": "unknown",
            "=?utf-8?q?Caf=C3=A9?= <c@x.com>": "Caf\u00e9",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(gmail.clean_sender(raw), expected)

    def test_decode_subject(self):
        self.assertEqual(gmail.decode_header_value("=?utf-8?q?Caf=C3=A9_menu?="), "Caf\u00e9 menu")
        self.assertEqual(gmail.decode_header_value("plain"), "plain")


class FetchTests(unittest.TestCase):
    def pages(self, *sizes):
        n = 0
        out = []
        for size in sizes:
            out.append({"messages": [{"id": str(n + i)} for i in range(size)]})
            n += size
        return out

    def test_reads_across_pages_and_flags_more(self):
        svc = FakeGmail(self.pages(3, 3, 3))
        emails, has_more = gmail.fetch_unread_emails(limit=5, service=svc)
        self.assertEqual(len(emails), 5)
        self.assertTrue(has_more)
        self.assertEqual(emails[0]["subject"], "S0")
        self.assertEqual(emails[0]["from"], "Doe, Jane")  # header names are case-insensitive

    def test_no_more_when_exhausted(self):
        emails, has_more = gmail.fetch_unread_emails(limit=20, service=FakeGmail(self.pages(2, 1)))
        self.assertEqual(len(emails), 3)
        self.assertFalse(has_more)

    def test_deleted_message_is_skipped(self):
        emails, _ = gmail.fetch_unread_emails(limit=5, service=FakeGmail(self.pages(3), broken=("1",)))
        self.assertEqual([e["id"] for e in emails], ["0", "2"])

    def test_empty_inbox(self):
        emails, has_more = gmail.fetch_unread_emails(service=FakeGmail([{}]))
        self.assertEqual((emails, has_more), ([], False))


if __name__ == "__main__":
    unittest.main()
