
"""Invoice generation logic."""

import argparse
from html import parser
import yaml


def generate_invoice(beanfile, config, output_dir):
    """
    Generate an invoice (HTML/PDF) from a Beancount file.
    Args:
        beanfile (str): Path to the Beancount file for the period.
        config (dict): Invoice/customer configuration.
        output_dir (str): Directory to save the invoice files.
    """
    # TODO: Implement logic
    pass


def generate_invoice_cli():
    parser = argparse.ArgumentParser(description="Generate invoice from a Beancount file.")
    parser.add_argument("beanfile", help="Beancount file for the period")
    parser.add_argument("config", help="YAML config file for invoice/customer")
    parser.add_argument("output_dir", help="Directory to save invoice files")
    args = parser.parse_args()
    with open(args.config) as f:
        config = yaml.safe_load(f)
    generate_invoice(args.beanfile, config, args.output_dir)
