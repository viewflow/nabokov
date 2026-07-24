"""Configuration — env vars and the business constants in one place."""

import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]

# kmmbvnr is the admin: unlimited texts. Everyone else: 3 free, then packs.
ADMIN_USERNAMES = {u.strip().lower() for u in os.getenv("ADMIN_USERNAMES", "kmmbvnr").split(",")}

FREE_TEXTS = 3
PACK_STARS = 50
PACK_TEXTS = 13
MAX_WORDS = 600  # hard cap for everyone, no exceptions

DB_PATH = os.getenv("DB_PATH", "nabokovbot.sqlite3")

DEEPSEEK_MODEL = "deepseek-v4-flash"
TEMPERATURE_NORMAL = 1.0
TEMPERATURE_CREATIVE = 1.5
MAX_LINT_TOOL_CALLS = 2  # the skills cap self-check rounds at two
MAX_ASK_CALLS = 2  # clarifying questions to the user per text
ASK_TIMEOUT_SECONDS = 300  # no answer -> the model is told to do without
