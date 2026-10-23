
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("TRUSTVAULT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "TRUSTVAULT_SECRET_KEY is missing. "
        "Set it in your backend .env file."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30
