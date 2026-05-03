import os
from beancount_timesheets.file_period import file_period
import beancount_timesheets.core as core

def test_process_timesheet_creates_files(temp_env):
    file_period(config=temp_env["config"], dry_run=False)
    archive_files = os.listdir(temp_env["archive_dir"])
    assert archive_files, "Archive file not created"
    assert os.path.exists(temp_env["ledger"]), "Ledger file not created"
    with open(temp_env["timesheet"]) as f:
        content = f.read()
    assert core.DEFAULT_TIMESHEET.strip() in content

def test_dry_run_does_not_modify_files(temp_env, capsys):
    orig_timesheet = open(temp_env["timesheet"]).read()
    file_period(config=temp_env["config"], dry_run=True)
    assert open(temp_env["timesheet"]).read() == orig_timesheet
    captured = capsys.readouterr()
    assert "Would write period file" in captured.out
