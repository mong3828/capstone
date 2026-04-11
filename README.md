# B2MARK

안전한 데이터 유통을 위한 **워터마킹·검출·소유권 관리** 도구 (로컬 엔진 + CLI + 추후 웹/API).

## 문서

| 문서 | 설명 |
|------|------|
| [12주_개발_계획.md](./12주_개발_계획.md) | 주차별 목표·산출물 |
| [설계문서.md](./설계문서.md) | 전체 설계·로컬 중심 원칙 |
| [docs/scope_alignment.md](./docs/scope_alignment.md) | 설계문서 vs 12주 계획(웹/API) 정렬 |
| [docs/threat_model_v1.md](./docs/threat_model_v1.md) | 위협 모델 v1 |
| [docs/acceptance_criteria_v1.md](./docs/acceptance_criteria_v1.md) | 보안 AC v1 |
| [docs/api_spec_v1.md](./docs/api_spec_v1.md) | CLI·REST·Python API 초안 |
| [docs/engine_interface.md](./docs/engine_interface.md) | 엔진 입출력 |

(`docs/**/*.md` 는 `.gitignore` 에 포함되어 있으면 Git 에 올라가지 않음. 로컬에서만 참고하거나 나중에 별도로 추가.)

## 프로젝트 구조

```text
B2MARK/
  pyproject.toml
  package.json         # Hardhat + OpenZeppelin (7주차 컨트랙트)
  contracts/
    DataAsset.sol
  test-solidity/       # Hardhat 테스트
  core/
    hash_utils.py
    onchain.py         # web3.py — structHash·서명·mint (8주차)
    watermark.py       # B²Mark 삽입·검출·통계 유틸
  cli/
  docs/
  tests/
  .github/workflows/ci.yml
```

## 로컬 실행

```powershell
cd B2MARK
copy .env.example .env
# .env 에 B2MARK_WATERMARK_SECRET_KEY 등 필요한 값을 채움 (Git 에 올리지 않음)
python -m pip install -e ".[dev]"
npm install
python -m pytest
python -m bandit -r core cli api -q -ll
watermark --version
```

### 스마트 컨트랙트 (7주차)

```powershell
npm install
npx hardhat test
```

설계 요약: `docs/week7_contract_design.txt`

### 온체인 mint (8주차)

`.env` 에 `B2MARK_RPC_URL`, `B2MARK_CONTRACT_ADDRESS`, `B2MARK_ADMIN_PRIVATE_KEY` 를 두고,
(선택) `B2MARK_USER_PRIVATE_KEY` 로 민팅 가스만 다른 지갑에 둘 수 있습니다.

```powershell
watermark mint -i .\out.csv --metadata-uri ipfs://Qm.../meta.json
```

가이드: `docs/week8_user_guide.txt`

**Git:** 원격 CI를 쓰려면 저장소 **루트를 `B2MARK` 폴더**로 두는 것이 좋습니다 (`.github` 위치).

## 현재 상태

- `core/watermark.py`: [cds3473/2376292](https://github.com/cds3473/2376292) 와 동일한 Green Zone·비트열·Z-검정 (삽입 시 `metadata` 로 검출).
- `core/hash_utils.py`: SHA-256 파일/바이트 해시

---

*12주 계획 기준 개발 (2026.03)*
