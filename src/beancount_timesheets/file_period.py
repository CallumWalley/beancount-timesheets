import os
from datetime import date
import typer
from collections import defaultdict
from beancount.loader import load_file
from beancount.core.data import Transaction
from beancount.parser import printer
import beancount_timesheets.core as core

def file_period(
    config: str = typer.Option("beancount-timesheets-config.yml", "-c", "--config", help="Path to config.yml (default: ./config.yml next to timesheet file)"),
    dry_run: bool = typer.Option(False, "-d", "--dry-run", help="Print changes instead of writing to files"),
):

    config = core.parse_config(config)
    timesheet_file = core.format_path( config["timesheetPath"], **config )

    print(f"Reading {timesheet_file}")
    entries, errors, options_map = load_file(timesheet_file)
    if not entries:
        raise Exception("Warning: No entries to file.")

    customers = dict(config["customers"])
    customer_entries = defaultdict(list)

    for entry in entries:
        if isinstance(entry, Transaction):
            cust_key = core.match_customer(entry, customers)
            if cust_key not in customers:
                new_cust = dict(core.DEFAULT_CUSTOMER)
                new_cust["code"] = core.generate_code(cust_key)
                new_cust["fullName"] = cust_key
                customers[cust_key] = new_cust
                print(f"Warning: '{cust_key}' not found in customer list, using default.")
            customer_entries[cust_key].append(entry)

    print(f"Found {len(entries)} total entries.")

    for cust_key, period_entries in customer_entries.items():
        cust = customers[cust_key]
        print(f"    {cust_key}: {len(period_entries)}")
        dates = [str(entry.date) for entry in period_entries]
        min_date = min(dates)
        max_date = max(dates)

        invoiceKey = core.format_path(cust["invoiceKey"],  slug=cust_key, min_date=min_date, max_date=max_date, cust_key=cust_key, **cust)

        # Write period entries to archivePath
        archivePath = core.format_path(cust["archivePath"], slug=cust_key, min_date=min_date, max_date=max_date, cust_key=cust_key, **cust )
        archiveTimesheet = core.render_entries(period_entries)
        ledgerPath = core.format_path(config["ledgerPath"],  slug=cust_key, min_date=min_date, max_date=max_date, cust_key=cust_key, **cust )
        ledgerSummary = core.ledger_transaction(period_entries, cust, cust_key, config, min_date, max_date)

        if dry_run:
            print(f"Would write to {archivePath}:\n---\n{archiveTimesheet}---\n")
            print(f"Would append to {ledgerPath}:\n---\n{ledgerSummary}---\n")

        else:
            core.write_file(archivePath, archiveTimesheet + "\n", append=False)
            core.write_file(ledgerPath, ledgerSummary, append=True)
    if dry_run:
        print(f"Would overrite {timesheet_file}:\n---\n{core.DEFAULT_TIMESHEET}---\n")
    else:
        core.write_file(timesheet_file, core.DEFAULT_TIMESHEET)

if __name__ == "__main__":
    typer.run(file_period)