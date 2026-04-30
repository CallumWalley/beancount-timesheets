import tempfile
import os
import shutil
from beancount_timesheets import generate_invoice

# def test_generate_invoice():
#     example_dir = os.path.join(os.path.dirname(__file__), "../example")
#     period_path = os.path.join(example_dir, "-04-01_2026-04-27.beancount")
#     config_path = os.path.join(example_dir, "config.yml")
#     template_path = os.path.join(example_dir, "invoice_template.html")
#     with tempfile.TemporaryDirectory() as tmpdir:
#         output_path = os.path.join(tmpdir, "invoice.html")
#         generate_invoice(
#             period_file=period_path,
#             config_file=config_path,
#             template_file=template_path,
#             output_file=output_path
#         )
#         with open(output_path) as f:
#             html = f.read()
#         assert "" in html
