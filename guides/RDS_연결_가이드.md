# MintMark — AWS RDS(PostgreSQL) 연결 가이드

이 문서는 **MintMark API**가 로컬 SQLite 대신 **AWS RDS for PostgreSQL**을 쓰도록 연결하는 절차를 정리합니다.  
앱은 이미 `MINTMARK_DATABASE_URL` 환경 변수 하나로 DB 종류를 바꿀 수 있게 되어 있습니다.

---

## 1. 전체 그림

| 구분 | 설명 |
|------|------|
| 프론트엔드 | DB에 직접 연결하지 않습니다. **배포된 API URL**만 호출합니다. |
| 백엔드(Lambda·EC2 등) | `MINTMARK_DATABASE_URL`에 RDS 접속 문자열을 넣습니다. |
| RDS | PostgreSQL 인스턴스. **API가 있는 네트워크에서만** 5432 포트로 접근 가능하게 보안 그룹을 맞춥니다. |

**중요:** API를 **Lambda + VPC**에 두었다면, RDS도 **같은 VPC**(또는 피어링된 VPC) 안에 두고, RDS 보안 그룹 인바운드에 **Lambda가 붙은 보안 그룹**을 허용하는 방식이 일반적입니다.  
Lambda를 VPC 밖에 두면 RDS가 “퍼블릭”이 아니면 연결이 안 됩니다.

---

## 2. RDS 인스턴스 만들기 (콘솔)

1. AWS 콘솔 → **RDS** → **데이터베이스 생성**.
2. **엔진**: PostgreSQL (팀과 버전 통일, 예: 15 또는 16).
3. **템플릿**: 개발/실습이면 **프리 티어** 가능 시 선택.
4. **DB 인스턴스 식별자**: 예) `mintmark-db`.
5. **마스터 사용자 이름 / 비밀번호**: 안전한 비밀번호 저장(비밀 관리자·로컬 메모 금지 권장 → **Secrets Manager** 또는 팀 공유 금고).
6. **인스턴스 크기**: `db.t3.micro` 등.
7. **스토리지**: 기본값으로 시작 가능.
8. **연결**:
   - **VPC**: API(Lambda)를 올릴 VPC와 **동일**하게 선택하는 것이 가장 단순합니다.
   - **퍼블릭 액세스**:
     - **프로덕션 권장:** `아니오` — Lambda는 **VPC 안**에서만 접속.
     - **로컬 PC에서만 DB 테스트:** 잠시 `예`로 두고, 아래 보안 그룹에서 **본인 IP만** 5432 허용(범위를 넓히지 않기).
9. **VPC 보안 그룹**: 새로 만들거나 기존 선택. 이름 예: `sg-rds-mintmark`.
10. **초기 데이터베이스 이름**: 예) `mintmark` (나중에 URL에 그대로 씁니다).
11. 생성 완료까지 수 분 대기 → **엔드포인트**(호스트 이름)와 **포트**(기본 5432)를 메모합니다.

---

## 3. 보안 그룹(SG) 설정

### 3-A. RDS 쪽 SG (인바운드)

- **유형:** PostgreSQL (또는 사용자 지정 TCP **5432**)
- **소스:**
  - Lambda가 **VPC 안**이면: **Lambda에 연결한 SG**를 소스로 지정(예: `sg-lambda-mintmark`).
  - 로컬에서만 테스트: **내 IP**/32.

### 3-B. Lambda가 VPC 안에 있을 때 (요약)

1. Lambda → **구성** → **VPC** → 서브넷(보통 **프라이빗** 2개 이상) + **보안 그룹** 지정.
2. Lambda가 인터넷(ECR, 외부 API)에 나가야 하면 **NAT 게이트웨이**가 있는 라우팅이 필요합니다(프라이빗 서브넷 → NAT → 인터넷). 이 부분은 VPC 설계가 한 번 필요합니다.
3. RDS SG 인바운드에 **Lambda SG** 허용.

자세한 그림은 AWS 문서 [Lambda를 VPC에 구성](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)을 참고하세요.

---

## 4. 연결 문자열 (`MINTMARK_DATABASE_URL`)

형식(SQLAlchemy + psycopg2):

```text
postgresql+psycopg2://마스터사용자:비밀번호@엔드포인트:5432/데이터베이스이름?sslmode=require
```

- **비밀번호**에 `@`, `#`, `%` 등이 있으면 [URL 인코딩](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.quote)이 필요합니다.
- RDS는 TLS를 쓰는 경우가 많으므로 **`?sslmode=require`**(또는 환경에 맞게 `verify-full` 등)를 권장합니다.

예시(값은 가짜):

```text
postgresql+psycopg2://admin:MySecretPass%21@mintmark-db.xxxxx.ap-northeast-2.rds.amazonaws.com:5432/mintmark?sslmode=require
```

### Lambda에 넣는 방법

- Lambda 함수 → **구성** → **환경 변수** → `MINTMARK_DATABASE_URL` = 위 문자열 전체.
- 비밀번호는 가능하면 **Secrets Manager**에 두고 Lambda에서 읽어 조합하는 편이 안전합니다(초기에는 환경 변수로도 가능하나 과제 수준 이후에는 분리 권장).

### 로컬에서 테스트

PowerShell 예:

```powershell
$env:MINTMARK_DATABASE_URL="postgresql+psycopg2://USER:PASS@endpoint:5432/mintmark?sslmode=require"
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 5. MintMark 프로젝트 쪽에서 할 일

1. **의존성:** `pyproject.toml`에 `psycopg2-binary`가 포함되어 있어야 합니다(이미 반영됨).
2. **이미지 재빌드:** Lambda에 컨테이너 배포 시 `docker build` 후 ECR 푸시·함수 업데이트.
3. **시작 시 테이블:** `api/main.py`에서 `Base.metadata.create_all(bind=engine)`이 호출되므로, **빈 DB**에 처음 띄우면 테이블이 생성됩니다. 운영에서 스키마를 엄격히 관리하려면 Alembic 등 마이그레이션 도입을 검토하세요.

---

## 6. 동작 확인

1. RDS가 “사용 가능” 상태인지 확인.
2. SG가 실제 트래픽 경로(Lambda SG 또는 내 IP)를 허용하는지 확인.
3. API `GET /health` (또는 팀이 정의한 헬스) 성공.
4. 회원가입/로그인 등 DB를 쓰는 API 한 번 호출해 에러 로그가 없는지 확인.

---

## 7. 자주 나는 오류

| 증상 | 원인 후보 |
|------|-----------|
| `could not connect to server` | SG 미허용, RDS 엔드포인트/포트 오타, Lambda가 VPC 밖인데 RDS는 비공개 |
| `password authentication failed` | 사용자·비밀번호 오타, URL 인코딩 누락 |
| `SSL connection required` | URL에 `?sslmode=require` 추가 |
| Lambda 타임아웃 | 프라이빗 서브넷에 NAT 없이 외부만 호출하려 함, 또는 RDS SG 미설정으로 연결 대기 |

---

## 8. SQLite와의 차이

- **SQLite + `/tmp` (Lambda):** 컨테이너 재시작 시 데이터 유실 가능.
- **RDS:** 데이터가 RDS에 지속 저장되며, 백업·다중 AZ 등 운영 옵션을 쓸 수 있습니다.

질문이 VPC·NAT·RDS만의 비용 구조까지 이어지면, AWS 공식 **VPC + RDS + Lambda** 튜토리얼을 함께 보는 것을 권장합니다.
