import asyncio
import json
import logging
import logging.config
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import aiohttp
from appcfg import get_config
from fastapi import FastAPI

from main import STATE_DB_PATH

logger = logging.getLogger(__name__)

config = get_config("main")

async def main() -> None:

    conn = sqlite3.connect(config["patterns_db_path"])
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT pick_date
        FROM Pick
        ORDER BY pick_date DESC
    """)
    result = cursor.fetchall()

    for row in result:
        date_cursor = row[0]
        print(f"pixlet render vestaboard-offline.star -c gen/{date_cursor}.json -o output/{date_cursor}.webp")
        

if __name__ == '__main__':
    asyncio.run(main())
