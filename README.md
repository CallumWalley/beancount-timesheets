# beancount-timesheets

Core logic for time tracking, period filing, and invoice generation for Beancount users.

## Features
- Record hours and append to Beancount files
- File periods (move entries, create new files)
- Generate invoices (HTML/PDF) from Beancount data based on 
- CLI

## Installation

```sh
pip install beancount-timesheets
```

## From repo

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## setup

You hould have an income and a receivable account for each customer.

e.g. 

```bean
1900-01-01 open Assets:AccountsReceivable:ExampleCustomer
1900-01-01 open Income:ServicesRendered:ExampleCustomer
```


## Usage

### 1. Do work

### 2. Record work in `timesheet.beancount`

For example

```bean
2023-03-31 * "1000 1030" "What you were doing"
    Income:HOURS:Uninvoiced:ExampleCustomer   0.5 HOURS
    Income:HoursWorked
```

### 3. At the end of the month (or billing period)

run `file-period`.

This will do a few things.

- All hours worked entries will be seperated by customer and filed away.
- An 'accountsRecivable` entry will be added for each customer.
- A new empty timesheet.beancount will be made.

### 4. (Optional) Generate invoice

run `generate-invoice` will create a nice formatted invoice for you to send.

### Commands

- `file-period <timesheet_file> <target_dir> <parent_record>`
	- Move unbilled entries to a new period file and update parent record.
- `generate-invoice <beanfile> <config> <output_dir>`
	- Generate invoice (HTML/PDF) from a Beancount file and config.

## Library Usage

```python
from beancount_timesheets import record_hours, file_period, generate_invoice
```

## For Plugin Authors

This package is designed to be Fava-agnostic and can be used as a backend for Fava plugins (e.g., fava-timesheets).

## Testing

Automated tests are provided using [pytest](https://pytest.org/). Tests cover:
- Timesheet processing and file creation
- Timesheet reset after processing
- Dry run mode (no file changes, output only)
- Edge cases (new customers, error handling, etc.)

To run the tests:

```sh
pip install pytest
pytest tests/
```

See `tests/test_file_period.py` for example test cases and usage.
