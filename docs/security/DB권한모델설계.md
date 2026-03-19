## DB 권한 모델 설계


## 1) 용어
- **Subject(주체)**: request를 보낸 사용자 (예: user)
- **Object(객체)**: Job/File 등 접근 대상
- **Action(행동)**: read/create/download 등
- **Attribute(속성)**: tenant_id, user_id(소유자), role 등

---

## 2) RBAC
DB에 접근하는 사용자 그룹을 두가지로 분류함
- **admin**
  - 동일 tenant 범위에서 AuditLog 조회 등 관리 기능 가능
- **user**
  - 본인 Job/File 생성 및 조회/다운로드 가능

현재는(2주차) admin 기능을 세부적으로 구현하지 않았으며, 추후 (약 8주차로 예상) 구현 예정

---

## 3) ABAC+ object-level auth
### 기본 규칙
- **R1 (Tenant 경계)**: 모든 리소스는 `tenant_id` 스코프를 벗어나면 접근 불가
- **R2 (소유자 규칙)**: Job/File은 기본적으로 `user_id`(소유자)만 접근 가능
- **R3 (예외: admin)**: admin은 동일 tenant 내에서 타 사용자 리소스 접근 가능(추후 범위 확정 예정)

---

## 4) API별 권한 매핑 (*2주차 기준)
### Jobs
- **GET /jobs/{job_id}**
  - **허용**: subject.tenant_id == job.tenant_id AND (subject.user_id == job.user_id OR subject.role == admin)
  - **거절**: 위 조건 불만족 시 403
- **POST /jobs**
  - **허용**: 인증된 사용자(tenant_id 존재)
  - **추가 조건**: source_object_key가 subject 소유인지 검증 (3주차에 구체적 구현 예정)

### Files/Storage
- **POST /storage/upload-url**
  - **허용**: 인증된 사용자
  - **추가 조건**: 업로드 제한 정책(크기/타입) 위반 시 400/413

---

## 5) 실패 코드 정책
- **401 Unauthorized**: 토큰 없음/만료/서명 실패
- **403 Forbidden**: 인증은 되었으나 object-level auth 불만족
- **404 Not Found**: 리소스 미존재