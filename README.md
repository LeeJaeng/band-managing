# Band Managing

찬양팀 운영 관리 서비스 (리빌드 예정)

## 인프라 정보

- **배포**: AWS Lightsail + GitHub Actions (main push → 자동 배포)
- **컨테이너**: Docker Compose (Nginx + App + DB)
- **CI/CD**: `.github/workflows/deploy.yml`
- **참조 설정**: `infra-ref/` 디렉토리에 기존 인프라 설정 보관

## infra-ref/

| 파일 | 설명 |
|------|------|
| `docker-compose.yml` | 기존 Docker Compose 구성 (nginx, web, api, db) |
| `nginx-default.conf` | Nginx 리버스 프록시 설정 |
| `api-Dockerfile` | Python FastAPI 컨테이너 빌드 |
| `web-Dockerfile` | Nuxt 3 컨테이너 빌드 |

## Lightsail 서버

- 경로: `/home/ubuntu/band-managing/`
- SSH 접속 정보: GitHub Secrets (`LIGHTSAIL_HOST`, `LIGHTSAIL_USER`, `LIGHTSAIL_SSH_KEY`, `LIGHTSAIL_PORT`)
