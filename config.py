from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
TESTCASE_DIR = BASE_DIR / "testcases"

MEMORY_DB = DATA_DIR / "test_memory.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
TESTCASE_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# OPENAI
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "gpt-5"
)

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. "
        "Add it to your .env file."
    )


# =========================================================
# PLAYWRIGHT MCP
# =========================================================

# Windows:
# cmd.exe /c npx.cmd -y @playwright/mcp@latest --headless

MCP_COMMAND = "cmd.exe"

MCP_ARGS = [
    "/c",
    "npx.cmd",
    "-y",
    "@playwright/mcp@latest",
    "--headless"
]


# =========================================================
# TEST EXECUTION
# =========================================================

MAX_RETRIES = int(
    os.getenv("MAX_RETRIES", "1")
)

MAX_AGENT_STEPS = int(
    os.getenv("MAX_AGENT_STEPS", "30")
)

TAKE_SCREENSHOTS = (
    os.getenv("TAKE_SCREENSHOTS", "true").lower()
    == "true"
)