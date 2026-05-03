import glob
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unicodedata
import os
from datetime import date
from beancount.core.data import Transaction
from beancount.parser import printer
import yaml
from pathlib import Path


_REPORTER = None
_SKIP_WRITE_PROMPT = False


def set_write_approval(skip_prompt=False):
    global _SKIP_WRITE_PROMPT
    _SKIP_WRITE_PROMPT = skip_prompt


def set_reporter(reporter):
    global _REPORTER
    _REPORTER = reporter


def emit(level, message):
    if _REPORTER is not None:
        _REPORTER(level, message)
    print(f"{level.capitalize()}: {message}")


def emit_warning(message):
    emit("warning", message)


def emit_info(message):
    emit("info", message)

DEFAULT_TIMESHEET = """; Example transaction
;2023-03-31 * "1000 1030" "What you were doing"
;    Income:HOURS:Uninvoiced:ExampleCustomer   0.5 HOURS
;    Income:HoursWorked
"""

DEFAULT_CONFIG = {
    "customers": None,
    "fullName": "Issuer",
    "ledgerPath": "invoice.beancount",                                  # Where to record generated invoices.
    "timesheetPath": "timesheet.beancount",                             # Where to read timesheet from.
    "hourlyRate": 50,
    "gstRate": 0.15
}

DEFAULT_CUSTOMER = {
    "fullName": None, 
    "invoiceKey": "{code}{count}",                                      # Unique key for this invoice.
    "invoicePath": "invoices/slug/{invoiceKey}.pdf",                        # Where to file invoices. Can be multiple.
    "archivePath": "archive/{slug}/{min_date}_{max_date}.beancount",    # Where to file timesheets that have been proccssed
    "hourlyRate": DEFAULT_CONFIG["hourlyRate"],
    "code": None,
    # 'slug' and 'code' can be generated from the key
}


def path_safe(value):
    """Make a string safe for use in file paths."""
    value = str(value)
    value = unicodedata.normalize('NFKD', value)
    value = re.sub(r'[\s/\\:;"\'<>|?*]', '_', value)
    value = re.sub(r'[^\w.-]', '', value)
    value = value.strip('._')
    return value or 'X'

class SafeDict(dict):
    def __missing__(self, key):
        return ''

def format_path(template, **kwargs):
    """
    Format a path template string with all relevant info, then make the final result path safe.
    Always includes all provided values, so any template can use any field.
    """
    result = template.format_map(SafeDict(kwargs))
    is_absolute = os.path.isabs(result)
    # Normalize all slashes to os.sep for splitting
    parts = [p for p in result.split(os.sep) if p != '']
    safe_parts = [path_safe(part) for part in parts]
    formatted = os.sep.join(safe_parts)
    if is_absolute:
        return os.sep + formatted
    return formatted

def write_file(path, content, append=False):
    """
    Write content to a file, creating directories as needed.
    If append is True, append to the file if it exists; otherwise, throw error file exists.
    """
    dirpart = os.path.dirname(path)
    if dirpart:
        os.makedirs(dirpart, exist_ok=True)

    reviewed_content = review_write(path, content)
    if reviewed_content is None:
        emit_info(f"Skipped write to {path}.")
        return False

    try:
        with open(path, 'a' if append else 'x') as f:
            f.write(reviewed_content)
    except FileExistsError:
        if not append:
            raise
    return True


def overwrite_file(path, content):
    """Overwrite a file after optional editor review/approval."""
    dirpart = os.path.dirname(path)
    if dirpart:
        os.makedirs(dirpart, exist_ok=True)

    reviewed_content = review_write(path, content)
    if reviewed_content is None:
        emit_info(f"Skipped write to {path}.")
        return False

    with open(path, "w") as f:
        f.write(reviewed_content)
    return True


def review_write(path, content):
    """
    Allow the user to review proposed file contents in $EDITOR and approve.
    Returns approved content, or None if declined.
    """
    if _SKIP_WRITE_PROMPT or not sys.stdin.isatty() or not sys.stdout.isatty():
        return content

    editor = os.environ.get("EDITOR", "vi")
    tmp_path = None
    try:
        suffix = os.path.splitext(path)[1] or ".tmp"
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name

        command = shlex.split(editor) + [tmp_path]
        subprocess.run(command, check=True)

        with open(tmp_path) as tmp:
            reviewed_content = tmp.read()

        answer = input(f"Approve write to {path}? [y/N]: ").strip().lower()
        if answer in {"y", "yes"}:
            return reviewed_content
        return None
    except (OSError, subprocess.CalledProcessError) as err:
        emit_warning(f"Editor review failed ({err}); skipping write to '{path}'.")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

def generate_code(cust_key):
    # Normalize underscores and hyphens to spaces, then split on capital boundaries
    words = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])', re.sub(r'[_-]', ' ', cust_key))
    code = ''.join(word[0] for word in words[:-1]) + words[-1]
    return code[:3].upper()

