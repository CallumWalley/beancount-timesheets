from pathlib import Path

import pytest


@pytest.fixture
def period_file_factory():
    def _write_period_file(path, customer_name, narration="Worked all day"):
        path.write_text(
            f"2026-04-01 * \"0900 1700\" \"{narration}\"\n"
            f"    Income:HOURS:Uninvoiced:{customer_name}   8 HOURS\n"
            "    Income:HoursWorked\n"
        )

    return _write_period_file


@pytest.fixture
def template_factory():
    def _write_template(path, content="{{ customer.code }}{{ customer.invoiceNumber }} {{ hourlyRate }}"):
        path.write_text(content)

    return _write_template


@pytest.fixture
def temp_env(tmp_path, period_file_factory):
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
    period_file_factory(timesheet_path, "TestCustomer")
    return {
        "config": str(config_path),
        "timesheet": str(timesheet_path),
        "ledger": str(ledger_path),
        "archive_dir": str(archive_dir),
    }