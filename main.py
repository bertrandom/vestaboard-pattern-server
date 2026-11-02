import json
import logging
import logging.config
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import aiohttp
import vesta
from appcfg import get_config
from fastapi import FastAPI

STATE_DB_PATH = Path("data/state.db")

TRONBYT_DEVICE_URL = "http://nuke.smittn.com:8000/v0/devices/tidbyt"
TRONBYT_INSTALLATION_ID = "109"
TRONBYT_APP_ID = "vestaboard"

logger = logging.getLogger(__name__)

config = get_config("main")

conn = sqlite3.connect(config["patterns_db_path"])
cursor = conn.cursor()

state_conn = sqlite3.connect(STATE_DB_PATH)
state_cursor = state_conn.cursor()

session = None

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
    async with aiohttp.ClientSession() as session:
        app.state.http_session = session
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

    date_cursor = result[0]

    await update_tronbyt(date_cursor)

    return {"ok": True, "date_cursor": date_cursor}

async def update_tronbyt(date_cursor = None):
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

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['tronbyt_api_key']}"
    }

    # Save the pattern on the installation so it stays current in rotation
    url = f"{TRONBYT_DEVICE_URL}/installations/{TRONBYT_INSTALLATION_ID}"

    async with app.state.http_session.patch(url, json={"config": {"message_body": row[0]}}, headers=headers) as resp:
        if resp.status >= 400:
            logger.error(f"Tronbyt installation update failed: {resp.status} {await resp.text()}")
            return

    # Render the app with this pattern and show it immediately. Don't pass
    # installationID: Tronbyt then tracks a separate "pushed" app and re-sends its
    # first cached image on every later push instead of re-rendering.
    url = f"{TRONBYT_DEVICE_URL}/push_app"

    payload = {
        "app_id": TRONBYT_APP_ID,
        "background": False,
        "config": {"message_body": row[0]}
    }

    async with app.state.http_session.post(url, json=payload, headers=headers) as resp:
        if resp.status >= 400:
            logger.error(f"Tronbyt push_app failed: {resp.status} {await resp.text()}")

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

    date_cursor = result[0]

    state_cursor.execute("UPDATE state SET value = ? WHERE key = 'date_cursor'", (result[0],))
    state_conn.commit()

    await update_tronbyt(date_cursor)

    return {"ok": True, "date_cursor": date_cursor}

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

async def update_tronbyt_with_sending():
    url = f"{TRONBYT_DEVICE_URL}/push_app"

    payload = {
        "app_id": "split-flap",
        "background": False,
        "config": {
            "message": "SENDING VESTA BOARD",
            "center_text": "true",
        }
    }

    await app.state.http_session.post(url, json=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['tronbyt_api_key']}"
    })

@app.post("/current/send")
async def send_current():

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

    # Filled is 71 but the Vestaboard Local API can't handle this, so we need to replace it with 69 (which is white)

    # Replace all 71 with 69 in pattern
    for i in range(len(pattern)):
        for j in range(len(pattern[i])):
            if pattern[i][j] == 71:
                pattern[i][j] = 69

    await update_tronbyt_with_sending()

    local_client = vesta.LocalClient(local_api_key=config["vestaboard"]["local_api_key"], base_url=config["vestaboard"]["base_url"])
    local_client.write_message(pattern)

    return {"ok": True}

@app.get("/")
async def read_root():
    return {"ok": True}
