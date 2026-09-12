import json
import logging
import random
from contextlib import asynccontextmanager

from appcfg import get_config
from fastapi import FastAPI

logger = logging.getLogger(__name__)

config = get_config("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"ok": True}
