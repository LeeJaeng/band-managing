import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sqlalchemy import text

from db import engine, Base
from routers import songs, contis, admin

# 기존 테이블에 새 컬럼 추가 (마이그레이션)
MIGRATIONS = [
    "ALTER TABLE songs ADD COLUMN IF NOT EXISTS keys JSON",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """DB 연결 대기 후 테이블 생성 + 마이그레이션."""
    for attempt in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception:
            if attempt < 9:
                time.sleep(2)
            else:
                raise

    # 마이그레이션 실행
    with engine.connect() as conn:
        for sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()
    yield


app = FastAPI(title="Band Managing API", version="0.1.0", lifespan=lifespan)

app.include_router(songs.router)
app.include_router(contis.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"ok": True, "service": "band-managing-api"}
