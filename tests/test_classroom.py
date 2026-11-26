import datetime
import unittest

from tests.helpers import Req, paged
import classroom

UTC5 = datetime.timezone(datetime.timedelta(hours=5))


class DueTests(unittest.TestCase):
    def test_no_due_date(self):
        self.assertIsNone(classroom.interpret_due({}))

    def test_date_only_means_end_of_day(self):
        cw = {"dueDate": {"year": 2026, "month": 11, "day": 26}}
        self.assertEqual(classroom.interpret_due(cw, UTC5), datetime.datetime(2026, 11, 26, 23, 59, 59))

    def test_utc_time_is_converted_to_local(self):
        cw = {"dueDate": {"year": 2026, "month": 11, "day": 26},
              "dueTime": {"hours": 20, "minutes": 30}}
        self.assertEqual(classroom.interpret_due(cw, UTC5), datetime.datetime(2026, 11, 27, 1, 30))

    def test_empty_due_time_is_midnight_utc(self):
        cw = {"dueDate": {"year": 2026, "month": 11, "day": 26}, "dueTime": {}}
        self.assertEqual(classroom.interpret_due(cw, UTC5), datetime.datetime(2026, 11, 26, 5, 0))

    def test_bad_date_is_none(self):
        self.assertIsNone(classroom.interpret_due({"dueDate": {"year": 2026, "month": 13, "day": 1}}))


class BucketTests(unittest.TestCase):
    def test_no_overlap(self):
        now = datetime.datetime(2026, 11, 26, 15, 0)
        mk = lambda due: {"due": due}  # noqa: E731
        work = [mk(datetime.datetime(2026, 11, 26, 9, 0)),   # earlier today -> overdue only
                mk(datetime.datetime(2026, 11, 26, 18, 0)),  # later today
                mk(datetime.datetime(2026, 11, 30, 9, 0)),
                mk(None)]
        b = classroom.bucket(work, now)
        self.assertEqual([len(b[k]) for k in ("overdue", "today", "upcoming", "nodue")], [1, 1, 1, 1])


class FakeClassroom:
    def __init__(self, course_pages, work_pages, sub_pages, fail=()):
        self.course_pages, self.work_pages, self.sub_pages, self.fail = course_pages, work_pages, sub_pages, fail

    def courses(self):
        svc = self

        class Courses:
            def list(self, **kw):
                return paged(svc.course_pages)(**kw)

            def courseWork(self):
                class CW:
                    def list(_, courseId, **kw):
                        if courseId in svc.fail:
                            return Req(exc=RuntimeError("boom"))
                        return paged(svc.work_pages[courseId])(courseId=courseId, **kw)

                    def studentSubmissions(_):
                        class Subs:
                            def list(_, courseId, **kw):
                                assert kw["courseWorkId"] == "-" and kw["userId"] == "me"
                                return paged(svc.sub_pages[courseId])(**kw)
                        return Subs()
                return CW()
        return Courses()


def date(d):
    return {"year": 2026, "month": 12, "day": d}


class FetchTests(unittest.TestCase):
    def test_pagination_states_and_warnings(self):
        svc = FakeClassroom(
            course_pages=[{"courses": [{"id": "c1", "name": "Math"}]},
                          {"courses": [{"id": "c2", "name": "Bio"}, {"id": "c3", "name": "Bad"}]}],
            work_pages={
                "c1": [{"courseWork": [{"id": "a", "title": "A", "dueDate": date(5)}]},
                       {"courseWork": [{"id": "b", "title": "B", "dueDate": date(2)},
                                       {"id": "c", "title": "C (turned in)"},
                                       {"id": "d", "title": "D (graded)"},
                                       {"id": "e", "title": "E (not mine)"}]}],
                "c2": [{"courseWork": [{"id": "f", "title": "F", "workType": "MULTIPLE_CHOICE_QUESTION"}]}],
            },
            sub_pages={
                "c1": [{"studentSubmissions": [{"courseWorkId": "a", "state": "NEW"},
                                               {"courseWorkId": "c", "state": "TURNED_IN"}]},
                       {"studentSubmissions": [{"courseWorkId": "b", "state": "CREATED"},
                                               {"courseWorkId": "d", "state": "RETURNED", "assignedGrade": 9}]}],
                "c2": [{"studentSubmissions": [{"courseWorkId": "f", "state": "RECLAIMED_BY_STUDENT"}]}],
            },
            fail=("c3",),
        )
        pending, warnings = classroom.fetch_pending_work(svc)
        self.assertEqual([w["title"] for w in pending], ["B", "A", "F"])  # sorted, no-due last
        self.assertTrue(classroom.is_quiz(pending[2]))
        self.assertTrue(classroom.is_assignment(pending[0]))
        self.assertEqual(len(warnings), 1)
        self.assertIn("Bad", warnings[0])


if __name__ == "__main__":
    unittest.main()
