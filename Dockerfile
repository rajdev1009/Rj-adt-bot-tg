# ════════════════════════════════════════════════════════════
# Dockerfile — Telegram File Store Bot
# Compatible with: Koyeb, Render, Railway, VPS (Docker)
# ════════════════════════════════════════════════════════════

FROM python:3.11-slim

# ── System deps ──────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python deps first (layer cache friendly) ──────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy source ───────────────────────────────────────────────
COPY . .

# ── Create session directory (Pyrogram stores .session files) ─
RUN mkdir -p /app/sessions

# ── Non-root user for security ────────────────────────────────
RUN useradd -m botuser && chown -R botuser /app
USER botuser

# ── Tell Docker/orchestrator to use SIGTERM for clean shutdown ─
# This lets Pyrogram finish its session cleanly rather than
# being killed mid-auth, which can invalidate the session file
# and force a full re-auth on next start (triggering FloodWait).
STOPSIGNAL SIGTERM

# ── Entry point ───────────────────────────────────────────────
# bot.py handles FloodWait internally by sleeping, so the
# container stays alive during flood cooldowns instead of
# exiting and being restarted by the orchestrator.
CMD ["python", "-u", "bot.py"]
