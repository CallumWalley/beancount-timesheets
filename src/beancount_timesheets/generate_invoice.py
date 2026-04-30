
"""Invoice generation logic."""

import argparse
from html import parser
import yaml



import os
import datetime as dt
import jinja2
import pdfkit
from beancount.loader import load_file

def generate_invoice(beanfile, config, output_dir):
    """
    Generate an invoice (HTML/PDF) from a Beancount file.
    Args:
        beanfile (str): Path to the Beancount file for the period.
        config (dict): Invoice/customer configuration.
        output_dir (str): Directory to save the invoice files.
    """
    # Load issuer and customer from config
    issuer = config["issuers"][next(iter(config["issuers"]))]
    customer = config["customers"][next(iter(config["customers"]))]

    # Setup Jinja2
    template_path = os.path.join(os.path.dirname(beanfile), config["invoice"]["templateFile"])
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

    # Invoice numbering
    from parse import compile as parse_compile
    lastInvoice = 0
    parser = parse_compile(customer["invoiceName"])
    invoice_dir = os.path.join(output_dir, customer["invoicePath"]) if not os.path.isabs(customer["invoicePath"]) else customer["invoicePath"]
    os.makedirs(invoice_dir, exist_ok=True)
    for i in os.listdir(invoice_dir):
        try:
            lastInvoice = max(parser.parse(i.split('.')[0])["invoiceNumber"], lastInvoice)
        except Exception:
            continue
    customer["invoiceNumber"] = lastInvoice + 1

    invoiceName = customer["invoiceName"].format(
        **customer, maxdate=maxdate, mindate=mindate, today=today
    )

    templateVars = {
        "title": config["invoice"].get("title", "INVOICE"),
        "issuer": issuer,
        "customer": customer,
        "dateFirst": mindate,
        "dateLast": maxdate,
        "dateIssue": today,
        "dateDue": (today + dt.timedelta(weeks=9)),
        "hourlyRate": config["invoice"].get("hourlyRate", 50),
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

    if config["invoice"].get("writeHTML", True):
        with open(os.path.join(invoice_dir, f"{invoiceName}.html"), "w+") as f:
            f.write(outputText)
    if config["invoice"].get("writePDF", True):
        pdfkit.from_string(
            outputText,
            os.path.join(invoice_dir, f"{invoiceName}.pdf"),
            options=options_pdf,
            verbose=True
        )


def generate_invoice_cli():
    parser = argparse.ArgumentParser(description="Generate invoice from a Beancount file.")
    parser.add_argument("beanfile", help="Beancount file for the period")
    parser.add_argument("config", help="YAML config file for invoice/customer")
    parser.add_argument("output_dir", help="Directory to save invoice files")
    args = parser.parse_args()
    with open(args.config) as f:
        config = yaml.safe_load(f)
    generate_invoice(args.beanfile, config, args.output_dir)
