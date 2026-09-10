from __future__ import annotations

import html
import json
from pathlib import Path


class Reporter:

    def __init__(self, output_dir):

        self.output_dir = Path(output_dir)

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def generate(
        self,
        run_id: int,
        results: list[dict]
    ):

        total = len(results)

        passed = sum(
            1
            for r in results
            if r["status"] == "PASS"
        )

        failed = total - passed

        pass_rate = (
            round(
                (passed / total) * 100,
                2
            )
            if total
            else 0
        )

        report = {
            "run_id": run_id,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "tests": results
        }

        json_path = (
            self.output_dir /
            "test-report.json"
        )

        html_path = (
            self.output_dir /
            "test-report.html"
        )

        with open(
            json_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=2,
                ensure_ascii=False
            )

        rows = []

        for test in results:

            status = html.escape(
                test.get("status", "")
            )

            css = (
                "pass"
                if status == "PASS"
                else "fail"
            )

            rows.append(
                f"""
                <tr>
                    <td>{html.escape(str(test.get("id", "")))}</td>
                    <td>{html.escape(str(test.get("test_name", "")))}</td>
                    <td class="{css}">{status}</td>
                    <td>{test.get("attempt", "")}</td>
                    <td>{test.get("duration", "")}</td>
                    <td>{html.escape(str(test.get("reason", "")))}</td>
                </tr>
                """
            )

        html_content = f"""
<!DOCTYPE html>
<html>
<head>

<meta charset="UTF-8">

<title>AI Playwright Test Report</title>

<style>

body {{
    font-family: Arial, sans-serif;
    margin: 40px;
}}

.summary {{
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
}}

.card {{
    padding: 20px;
    border: 1px solid #ddd;
    border-radius: 8px;
}}

table {{
    border-collapse: collapse;
    width: 100%;
}}

th, td {{
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
}}

th {{
    background: #f5f5f5;
}}

.pass {{
    color: green;
    font-weight: bold;
}}

.fail {{
    color: red;
    font-weight: bold;
}}

</style>

</head>

<body>

<h1>AI Playwright Test Report</h1>

<div class="summary">

<div class="card">
<strong>Total</strong><br>
{total}
</div>

<div class="card">
<strong>Passed</strong><br>
{passed}
</div>

<div class="card">
<strong>Failed</strong><br>
{failed}
</div>

<div class="card">
<strong>Pass Rate</strong><br>
{pass_rate}%
</div>

</div>

<table>

<thead>
<tr>
<th>ID</th>
<th>Test</th>
<th>Status</th>
<th>Attempt</th>
<th>Duration</th>
<th>Reason</th>
</tr>
</thead>

<tbody>

{"".join(rows)}

</tbody>

</table>

</body>
</html>
"""

        with open(
            html_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(html_content)

        return {
            "json": str(json_path),
            "html": str(html_path)
        }