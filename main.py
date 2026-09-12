import json
import logging
import logging.config
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from appcfg import get_config
from fastapi import FastAPI

STATE_DB_PATH = Path("data/state.db")

logger = logging.getLogger(__name__)

config = get_config("main")

conn = sqlite3.connect(config["patterns_db_path"])
cursor = conn.cursor()

state_conn = sqlite3.connect(STATE_DB_PATH)
state_cursor = state_conn.cursor()

async def get_date_cursor():
    state_cursor.execute("SELECT value FROM state WHERE key = 'date_cursor'")
    result = state_cursor.fetchone()
    if result:
        logger.info(f"Retrieved date_cursor from state: {result[0]}")
        return result[0]
    else:
        cursor.execute("""
            SELECT DISTINCT pick_date
            FROM Pick
            ORDER BY pick_date DESC
            LIMIT 1
        """)
        result = cursor.fetchone()

        if not result:
            logger.error("No pick dates found.")
            return

        latest_pick_date = result[0]

        state_cursor.execute("INSERT INTO state (key, value) VALUES (?, ?)", ('date_cursor', latest_pick_date))
        state_conn.commit()
        logger.info(f"Initialized date_cursor in state: {latest_pick_date}")
        return latest_pick_date


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/previous")
async def cursor_previous():

    date_cursor = await get_date_cursor()

    cursor.execute("""
        SELECT DISTINCT pick_date
        FROM Pick
        WHERE Pick.pick_date < ?
        ORDER BY pick_date DESC
        LIMIT 1
    """, (date_cursor,))
    result = cursor.fetchone()

    if not result:
        return {"ok": False, "date_cursor": date_cursor}

    state_cursor.execute("UPDATE state SET value = ? WHERE key = 'date_cursor'", (result[0],))
    state_conn.commit()

    return {"ok": True, "date_cursor": result[0]}

@app.post("/next")
async def cursor_next():

    date_cursor = await get_date_cursor()

    cursor.execute("""
        SELECT DISTINCT pick_date
        FROM Pick
        WHERE Pick.pick_date > ?
        ORDER BY pick_date ASC
        LIMIT 1
    """, (date_cursor,))
    result = cursor.fetchone()

    if not result:
        return {"ok": False, "date_cursor": date_cursor}

    state_cursor.execute("UPDATE state SET value = ? WHERE key = 'date_cursor'", (result[0],))
    state_conn.commit()

    return {"ok": True, "date_cursor": result[0]}

@app.get("/current")
async def read_current():

    date_cursor = await get_date_cursor()

    cursor.execute("""
        SELECT Message.body
        FROM Pick
        JOIN Message ON Pick.message_id = Message.id
        WHERE Pick.pick_date = ?
        LIMIT 1
    """, (date_cursor,))
    row = cursor.fetchone()

    if not row:
        logger.error(f"No messages found for pick date: {date_cursor}")
        return

    raw_pattern = row[0]

    pattern = json.loads(raw_pattern)

    return {"ok": True, "date_cursor": date_cursor, "pattern": pattern}


@app.get("/")
async def read_root():
    return {"ok": True}
