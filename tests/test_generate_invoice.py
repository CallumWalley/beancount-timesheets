import importlib
from pathlib import Path

generate_invoice_module = importlib.import_module("beancount_timesheets.generate_invoice")


def test_generate_invoice_numbers_per_customer_path_and_writes_multiple_suffixes(
	tmp_path,
	monkeypatch,
	template_factory,
	period_file_factory,
):
	template_path = tmp_path / "invoice_template.html"
	template_factory(template_path)

	output_dir = tmp_path / "output"
	output_dir.mkdir()
	existing_invoice = output_dir / "invoices" / "example" / "EC1.html"
	existing_invoice.parent.mkdir(parents=True)
	existing_invoice.write_text("existing")

	example_period = tmp_path / "example.beancount"
	second_period = tmp_path / "second.beancount"
	period_file_factory(example_period, "ExampleCustomer")
	period_file_factory(second_period, "SecondCustomer")

	pdf_outputs = []

	def fake_pdf(output_text, output_path, options, verbose):
		pdf_outputs.append(output_path)
		Path(output_path).write_text(output_text)

	monkeypatch.setattr(generate_invoice_module.pdfkit, "from_string", fake_pdf)

	config = {
		"fullName": "Callum Walley",
		"templatePath": str(template_path),
		"hourlyRate": 55,
		"customers": {
			"exampleCustomer": {
				"fullName": "ExampleCustomer",
				"code": "EC",
				"invoicePath": [
					"invoices/example/{code}{count}.html",
					"invoices/example/{code}{count}.pdf",
				],
				"hourlyRate": 100,
			},
			"secondCustomer": {
				"fullName": "SecondCustomer",
				"code": "SC",
				"invoicePath": ["invoices/second/{code}{count}.html"],
				"hourlyRate": 120,
			},
		},
	}

	generate_invoice_module.generate_invoice(str(example_period), config, str(output_dir))
	generate_invoice_module.generate_invoice(str(second_period), config, str(output_dir))

	assert (output_dir / "invoices" / "example" / "EC2.html").exists()
	assert (output_dir / "invoices" / "second" / "SC1.html").exists()
	assert pdf_outputs == [str(output_dir / "invoices" / "example" / "EC2.pdf")]


def test_generate_invoice_uses_suffix_to_choose_output_writer(
	tmp_path,
	monkeypatch,
	template_factory,
	period_file_factory,
):
	template_path = tmp_path / "invoice_template.html"
	template_factory(template_path)

	output_dir = tmp_path / "output"
	output_dir.mkdir()
	period_file = tmp_path / "example.beancount"
	period_file_factory(period_file, "ExampleCustomer")

	def fail_pdf(*_args, **_kwargs):
		raise AssertionError("pdf writer should not be called for html-only outputs")

	monkeypatch.setattr(generate_invoice_module.pdfkit, "from_string", fail_pdf)

	config = {
		"fullName": "Callum Walley",
		"templatePath": str(template_path),
		"hourlyRate": 55,
		"customers": {
			"exampleCustomer": {
				"fullName": "ExampleCustomer",
				"code": "EC",
				"invoicePath": "invoices/example/{code}{count}.html",
				"hourlyRate": 100,
			},
		},
	}

	generate_invoice_module.generate_invoice(str(period_file), config, str(output_dir))

	assert (output_dir / "invoices" / "example" / "EC1.html").exists()
