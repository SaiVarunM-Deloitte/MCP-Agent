from __future__ import annotations

import json
import time
from typing import Any

from openai import AsyncOpenAI


SYSTEM_PROMPT = """
You are an autonomous web application QA test agent.

You execute user-provided test cases using Playwright MCP tools.

IMPORTANT RULES:

1. Always inspect the page using browser_snapshot before
   deciding how to interact with it.

2. Use exact element references from the latest snapshot
   when calling browser_click, browser_type, etc.

3. Never invent element references.

4. Follow the test steps in order.

5. You may adapt to small UI changes when the intended action
   is unambiguous.

6. Validate the expected result after completing the steps.

7. Do not declare PASS merely because an action succeeded.
   PASS means the expected application behavior was actually observed.

8. If a test cannot satisfy its expected result, mark it FAILED.

9. At the end, return ONLY this JSON:

{
  "status": "PASS" or "FAILED",
  "reason": "brief explanation",
  "evidence": [
    "observable evidence 1",
    "observable evidence 2"
  ]
}
"""


class TestAgent:

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        executor,
        memory,
        model: str,
        max_steps: int = 30
    ):

        self.client = openai_client
        self.executor = executor
        self.memory = memory
        self.model = model
        self.max_steps = max_steps

    # =====================================================
    # MCP → OPENAI TOOL FORMAT
    # =====================================================

    async def build_tools(self):

        mcp_tools = await self.executor.list_tools()

        tools = []

        for tool in mcp_tools:

            schema = tool.inputSchema or {
                "type": "object",
                "properties": {}
            }

            tools.append(
                {
                    "type": "function",
                    "name": tool.name,
                    "description": (
                        tool.description
                        or tool.name
                    ),
                    "parameters": schema
                }
            )

        return tools

    # =====================================================
    # CONVERT MCP RESULT
    # =====================================================

    @staticmethod
    def serialize_mcp_result(result: Any) -> str:

        # MCP result commonly has .content
        if hasattr(result, "content"):

            output = []

            for item in result.content:

                if hasattr(item, "text"):
                    output.append(item.text)

                elif hasattr(item, "model_dump"):
                    output.append(
                        json.dumps(
                            item.model_dump(),
                            default=str
                        )
                    )

                else:
                    output.append(str(item))

            return "\n".join(output)

        if hasattr(result, "model_dump"):

            return json.dumps(
                result.model_dump(),
                default=str
            )

        return str(result)

    # =====================================================
    # TEST EXECUTION
    # =====================================================

    async def run_test(
        self,
        run_id: int,
        test_case: dict,
        attempt: int
    ):

        test_id = test_case["id"]

        print()
        print("=" * 60)
        print(
            f"{test_id} | "
            f"{test_case['name']} | "
            f"Attempt {attempt}"
        )
        print("=" * 60)

        start_time = time.perf_counter()

        try:

            history = self.memory.get_test_history(
                test_id
            )

            history_text = self._format_history(
                history
            )

            test_text = json.dumps(
                test_case,
                indent=2,
                ensure_ascii=False
            )

            user_prompt = f"""
Execute this QA test case.

TEST CASE:

{test_text}

PREVIOUS TEST HISTORY:

{history_text}

Use the Playwright MCP tools to execute the test.

When execution is complete, return the required JSON result.
"""

            tools = await self.build_tools()

            # Responses API input
            conversation = [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]

            result = None

            for step in range(self.max_steps):

                print(
                    f"\n[AI] Agent iteration "
                    f"{step + 1}"
                )

                response = await self.client.responses.create(
                    model=self.model,
                    instructions=SYSTEM_PROMPT,
                    input=conversation,
                    tools=tools
                )

                function_calls = [
                    item
                    for item in response.output
                    if item.type == "function_call"
                ]

                # -----------------------------------------
                # Model finished
                # -----------------------------------------

                if not function_calls:

                    result = self._parse_final_result(
                        response.output_text
                    )

                    break

                # -----------------------------------------
                # Execute MCP tools
                # -----------------------------------------

                # Keep the model's output in the next turn.
                conversation.extend(
                    response.output
                )

                for call in function_calls:

                    try:

                        arguments = json.loads(
                            call.arguments
                        )

                    except json.JSONDecodeError:

                        arguments = {}

                    try:

                        mcp_result = (
                            await self.executor.call_tool(
                                call.name,
                                arguments
                            )
                        )

                        tool_output = (
                            self.serialize_mcp_result(
                                mcp_result
                            )
                        )

                    except Exception as exc:

                        tool_output = json.dumps(
                            {
                                "error": str(exc)
                            }
                        )

                    conversation.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": tool_output
                        }
                    )

            else:

                result = {
                    "status": "FAILED",
                    "reason": (
                        "Maximum AI agent steps exceeded"
                    ),
                    "evidence": []
                }

            duration = (
                time.perf_counter()
                - start_time
            )

            status = result["status"]

            self.memory.save_result(
                run_id=run_id,
                test_id=test_id,
                test_name=test_case["name"],
                attempt=attempt,
                status=status,
                reason=result.get("reason"),
                evidence=result.get("evidence"),
                duration=duration
            )

            print(
                f"\nRESULT: {status}"
            )

            return {
                **result,
                "attempt": attempt,
                "duration": duration
            }

        except Exception as exc:

            duration = (
                time.perf_counter()
                - start_time
            )

            error_result = {
                "status": "FAILED",
                "reason": "Agent execution error",
                "evidence": [],
                "error": str(exc)
            }

            self.memory.save_result(
                run_id=run_id,
                test_id=test_id,
                test_name=test_case["name"],
                attempt=attempt,
                status="FAILED",
                reason="Agent execution error",
                error=str(exc),
                duration=duration
            )

            print(
                f"\nRESULT: FAILED"
            )

            print(
                f"ERROR: {exc}"
            )

            return error_result

    # =====================================================
    # HISTORY FORMAT
    # =====================================================

    @staticmethod
    def _format_history(history):

        if not history:
            return "No previous test history."

        output = []

        for item in history:

            output.append(
                f"""
Run {item['run_id']}
Attempt: {item['attempt']}
Status: {item['status']}
Reason: {item.get('reason')}
Evidence: {item.get('evidence')}
"""
            )

        return "\n".join(output)

    # =====================================================
    # FINAL JSON PARSER
    # =====================================================

    @staticmethod
    def _parse_final_result(text: str):

        text = text.strip()

        try:

            return json.loads(text)

        except json.JSONDecodeError:
            pass

        # Handle ```json ... ```
        if "```json" in text:

            text = (
                text
                .split("```json", 1)[1]
                .split("```", 1)[0]
                .strip()
            )

            try:
                return json.loads(text)

            except json.JSONDecodeError:
                pass

        # Last-resort classification
        upper = text.upper()

        if "PASS" in upper and "FAIL" not in upper:

            return {
                "status": "PASS",
                "reason": text,
                "evidence": []
            }

        return {
            "status": "FAILED",
            "reason": text,
            "evidence": []
        }