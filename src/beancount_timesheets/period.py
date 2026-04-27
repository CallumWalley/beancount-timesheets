import yaml
import re
import sys
import os
from datetime import date
import argparse

def parse_config(config_path):
    # Load config and fill sensible defaults
    with open(config_path) as f:
        config = yaml.safe_load(f)
    # Sensible defaults
    if "customers" not in config or not config["customers"]:
        config["customers"] = {"default": {"code": "CUST", "fullName": "Customer", "invoicePath": "./invoices/Customer/", "slug": "Customer"}}
    for cust in config["customers"].values():
        cust.setdefault("code", "CUST")
        cust.setdefault("fullName", "Customer")
        cust.setdefault("invoicePath", "./invoices/Customer/")
        cust.setdefault("slug", cust["fullName"].replace(" ", ""))
        cust.setdefault("periodFileName", "{slug}_{min_date}_{max_date}.beancount")
        cust.setdefault("periodDir", "./periods/")
    # Top-level issuer defaults
    config.setdefault("fullName", "Issuer")
    config.setdefault("parentRecord", "invoice.beancount")
    config.setdefault("hourlyRate", 0)
    return config

def file_period(current_file, parent_record=None, config_path=None, dry_run=False):
    config_path = config_path or os.path.join(os.path.dirname(current_file), "config.yml")
    config = parse_config(config_path)
    customer_key = next(iter(config["customers"]))
    customer = config["customers"][customer_key]
    # Use config values if not provided
    target_dir = customer.get("periodDir", "./periods/")
    parent_record = parent_record or customer.get("parentRecord", "invoice.beancount")
    # Use customer hourlyRate if present, else global
    hourly_rate = customer.get("hourlyRate", config.get("hourlyRate", 0))
    # Read all entries from current_file
    with open(current_file) as f:
        lines = f.readlines()

    # Parse entries (simple block split by blank line or line starting with date)
    entries = []
    entry = []
    for line in lines:
        if re.match(r"^\d{4}-\d{2}-\d{2} ", line) and entry:
            entries.append(entry)
            entry = [line]
        else:
            entry.append(line)
    if entry:
        entries.append(entry)

    # Filter entries with Income:HOURS:Uninvoiced:<Customer>
    customer_account = f"Income:HOURS:Uninvoiced:{customer['fullName'].replace(' ', '')}"
    # Accept either fullName or code as suffix
    account_pattern = re.compile(rf"Income:HOURS:Uninvoiced:({re.escape(customer['fullName'])}|{re.escape(customer.get('code',''))})")
    period_entries = []
    remaining_entries = []
    for entry in entries:
        entry_str = ''.join(entry)
        if account_pattern.search(entry_str):
            period_entries.append(entry)
        else:
            remaining_entries.append(entry)

    # Determine min/max date
    dates = []
    for entry in period_entries:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", entry[0])
        if m:
            dates.append(m.group(1))
    if not dates:
        raise Exception("No matching entries to file.")
    min_date = min(dates)
    max_date = max(dates)

    # Determine period file name
    period_name_fmt = customer.get("periodFileName", "{slug}_{min_date}_{max_date}.beancount")
    slug = customer.get("slug") or customer['fullName'].replace(' ', '')
    period_file = os.path.join(target_dir, period_name_fmt.format(slug=slug, min_date=min_date, max_date=max_date))

    # Write period file
    if dry_run:
        print(f"Would write period file: {period_file}\n---")
        for entry in period_entries:
            sys.stdout.writelines(entry)
            if entry[-1][-1] != '\n':
                print()
        print(f"--- End of {period_file}\n")
    else:
        with open(period_file, "w") as f:
            for entry in period_entries:
                f.writelines(entry)
                if entry[-1][-1] != '\n':
                    f.write('\n')

    # Write remaining entries back to current_file
    if dry_run:
        print(f"Would write remaining entries to {current_file}\n---")
        for entry in remaining_entries:
            sys.stdout.writelines(entry)
            if entry[-1][-1] != '\n':
                print()
        print(f"--- End of {current_file}\n")
    else:
        with open(current_file, "w") as f:
            for entry in remaining_entries:
                f.writelines(entry)
                if entry[-1][-1] != '\n':
                    f.write('\n')

    # Update parent_record with summary transaction
    invoice_code = customer.get("code", slug) + max_date.replace('-', '')
    hours = sum(float(re.search(r"([\d.]+) HOURS", ''.join(e)).group(1)) for e in period_entries if re.search(r"([\d.]+) HOURS", ''.join(e)))
    gross_income = hourly_rate * hours
    gst = gross_income * 0.15
    account_payable = f"Income:ServicesRendered:{slug}"
    account_payable_gst = "Liabilities:AccountsPayable:IRD"
    account_receivable = f"Assets:AccountsReceivable:{slug}"
    summary = (
        f"{date.today().strftime('%Y-%m-%d')} * \"{invoice_code}\" ^{invoice_code}\n"
        f"    {account_payable.ljust(60)} -{gross_income} NZD ; {hours} HOURS @ {hourly_rate} NZD\n"
        f"    {account_payable_gst.ljust(60)} -{gst} NZD\n"
        f"    {account_receivable}\n"
    )
    if dry_run:
        print(f"Would append to {parent_record}:\n---\n{summary}--- End of {parent_record}\n")
    else:
        with open(parent_record, "a") as f:
            f.write(summary)

# CLI

def cli():
    parser = argparse.ArgumentParser(description="File period entries to a new file.")
    parser.add_argument("-c", "--config", default=None, help="Path to config.yml (default: ./config.yml next to current file)")
    parser.add_argument("-f", "--current-file", default="current.beancount", help="Current Beancount file (default: current.beancount)")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Print changes instead of writing to files")
    parser.add_argument("--parent-record", default=None, help="Override parent record file (default: from config)")
    args = parser.parse_args()
    config_path = args.config or os.path.join(os.path.dirname(args.current_file), "config.yml")
    file_period(args.current_file, parent_record=args.parent_record, config_path=config_path, dry_run=args.dry_run)