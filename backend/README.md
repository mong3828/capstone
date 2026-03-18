## FlowGuard Backend (Week 1 skeleton)

### 의도(왜 이렇게 시작하나)
- **Docker 없이도** 로컬에서 바로 실행되는 API 뼈대를 먼저 만든다.
- 이후 주차에서 Auth/업로드/Job 처리 로직이 들어와도 흔들리지 않게, **요청 ID 기반 로깅**과 **일관된 에러 응답 형태**를 초기에 고정한다.

### 로컬 실행(Windows PowerShell)

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### 동작 확인
- 브라우저 또는 curl로 `GET /health`

```bash
curl http://127.0.0.1:8000/health
```

### 테스트 실행

```bash
pytest -q
```

