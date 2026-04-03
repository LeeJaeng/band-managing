# 배포 파이프라인

## 개요

GitHub Actions → SSH → AWS Lightsail → Docker Compose

## 트리거

`main` 브랜치에 push 시 자동 배포.

## 워크플로우 (`.github/workflows/deploy.yml`)

1. Lightsail 인스턴스에 SSH 접속
2. `/home/ubuntu/band-managing` 디렉토리로 이동
3. `git pull origin main`
4. `docker compose up -d --build`
5. API 헬스 체크 (최대 90초 대기)
6. Nginx 프록시 통과 확인 (`/api/health`)

## GitHub Secrets

| 시크릿 | 설명 |
|--------|------|
| `LIGHTSAIL_HOST` | 서버 IP/호스트 |
| `LIGHTSAIL_USER` | SSH 사용자명 |
| `LIGHTSAIL_SSH_KEY` | SSH 개인키 |
| `LIGHTSAIL_PORT` | SSH 포트 |

## 헬스 체크

- API 컨테이너 내부: `http://127.0.0.1:8000/health`
- Nginx 프록시: `http://localhost/api/health`
- 재시도: 18회, 5초 간격 (총 90초)
- 실패 시: 로그 출력 후 배포 실패 처리

## 수동 배포

```bash
ssh user@host
cd /home/ubuntu/band-managing
git pull origin main
docker compose up -d --build
```