def ledger_transaction(entries, cust, cust_key, config, min_date, max_date):
    invoice_code =  cust_key + max_date.replace('-', '')
    hours = sum(
        float(m.group(1))
        for entry in entries if isinstance(entry, Transaction)
        for posting in entry.postings
        for m in [re.search(r"([\d.]+) HOURS", entry.narration)] if m
    )
    hourly_rate = cust["hourlyRate"] if cust["hourlyRate"] is not None else config["hourlyRate"]
    gross_income = hourly_rate * hours
    gst = gross_income * config["gstRate"]
    account_payable = f"Income:ServicesRendered:{cust_key}"
    account_payable_gst = "Liabilities:AccountsPayable:IRD"
    account_receivable = f"Assets:AccountsReceivable:{cust_key}"
    return (
        f"{date.today().strftime('%Y-%m-%d')} * \"{invoice_code}\" ^{invoice_code}\n"
        f"    {account_payable.ljust(60)} -{gross_income} NZD ; {hours} HOURS @ {hourly_rate} NZD\n"
        f"    {account_payable_gst.ljust(60)} -{gst} NZD\n"
        f"    {account_receivable}\n"
    )

def render_entries(entries):
    return "\n".join(printer.format_entry(e) for e in entries)

def match_customer(entry, customers):
    for key, cust in customers.items():
        pattern = re.compile(rf"Income:HOURS:Uninvoiced:({re.escape(cust['fullName'])}|{re.escape(cust.get('code',''))})")
        if any(pattern.search(posting.account) for posting in entry.postings):
            return key
    for posting in entry.postings:
        m = re.match(r"Income:HOURS:Uninvoiced:([\w]+)", posting.account)
        if m:
            return m.group(1)
    return None

def resolve_config_path(config_dir, value):
    if value is None:
        return value
    if isinstance(value, list):
        return [resolve_config_path(config_dir, item) for item in value]
    if os.path.isabs(value):
        return value
    return os.path.join(config_dir, value)

def parse_config(config_path):
    # Load config and fill sensible defaults
    with open(config_path) as f:
        config = yaml.safe_load(f)

    config_dir = os.path.dirname(os.path.abspath(config_path))


    set_default(config, DEFAULT_CONFIG, "config")

    if "customers" not in config or not config["customers"]:
        config["customers"] = {"default": {k: v for k, v in DEFAULT_CUSTOMER.items() if v is not None}}

    # Use the dictionary key as the canonical slug/identifier
    new_customers = {}
    for key, cust in config["customers"].items():
        set_default(cust, DEFAULT_CUSTOMER, f"customer '{key}'")
        # Generate slug and code from key
        cust["code"] = key.upper()
        # If fullName is missing, use slug as fallback
        if not cust.get("fullName"):
            cust["fullName"] = key
        cust["archivePath"] = resolve_config_path(config_dir, cust["archivePath"])
        cust["invoicePath"] = resolve_config_path(config_dir, cust["invoicePath"])
        new_customers[key] = cust
    config["customers"] = new_customers

    config["ledgerPath"] = resolve_config_path(config_dir, config["ledgerPath"])
    config["timesheetPath"] = resolve_config_path(config_dir, config["timesheetPath"])

    return config

def set_default(obj, defaults, context="config"):
    for k in obj.keys():
        if k not in defaults:
            emit_warning(f"Unrecognized {context} key: '{k}'")
    for k, v in defaults.items():
        if k not in obj or obj[k] is None:
            emit_info(f"Using default for '{k}': {v!r}")
            obj[k] = v

def read_timesheet(timesheet):
    path = Path(timesheet)
    if not path.exists():
        emit_warning(f"{timesheet} does not exist. Creating '{timesheet}'.")
        path.write_text(DEFAULT_TIMESHEET)
    return path.read_text().splitlines(keepends=True)

def get_next_count(path_pattern, **variables):
    """
    Given a path pattern (e.g. './invoices/{code}{count}.pdf'), return the next count integer to use.
    All variable fields (e.g. {count}, {min_date}, {max_date}, etc.) are wildcarded for globbing, except those provided in variables.
    """
    # Find all {var} in the pattern
    var_fields = re.findall(r'\{(\w+)\}', path_pattern)
    glob_pattern = path_pattern
    regex_pat = re.escape(path_pattern)
    for var in var_fields:
        if var == 'count':
            glob_pattern = glob_pattern.replace(f'{{{var}}}', '*')
            regex_pat = regex_pat.replace(rf'\{{{var}\}}', r'(\\d+)')
        elif var in variables:
            val = str(variables[var])
            glob_pattern = glob_pattern.replace(f'{{{var}}}', val)
            regex_pat = regex_pat.replace(re.escape(f'{{{var}}}'), re.escape(val))
        else:
            glob_pattern = glob_pattern.replace(f'{{{var}}}', '*')
            regex_pat = regex_pat.replace(re.escape(f'{{{var}}}'), r'.*')
    files = glob.glob(glob_pattern)
    counts = []
    for f in files:
        m = re.search(regex_pat, f)
        if m:
            try:
                counts.append(int(m.group(1)))
            except Exception:
                pass
    if counts:
        return max(counts) + 1
    return 1