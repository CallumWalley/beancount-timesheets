import tempfile
import os
import shutil
from beancount_timesheets import file_period

def test_file_period():
    example_dir = os.path.join(os.path.dirname(__file__), "../example")
    timesheet_path = os.path.join(example_dir, "timesheet.beancount")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_timesheet = os.path.join(tmpdir, "timesheet.beancount")
        test_period = os.path.join(tmpdir, "-04-01_2026-04-27.beancount")
        shutil.copy(timesheet_path, test_timesheet)
        # Add a test entry
        with open(test_timesheet, "a") as f:
            f.write("2026-04-01 * 'start' 'desc'\n  Income:HOURS:Uninvoiced:   2 HOURS\n  Income:HoursWorked                         -2 HOURS\n")
        file_period(test_timesheet, test_period, "2026-04-01", "2026-04-27")
        with open(test_timesheet) as f:
            assert f.read().strip() == "" or f.read().strip() == "; Example Transaction\n; 2023-03-31 * \"timestart timeend\" \"What you were doing\"\n;     Income:HOURS:Uninvoiced:   1 HOURS\n;     Income:HoursWorked"
        with open(test_period) as f:
            content = f.read()
        assert "2026-04-01 * 'start' 'desc'" in content
