# API (Backend)

Python FastAPI 기반 백엔드. `api/` 디렉토리에 위치.

## 파일 구조

```
api/
├── main.py           # FastAPI 앱, 라우터, 엔드포인트
├── models.py         # SQLAlchemy ORM 모델
├── db.py             # DB 엔진, 세션 팩토리
├── ws_hub.py         # WebSocket 연결 관리
├── requirements.txt  # Python 의존성
└── Dockerfile        # 컨테이너 빌드
```

## 의존성

- FastAPI 0.115.6
- Uvicorn 0.32.1
- SQLAlchemy 2.0.36
- psycopg 3.2.3 (PostgreSQL 드라이버)

## 실행

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 관련 문서

- [엔드포인트 레퍼런스](./endpoints.md)
