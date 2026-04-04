import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import engine, Base
from routers import songs, contis, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """DB 연결 대기 후 테이블 생성."""
    for attempt in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception:
            if attempt < 9:
                time.sleep(2)
            else:
                raise
    yield


app = FastAPI(title="Band Managing API", version="0.1.0", lifespan=lifespan)

app.include_router(songs.router)
app.include_router(contis.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"ok": True, "service": "band-managing-api"}
