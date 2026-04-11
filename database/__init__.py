# database/__init__.py
# Re-export both DB classes for easy import
from database.mongodb import MongoDB
from database.neondb import NeonDB

# ── Active DB alias ───────────────────────────────────────────
# Change `DB` to `NeonDB` here to switch the entire bot to PostgreSQL.
# Both classes expose the same async interface.
DB = MongoDB
