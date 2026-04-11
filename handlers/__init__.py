# handlers/__init__.py
# Pyrogram auto-discovers all handlers in this package
# because bot.py sets plugins={"root": "handlers"}
# Each module registers its handlers via @Client.on_* decorators.

from handlers import start, upload, settings, admin, help
