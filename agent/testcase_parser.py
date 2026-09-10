from __future__ import annotations

import json
import re
from typing import Any, Dict, List


class TestCaseParser:
    """
    Converts different test case representations into
    a normalized structure.
    """

    REQUIRED_FIELDS = {
        "id",
        "name",
        "url",
        "steps",
        "expected"
    }

    def parse_json(
        self,
        test_case_json: str
    ) -> List[Dict[str, Any]]:
        """
        Parse JSON containing one or more test cases.
        """

        try:
            data = json.loads(test_case_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON test case: {exc}"
            ) from exc

        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            raise ValueError(
                "Test cases must be a JSON object or array."
            )

        normalized = []

        for index, test_case in enumerate(data, start=1):

            normalized.append(
                self.normalize(
                    test_case,
                    default_id=f"TC{index:03d}"
                )
            )

        return normalized

    def parse_text(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """
        Parse a simple natural-language test case.

        Example:

        Test: Login

        URL:
        https://example.com/login

        Steps:
        1. Enter username test@example.com
        2. Enter password Password123
        3. Click Login

        Expected:
        Dashboard should be displayed
        """

        test_name = self._extract_section(
            text,
            ["Test", "Name"]
        )

        url = self._extract_url(text)

        steps = self._extract_steps(text)

        expected = self._extract_expected(text)

        if not url:
            raise ValueError(
                "Could not find a URL in the test case."
            )

        if not steps:
            raise ValueError(
                "Could not find test steps."
            )

        if not expected:
            raise ValueError(
                "Could not find expected results."
            )

        return [
            {
                "id": "TC001",
                "name": test_name or "Unnamed Test",
                "url": url,
                "steps": steps,
                "expected": expected
            }
        ]

    def normalize(
        self,
        test_case: Dict[str, Any],
        default_id: str = "TC001"
    ) -> Dict[str, Any]:
        """
        Normalize and validate a test case.
        """

        test_case = dict(test_case)

        test_case.setdefault(
            "id",
            default_id
        )

        test_case.setdefault(
            "name",
            "Unnamed Test"
        )

        test_case.setdefault(
            "steps",
            []
        )

        test_case.setdefault(
            "expected",
            []
        )

        if not test_case.get("url"):
            raise ValueError(
                f"{test_case['id']} is missing URL."
            )

        if not isinstance(
            test_case["steps"],
            list
        ):
            raise ValueError(
                f"{test_case['id']} steps must be a list."
            )

        if not isinstance(
            test_case["expected"],
            list
        ):
            raise ValueError(
                f"{test_case['id']} expected must be a list."
            )

        return test_case

    def _extract_url(
        self,
        text: str
    ) -> str | None:

        match = re.search(
            r"https?://[^\s]+",
            text
        )

        return match.group(0) if match else None

    def _extract_section(
        self,
        text: str,
        headers: List[str]
    ) -> str | None:

        for header in headers:

            pattern = (
                rf"{header}\s*:\s*(.+)"
            )

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:
                return match.group(1).strip()

        return None

    def _extract_steps(
        self,
        text: str
    ) -> List[str]:

        match = re.search(
            r"Steps\s*:(.*?)(?:Expected\s*:|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            return []

        block = match.group(1)

        lines = block.splitlines()

        steps = []

        for line in lines:

            line = line.strip()

            line = re.sub(
                r"^\d+[\.\)]\s*",
                "",
                line
            )

            if line:
                steps.append(line)

        return steps

    def _extract_expected(
        self,
        text: str
    ) -> List[str]:

        match = re.search(
            r"Expected\s*:(.*)$",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            return []

        block = match.group(1)

        lines = block.splitlines()

        expected = []

        for line in lines:

            line = line.strip()

            line = re.sub(
                r"^[\-\*\d\.]+\s*",
                "",
                line
            )

            if line:
                expected.append(line)

        return expected