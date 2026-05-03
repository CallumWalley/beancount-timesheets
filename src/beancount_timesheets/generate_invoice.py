
"""Invoice generation logic."""

import argparse
import datetime as dt
import glob
import os
import re
from pathlib import Path

import jinja2
import pdfkit
import yaml
from beancount.core.data import Transaction
from beancount.loader import load_file

import beancount_timesheets.core as core


def _resolve_output_path(path_template, output_dir, **variables):
    formatted = core.format_path(path_template, **variables)
    if os.path.isabs(formatted):
        return formatted
    return os.path.join(output_dir, formatted)


def _next_invoice_count(path_template, output_dir, **variables):
    marker = "COUNTMARKER"
    stem_template, _suffix = os.path.splitext(path_template)
    stem_pattern = _resolve_output_path(
        stem_template,
        output_dir,
        count=marker,
        **variables,
    )
    glob_pattern = stem_pattern.replace(marker, "*") + ".*"
    regex = re.compile(re.escape(stem_pattern).replace(marker, r"(\d+)") + r"\.[^.]+$")

    counts = []
    for existing_path in glob.glob(glob_pattern):
        match = regex.match(existing_path)
        if match:
            counts.append(int(match.group(1)))

    return max(counts, default=0) + 1


def _select_issuer(config):
    if config.get("issuers"):
        return dict(config["issuers"][next(iter(config["issuers"]))])
    return {k: v for k, v in config.items() if k != "customers"}


def _select_customer(entries, config):
    customers = config["customers"]
    for entry in entries:
        if isinstance(entry, Transaction):
            cust_key = core.match_customer(entry, customers)
            if cust_key in customers:
                customer = dict(customers[cust_key])
                return cust_key, customer

    fallback_key = next(iter(customers))
    return fallback_key, dict(customers[fallback_key])


def _get_template_path(beanfile, output_dir, config):
    if config.get("invoice", {}).get("templateFile"):
        template_file = config["invoice"]["templateFile"]
        if os.path.isabs(template_file):
            return template_file
        return os.path.join(os.path.dirname(beanfile), template_file)

    template_path = config.get("templatePath", "invoice_template.html")
    if os.path.isabs(template_path):
        return template_path

    output_candidate = os.path.join(output_dir, template_path)
    if os.path.exists(output_candidate):
        return output_candidate
    return os.path.join(os.path.dirname(beanfile), template_path)

def generate_invoice(beanfile, config, output_dir):
    """
    Generate an invoice (HTML/PDF) from a Beancount file.
    Args:
        beanfile (str): Path to the Beancount file for the period.
        config (dict): Invoice/customer configuration.
        output_dir (str): Directory to save the invoice files.
    """
    issuer = _select_issuer(config)

    # Setup Jinja2
    template_path = _get_template_path(beanfile, output_dir, config)
    templateLoader = jinja2.FileSystemLoader(searchpath=os.path.dirname(template_path))
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(os.path.basename(template_path))

    entries, errors, options = load_file(beanfile)
    print(f"Invoicing for {len(entries)} entries.")

    today = dt.date.today()
    mindate = dt.date.max
    maxdate = dt.date.min
    entries_labour = []
    entries_other = []

    for _entry in entries:
        if not hasattr(_entry, 'postings') or not _entry.postings:
            continue
        posting = _entry.postings[0]
        entry = posting._asdict()
        entry["date"] = getattr(_entry, "date", None)
        entry["narration"] = getattr(_entry, "narration", "")
        if entry["units"][1] == "HOURS":
            entries_labour.append(entry)
        else:
            entries_other.append(entry)
        if entry["date"]:
            mindate = min(mindate, entry["date"])
            maxdate = max(maxdate, entry["date"])

    cust_key, customer = _select_customer(entries, config)
    customer.setdefault("code", cust_key.upper())
    customer.setdefault("fullName", cust_key)
    customer.setdefault("hourlyRate", config.get("hourlyRate", 50))

    invoice_paths = customer["invoicePath"]
    if not isinstance(invoice_paths, list):
        invoice_paths = [invoice_paths]

    invoice_count = _next_invoice_count(
        invoice_paths[0],
        output_dir,
        code=customer["code"],
        slug=cust_key,
        min_date=mindate,
        max_date=maxdate,
        today=today,
    )
    customer["invoiceNumber"] = invoice_count

    output_variables = {
        **customer,
        "count": invoice_count,
        "slug": cust_key,
        "min_date": mindate,
        "max_date": maxdate,
        "today": today,
    }

    templateVars = {
        "title": config.get("invoice", {}).get("title", "INVOICE"),
        "companyName": issuer.get("fullName", ""),
        "issuer": issuer,
        "customer": customer,
        "dateFirst": mindate,
        "dateLast": maxdate,
        "dateIssue": today,
        "dateDue": (today + dt.timedelta(weeks=9)),
        "hourlyRate": customer.get("hourlyRate", config.get("hourlyRate", 50)),
        "entriesLabour": entries_labour,
        "entriesOther": entries_other,
    }

    outputText = template.render(templateVars)
    options_pdf = {
        "enable-local-file-access": True,
        "margin-top": "0px",
        "margin-left": "0px",
        "margin-right": "0px",
        "margin-bottom": "0px",
        "no-outline": None
    }

    for invoice_path in invoice_paths:
        rendered_path = _resolve_output_path(invoice_path, output_dir, **output_variables)
        os.makedirs(os.path.dirname(rendered_path), exist_ok=True)
        suffix = Path(rendered_path).suffix.lower()

        if suffix == ".html":
            with open(rendered_path, "w+") as f:
                f.write(outputText)
        elif suffix == ".pdf":
            pdfkit.from_string(
                outputText,
                rendered_path,
                options=options_pdf,
                verbose=True,
            )
        else:
            raise ValueError(f"Unsupported invoice output type: {suffix}")


def main():
    parser = argparse.ArgumentParser(description="Generate invoice from a Beancount file.")
    parser.add_argument("beanfile", help="Beancount file for the period")
    parser.add_argument("config", help="YAML config file for invoice/customer")
    parser.add_argument("output_dir", help="Directory to save invoice files")
    args = parser.parse_args()
    with open(args.config) as f:
        config = yaml.safe_load(f)
    generate_invoice(args.beanfile, config, args.output_dir)


if __name__ == "__main__":
    main()
