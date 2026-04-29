import os
from datetime import date
import typer
from collections import defaultdict
from beancount.loader import load_file
from beancount.core.data import Transaction
import beancount_timesheets.config as btc
from beancount.parser import printer
from beancount_timesheets.core import (
    format_path, write_file, generate_code
)

def file_period(
    config: str = typer.Option(None, "-c", "--config", help="Path to config.yml (default: ./config.yml next to timesheet file)"),
    dry_run: bool = typer.Option(False, "-d", "--dry-run", help="Print changes instead of writing to files"),
):

    config = btc.parse_config(config)
    timesheet_file = config["timesheetPath"]
    entries, errors, options_map = load_file(timesheet_file)
    if not entries:
        raise Exception("Warning: No entries to file.")

    customers = dict(config["customers"])
    customer_entries = defaultdict(list)

    for entry in entries:
        if isinstance(entry, Transaction):
            cust_key = match_customer(entry, customers)
            if cust_key not in customers:
                new_cust = dict(btc.CUSTOMER_DEFAULTS)
                new_cust["code"] = generate_code(cust_key)
                new_cust["fullName"] = cust_key
                customers[cust_key] = new_cust
            customer_entries[cust_key].append(entry)

    print(f"Found {len(entries)} total entries.")

    for cust_key, cust in customers.items():
        period_entries = customer_entries.get(cust_key, [])
        if not period_entries:
            continue
        print(f"    {cust_key}: {len(period_entries)}")
        dates = [str(entry.date) for entry in period_entries]
        min_date = min(dates)
        max_date = max(dates)
        # Write period entries to archivePath
        period_file = format_path(cust["archivePath"], slug=cust_key, min_date=min_date, max_date=max_date, cust_key=cust_key, **cust )

        if dry_run:
            print(f"Would write period file: {period_file}\n---")
            print(render_entries(period_entries))
            print(f"--- End of {period_file}\n")
        else:
            write_file(period_file, render_entries(period_entries) + "\n", append=False)

        # Write summary to ledger
        summary = summary_transaction(period_entries, cust, cust_key, config, min_date, max_date)
        ledger = format_path(config["ledgerPath"],  slug=cust_key, min_date=min_date, max_date=max_date, cust_key=cust_key, **cust )
        if dry_run:
            print(f"Would append to {ledger}:\n---\n{summary}--- End of {ledger}\n")
        else:
            write_file(ledger, summary, append=True)


if __name__ == "__main__":
    typer.run(file_period)