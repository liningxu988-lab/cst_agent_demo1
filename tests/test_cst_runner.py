import unittest

from cst_runner import _has_actionable_cst_error


class DummyCtrl:
    def __init__(self, report):
        self._report = report

    def get_cst_error_report(self):
        return self._report


class TestCSTRunnerErrorReport(unittest.TestCase):
    def test_actionable_when_message_exists(self):
        ctrl = DummyCtrl({"message": "Solver failed", "cst_report": {}})
        self.assertTrue(_has_actionable_cst_error(ctrl))

    def test_not_actionable_when_report_clean(self):
        ctrl = DummyCtrl({"message": "", "cst_report": {"output_txt": "Simulation finished, 0 errors."}})
        self.assertFalse(_has_actionable_cst_error(ctrl))

    def test_actionable_when_log_contains_error(self):
        ctrl = DummyCtrl({"message": "", "cst_report": {"output_txt": "Fatal error: mesh failed"}})
        self.assertTrue(_has_actionable_cst_error(ctrl))


if __name__ == "__main__":
    unittest.main()
