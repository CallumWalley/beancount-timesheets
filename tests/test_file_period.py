import os
import shutil
import pytest
from beancount_timesheets import file_period, core

@pytest.fixture
def temp_env(tmp_path):
    config_path = tmp_path / "config.yml"
    timesheet_path = tmp_path / "timesheet.beancount"
    ledger_path = tmp_path / "ledger.beancount"
    archive_dir = tmp_path / "filed"
    config = f"""
customers:
  TestCustomer:
    fullName: Test Customer
    archivePath: "filed/{{slug}}_{{min_date}}_{{max_date}}.beancount"
    hourlyRate: 100
ledgerPath: "{ledger_path}"
timesheetPath: "{timesheet_path}"
"""
    config_path.write_text(config)
    timesheet = """
2026-04-01 * "0900 1700" "Worked all day"
    Income:HOURS:Uninvoiced:TestCustomer   8 HOURS
    Income:HoursWorked
"""
    timesheet_path.write_text(timesheet)
    yield {
        "config": str(config_path),
        "timesheet": str(timesheet_path),
        "ledger": str(ledger_path),
        "archive_dir": str(archive_dir),
    }
    shutil.rmtree(tmp_path)

def test_process_timesheet_creates_files(temp_env):
    file_period.file_period(config=temp_env["config"], dry_run=False)
    archive_files = os.listdir(temp_env["archive_dir"])
    assert archive_files, "Archive file not created"
    assert os.path.exists(temp_env["ledger"]), "Ledger file not created"
    with open(temp_env["timesheet"]) as f:
        content = f.read()
    assert core.DEFAULT_TIMESHEET.strip() in content

def test_dry_run_does_not_modify_files(temp_env, capsys):
    orig_timesheet = open(temp_env["timesheet"]).read()
    file_period.file_period(config=temp_env["config"], dry_run=True)
    assert open(temp_env["timesheet"]).read() == orig_timesheet
    captured = capsys.readouterr()
    assert "Would write period file" in captured.out
