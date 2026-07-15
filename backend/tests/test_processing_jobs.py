import unittest

from backend.app.processing import calculate_job_percent


class ProcessingJobTests(unittest.TestCase):
    def test_completed_jobs_always_report_full_progress(self) -> None:
        self.assertEqual(calculate_job_percent(0, 10, "completed"), 100)

    def test_running_jobs_are_capped_below_complete(self) -> None:
        self.assertEqual(calculate_job_percent(5, 10, "running"), 50)
        self.assertEqual(calculate_job_percent(10, 10, "running"), 99)

    def test_invalid_totals_report_zero_progress(self) -> None:
        self.assertEqual(calculate_job_percent(1, 0, "running"), 0)


if __name__ == "__main__":
    unittest.main()
