from fastapi import FastAPI

from db import engine, Base
from routers import songs, contis, admin

# 테이블 자동 생성 (MVP — 추후 Alembic 마이그레이션으로 전환)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Band Managing API", version="0.1.0")

app.include_router(songs.router)
app.include_router(contis.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"ok": True, "service": "band-managing-api"}
