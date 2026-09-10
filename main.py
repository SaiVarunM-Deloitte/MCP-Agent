from __future__ import annotations

import asyncio
import json

from mcp import ClientSession
from mcp.client.stdio import (
    StdioServerParameters,
    stdio_client
)
from openai import AsyncOpenAI

from agent.agent import TestAgent
from agent.executor import PlaywrightExecutor
from agent.memory import TestMemory
from agent.reporter import Reporter

from agent.testcase_parser import TestCaseParser

import config


# =========================================================
# LOAD TEST CASES
# =========================================================

def load_test_cases():

    path = (
        config.TESTCASE_DIR /
        "example.json"
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Test case file not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    parser = TestCaseParser()

    if isinstance(data, dict):
        data = [data]

    return [
        parser.normalize(
            item,
            default_id=f"TC{index:03d}"
        )
        for index, item in enumerate(
            data,
            start=1
        )
    ]


# =========================================================
# MAIN
# =========================================================

async def main():

    print()
    print("=" * 70)
    print("AI PLAYWRIGHT MCP TEST AGENT")
    print("=" * 70)

    # -----------------------------------------------------
    # Load test cases
    # -----------------------------------------------------

    test_cases = load_test_cases()

    print(
        f"\nLoaded {len(test_cases)} test case(s)"
    )

    # -----------------------------------------------------
    # OpenAI
    # -----------------------------------------------------

    client = AsyncOpenAI(
        api_key=config.OPENAI_API_KEY
    )

    # -----------------------------------------------------
    # Persistent memory
    # -----------------------------------------------------

    memory = TestMemory(
        config.MEMORY_DB
    )

    # -----------------------------------------------------
    # Create test run
    # -----------------------------------------------------

    run_id = memory.create_run()

    # -----------------------------------------------------
    # Launch Playwright MCP
    # -----------------------------------------------------

    server_params = StdioServerParameters(
        command=config.MCP_COMMAND,
        args=config.MCP_ARGS
    )

    print(
        "\nStarting Playwright MCP..."
    )

    async with stdio_client(
        server_params
    ) as (
        read_stream,
        write_stream
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            # Initialize MCP
            await session.initialize()

            print(
                "Playwright MCP connected."
            )

            # -------------------------------------------------
            # Executor
            # -------------------------------------------------

            executor = PlaywrightExecutor(
                session
            )

            # -------------------------------------------------
            # AI Agent
            # -------------------------------------------------

            agent = TestAgent(
                openai_client=client,
                executor=executor,
                memory=memory,
                model=config.LLM_MODEL,
                max_steps=config.MAX_AGENT_STEPS
            )

            # =================================================
            # FIRST RUN
            # =================================================

            print()
            print("=" * 70)
            print("FIRST EXECUTION")
            print("=" * 70)

            for test_case in test_cases:

                await agent.run_test(
                    run_id=run_id,
                    test_case=test_case,
                    attempt=1
                )

            # =================================================
            # FAILED TESTS
            # =================================================

            failed_tests = memory.get_failed_tests(
                run_id
            )

            print()
            print(
                f"Failed tests requiring retest: "
                f"{len(failed_tests)}"
            )

            # =================================================
            # RETEST
            # =================================================

            for failed in failed_tests:

                test_case = next(
                    (
                        tc
                        for tc in test_cases
                        if tc["id"]
                        == failed["test_id"]
                    ),
                    None
                )

                if test_case is None:
                    continue

                await agent.run_test(
                    run_id=run_id,
                    test_case=test_case,
                    attempt=failed["attempt"] + 1
                )

            # =================================================
            # FINAL RESULTS
            # =================================================

            results = memory.get_final_results(
                run_id
            )

            passed = sum(
                1
                for result in results
                if result["status"] == "PASS"
            )

            failed = sum(
                1
                for result in results
                if result["status"] == "FAILED"
            )

            memory.finish_run(
                run_id=run_id,
                total_tests=len(test_cases),
                passed=passed,
                failed=failed
            )

            # =================================================
            # REPORT
            # =================================================

            reporter = Reporter(
                config.REPORT_DIR
            )

            report_paths = reporter.generate(
                run_id=run_id,
                results=results
            )

            print()
            print("=" * 70)
            print("FINAL RESULTS")
            print("=" * 70)

            print(
                f"Total : {len(test_cases)}"
            )

            print(
                f"Passed: {passed}"
            )

            print(
                f"Failed: {failed}"
            )

            print()
            print(
                f"JSON : {report_paths['json']}"
            )

            print(
                f"HTML : {report_paths['html']}"
            )

            print(
                f"DB   : {config.MEMORY_DB}"
            )

    memory.close()

    print()
    print("Test execution completed.")


if __name__ == "__main__":

    asyncio.run(main())