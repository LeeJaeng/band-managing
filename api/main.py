import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sqlalchemy import text

from sqlalchemy.orm import Session as _Session

from db import engine, Base
from routers import songs, contis, admin, team, auth as auth_router

# 기존 테이블에 새 컬럼 추가 (마이그레이션)
MIGRATIONS = [
    "ALTER TABLE songs ADD COLUMN IF NOT EXISTS keys JSON",
    "ALTER TABLE songs ADD COLUMN IF NOT EXISTS source VARCHAR(10) DEFAULT 'MANUAL'",
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

    # 관리자 시드
    from models import User
    from auth import hash_password
    with _Session(engine) as session:
        existing = session.query(User).filter(User.username == "jeansvvv").first()
        if not existing:
            admin_user = User(
                username="jeansvvv",
                password_hash=hash_password("spdhvhzj"),
                display_name="관리자",
                role="ADMIN",
            )
            session.add(admin_user)
            session.commit()
    yield


app = FastAPI(title="Band Managing API", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(songs.router)
app.include_router(contis.router)
app.include_router(admin.router)
app.include_router(team.router)


@app.get("/health")
def health():
    return {"ok": True, "service": "band-managing-api"}
