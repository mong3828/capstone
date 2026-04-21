# MintMark 파일 안내

- **A. 핵심 엔진**: 워터마크/해시/온체인 핵심 로직
- **B. CLI**: 로컬 명령행 실행 진입점
- **C. API 서버**: 인증·사용자·NFT·워터마크 HTTP 계층
- **D. 스마트 컨트랙트**: NFT 발급/검증을 위한 Solidity 영역
- **E. 테스트**: 기능별 회귀 방지 테스트
- **F. 운영/설정**: 패키징, CI, 배포, 환경변수

---

## A. 핵심 엔진 (`MintMark/core`)

| 파일 | 역할 |
|---|---|
| [`MintMark/core/watermark.py`](https://github.com/mong3828/capstone/blob/main/MintMark/core/watermark.py) | CSV 워터마크 삽입/검출의 핵심 알고리즘 구현 |
| [`MintMark/core/hash_utils.py`](https://github.com/mong3828/capstone/blob/main/MintMark/core/hash_utils.py) | 파일/바이트 SHA-256 해시 유틸리티 |
| [`MintMark/core/onchain.py`](https://github.com/mong3828/capstone/blob/main/MintMark/core/onchain.py) | Python(web3) 기반 온체인 호출(민팅/트랜잭션) |
| [`MintMark/core/csv_safety.py`](https://github.com/mong3828/capstone/blob/main/MintMark/core/csv_safety.py) | CSV 인젝션 위험 패턴 탐지 및 차단 |
| [`MintMark/core/env_bootstrap.py`](https://github.com/mong3828/capstone/blob/main/MintMark/core/env_bootstrap.py) | `.env` / `.env.local` 로딩 부트스트랩 |

---

## B. CLI (`MintMark/cli`)

| 파일 | 역할 |
|---|---|
| [`MintMark/cli/main.py`](https://github.com/mong3828/capstone/blob/main/MintMark/cli/main.py) | `insert/detect/hash/mint` 명령 실행 진입점 |
| [`MintMark/cli/__main__.py`](https://github.com/mong3828/capstone/blob/main/MintMark/cli/__main__.py) | `python -m cli` 실행 시 엔트리포인트 |
| [`MintMark/cli/__init__.py`](https://github.com/mong3828/capstone/blob/main/MintMark/cli/__init__.py) | CLI 패키지 초기화 |

---

## C. API 서버 (`MintMark/api`)

### C-1. 서버 진입/공통

| 파일 | 역할 |
|---|---|
| [`MintMark/api/main.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/main.py) | FastAPI 앱 생성, CORS, 라우터 등록, `/health`, `/watermark` |
| [`MintMark/api/config.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/config.py) | 업로드 크기/행/열 제한 환경변수 설정 |
| [`MintMark/api/errors.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/errors.py) | 통합 오류 포맷(`error.code/message/httpStatus`) 핸들링 |
| [`MintMark/api/datetime_utils.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/datetime_utils.py) | naive/aware datetime UTC 정규화 유틸 |
| [`MintMark/api/watermark_service.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/watermark_service.py) | API 공용 워터마크 처리 서비스 로직 |

### C-2. 인증/사용자/NFT

| 파일 | 역할 |
|---|---|
| [`MintMark/api/security.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/security.py) | JWT 발급·검증, MetaMask(EIP-191) 서명 검증 |
| [`MintMark/api/deps.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/deps.py) | 인증 의존성(`get_current_user`) 및 DB 의존성 |
| [`MintMark/api/schemas.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/schemas.py) | 요청/응답 DTO(Pydantic) 정의 |
| [`MintMark/api/database.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/database.py) | SQLAlchemy 엔진/세션 설정 |
| [`MintMark/api/models.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/models.py) | ORM 모델(User, RefreshToken, LoginNonce, NftAsset) |
| [`MintMark/api/routers/auth.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/routers/auth.py) | `/auth/nonce`, `/auth/login`, `/auth/refresh`, `/auth/logout` |
| [`MintMark/api/routers/users.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/routers/users.py) | `/users/me` 조회·수정 |
| [`MintMark/api/routers/nfts.py`](https://github.com/mong3828/capstone/blob/main/MintMark/api/routers/nfts.py) | NFT 생성/목록/상세/수정/워터마크 API |

---

## D. 스마트 컨트랙트 (`MintMark/contracts`, Hardhat)

| 파일 | 역할 |
|---|---|
| [`MintMark/contracts/DataAsset.sol`](https://github.com/mong3828/capstone/blob/main/MintMark/contracts/DataAsset.sol) | NFT 민팅 관련 Solidity 컨트랙트 |
| [`MintMark/contracts/DataAsset.abi.json`](https://github.com/mong3828/capstone/blob/main/MintMark/contracts/DataAsset.abi.json) | Python/JS 연동용 ABI |
| [`MintMark/hardhat.config.js`](https://github.com/mong3828/capstone/blob/main/MintMark/hardhat.config.js) | Hardhat 네트워크/컴파일 설정 |
| [`MintMark/scripts/deploy_DataAsset.js`](https://github.com/mong3828/capstone/blob/main/MintMark/scripts/deploy_DataAsset.js) | 컨트랙트 배포 스크립트 |
| [`MintMark/test-solidity/DataAsset.test.js`](https://github.com/mong3828/capstone/blob/main/MintMark/test-solidity/DataAsset.test.js) | Solidity 단위 테스트 |

---

## E. 테스트 (`MintMark/tests`)

| 파일 | 역할 |
|---|---|
| [`MintMark/tests/test_api.py`](https://github.com/mong3828/capstone/blob/main/MintMark/tests/test_api.py) | 워터마크 API 및 입력 검증 테스트 |
| [`MintMark/tests/test_cli.py`](https://github.com/mong3828/capstone/blob/main/MintMark/tests/test_cli.py) | CLI 기능 통합/단위 테스트 |
| [`MintMark/tests/test_watermark.py`](https://github.com/mong3828/capstone/blob/main/MintMark/tests/test_watermark.py) | 워터마크 알고리즘 테스트 |
| [`MintMark/tests/test_csv_safety.py`](https://github.com/mong3828/capstone/blob/main/MintMark/tests/test_csv_safety.py) | CSV 인젝션 방어 테스트 |
| [`MintMark/tests/test_onchain.py`](https://github.com/mong3828/capstone/blob/main/MintMark/tests/test_onchain.py) | 온체인 연동 로직 테스트 |
| [`MintMark/tests/test_mintmark_stats.py`](https://github.com/mong3828/capstone/blob/main/MintMark/tests/test_mintmark_stats.py) | 통계/보조 함수 테스트 |
| [`MintMark/tests/conftest.py`](https://github.com/mong3828/capstone/blob/main/MintMark/tests/conftest.py) | 공통 테스트 환경/픽스처 설정 |

---

## F. 운영/설정

| 파일 | 역할 |
|---|---|
| [`MintMark/pyproject.toml`](https://github.com/mong3828/capstone/blob/main/MintMark/pyproject.toml) | Python 패키징/의존성/도구 설정 |
| [`MintMark/package.json`](https://github.com/mong3828/capstone/blob/main/MintMark/package.json) | Hardhat 및 Node 의존성 관리 |
| [`MintMark/.env.example`](https://github.com/mong3828/capstone/blob/main/MintMark/.env.example) | 필수 환경변수 예시 |
| [`MintMark/.github/workflows/ci.yml`](https://github.com/mong3828/capstone/blob/main/MintMark/.github/workflows/ci.yml) | Python/Node CI 파이프라인 |
| [`MintMark/.github/workflows/docker.yml`](https://github.com/mong3828/capstone/blob/main/MintMark/.github/workflows/docker.yml) | Docker 빌드 검증 |
| [`MintMark/dockerfile`](https://github.com/mong3828/capstone/blob/main/MintMark/dockerfile) | 컨테이너 배포 이미지 정의 |
| [`MintMark/README.md`](https://github.com/mong3828/capstone/blob/main/MintMark/README.md) | 프로젝트 개요/실행 방법 안내 |
