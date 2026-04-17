from fastapi import FastAPI, Query
from contextlib import asynccontextmanager
from database.manager import DBManager
from core.lru_engine import run_lru_cleanup
import asyncio
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.expanduser(CACHE_DIR), exist_ok=True)
    await db.init_db()
    lru_task = asyncio.create_task(lru_scheduler())
    yield
    lru_task.cancel()


app = FastAPI(title="DiscoHack Backend", lifespan=lifespan)
db = DBManager("cloudfusion.db")

CACHE_DIR = "~/.cache/disco-hack/"
MAX_CACHE_GB = 5


async def lru_scheduler():
    while True:
        try:
            await run_lru_cleanup(db.db_path, CACHE_DIR, MAX_CACHE_GB)
        except Exception as e:
            print(f"LRU Error: {e}")
        await asyncio.sleep(600)


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1)):
    return await db.search_files(q)


@app.get("/api/stats")
async def api_stats():
    return await db.get_stats()


@app.get("/api/files/list")
async def api_list(parent_id: int = None):
    return await db.get_items_by_parent(parent_id)


@app.post("/api/files/{file_id}/pin")
async def api_pin(file_id: int, pinned: bool):
    await db.toggle_pin(file_id, pinned)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
