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

## setup

You hould have an income account for each customer.

e.g. 

```
1900-01-01 open Assets:AccountsReceivable:ExampleCustomer
1900-01-01 open Income:ServicesRendered:ExampleCustomer
```


## Usage

### 1. Do work

### 2. Record work in current.beancount

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
- A new empty current.beancount will be made.

### 4. (Optional) Generate invoice

run `generate-invoice` will create a nice formatted invoice for you to send.

## CLI Usage

After installation, use the CLI:

```sh
python -m beancount_timesheets.cli <command> [options]
```

Or, if installed as a script:

```sh
beancount-timesheets <command> [options]
```






### Commands

- `file-period <current_file> <target_dir> <parent_record>`
	- Move unbilled entries to a new period file and update parent record.
- `generate-invoice <beanfile> <config> <output_dir>`
	- Generate invoice (HTML/PDF) from a Beancount file and config.




## Library Usage

```python
from beancount_timesheets import record_hours, file_period, generate_invoice
```

## For Plugin Authors

This package is designed to be Fava-agnostic and can be used as a backend for Fava plugins (e.g., fava-timesheets).