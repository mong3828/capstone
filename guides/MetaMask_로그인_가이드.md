# 프론트엔드에서 MetaMask 로그인 구현하는 법

- 아직 **DB 설정이 완료되지 않아** 정상적인 로그인은 안될 수 있음
- 그러나 프론트에서 로그인 시도시 메타마스크 api를 호출하는 부분은 별도로 구현 가능 할 것
- 파일 하단부에 바로 **복사-붙여넣기 할 수 있는 메타마스크 호출 예제 코드**가 있습니다!

## 1. 한 줄 요약

1. MetaMask로 **지갑 주소**를 받고(*이때 장치에 메타마스크 웹앱이 설치되어 있어야 함!!!!!!)
2. 백엔드에서 **서명할 문장(message)** 을 받은 뒤
3. MetaMask로 **그 문장에 서명**하고
4. 서명을 백엔드에 제공하면 검토 후 **JWT 토큰**을 받습니다.

> **백엔드는 MetaMask를 직접 호출하지 않음!**  
> 지갑·서명은 **브라우저(프론트)** 에서만 처리됩니다

---

## 2. 역할


| 담당      | 하는 일                                       |
| ------- | ------------------------------------------ |
| **프론트** | MetaMask 연결, 메시지 서명, API 호출, 토큰 저장         |
| **백엔드** | nonce·message 발급, 서명 검증, JWT 발급, DB 사용자 관리 |


이때 프론트는 배포된 API URL만 사용하면 됩니다

---

## 3. 로그인 흐름 (그림)

```
[사용자] → [프론트] → [MetaMask]     (지갑 연결, 서명)
              ↓
         [MintMark API]              (nonce, login, refresh)
              ↓
            [DB]                     (백엔드만 접근)
```

**순서**

```
① MetaMask 연결 → walletAddress 확보
② POST /auth/nonce  → message, nonce 받기
③ MetaMask signMessage(message) → signature 받기
④ POST /auth/login  → accessToken, refreshToken 받기
⑤ 이후 API → Header: Authorization: Bearer {accessToken}
```

---

## 4. API 베이스 URL

팀에서 정한 배포 주소를 사용합니다. 예:

```text
https://smzhmk8lch.execute-api.ap-northeast-2.amazonaws.com
```

아래 경로는 모두 `{API_BASE}` 뒤에 붙입니다.  
(끝에 `/` 없이 쓰는 것을 권장합니다.)

---

## 5. 단계별 상세

### 5-1. MetaMask 설치·연결 (백엔드 호출 없음)

**목적:** 로그인에 쓸 **지갑 주소**를 얻습니다.  
**아직 로그인 완료가 아닙니다.**

```javascript
// MetaMask 설치 확인
if (!window.ethereum) {
  alert("MetaMask를 설치해 주세요.");
  throw new Error("window.ethereum 없음");
}

// 계정 연결 요청
await window.ethereum.request({ method: "eth_requestAccounts" });

// ethers v6 예시
import { BrowserProvider } from "ethers";

const provider = new BrowserProvider(window.ethereum);
const signer = await provider.getSigner();
const walletAddress = await signer.getAddress();
// walletAddress 예: "0x33403E93FeDD45250CB32bdc35B2D782A871a19e"
```

**자주 쓰는 MetaMask API**


| API                          | 용도                                |
| ---------------------------- | --------------------------------- |
| `eth_requestAccounts`        | 지갑 연결·주소 노출 (사용자 승인 팝업)           |
| `wallet_switchEthereumChain` | Sepolia 등 팀이 정한 체인으로 전환 (필요 시)    |
| `signer.signMessage(text)`   | 로그인용 메시지 서명 (내부적으로 personal_sign) |


체인 ID는 팀 정책에 맞추세요. (참고: `webtest/app.js`는 Sepolia `11155111` 사용)

---

### 5-2. `POST /auth/nonce` — 서명할 문장 받기

**언제:** 지갑 주소를 알았을 때, **서명 전에** 한 번 호출합니다.

**요청**

```http
POST {API_BASE}/auth/nonce
Content-Type: application/json
```

```json
{
  "walletAddress": "0x33403E93FeDD45250CB32bdc35B2D782A871a19e"
}
```

**성공 응답** (필드명은 camelCase)

```json
{
  "nonce": "d43b9cd2a1a047f5a8c16e0edd9f3a62",
  "message": "MintMark 로그인 요청\n지갑: 0x3340...\nnonce: d43b9c...\n만료(UTC): 2026-04-13T01:49:09.801963+00:00",
  "expiresAt": "2026-04-13T01:49:09.801963Z"
}
```

**프론트에서 꼭 할 일**

- `nonce`, `message`를 **상태/변수에 저장**해 두기 (다음 단계에서 사용)
- `message`는 **한 글자도 수정하지 말 것** (백엔드가 DB에 저장한 문자열과 동일해야 함)
- `expiresAt` 기준 **약 15분** 안에 로그인까지 마치기

**에러 예**


| 상태  | 의미                                 |
| --- | ---------------------------------- |
| 400 | `walletAddress` 형식 오류 (`0x` + 42자) |


---

### 5-3. MetaMask로 `message` 서명 (백엔드 호출 없음)

**목적:** “이 지갑 주인이 로그인을 승인했다”는 **전자 서명**을 만듭니다.

```javascript
const signature = await signer.signMessage(message);
// signature 예: "0xabc123..."
```

- `message`는 **5-2 응답의 `message` 전체**를 그대로 사용합니다.
- 사용자에게 MetaMask **서명 요청** 팝업이 뜹니다. 거절하면 로그인 중단.

---

### 5-4. `POST /auth/login` — 서명 제출 → JWT 받기

**요청**

```http
POST {API_BASE}/auth/login
Content-Type: application/json
```

```json
{
  "walletAddress": "0x33403E93FeDD45250CB32bdc35B2D782A871a19e",
  "signature": "0x...",
  "nonce": "d43b9cd2a1a047f5a8c16e0edd9f3a62"
}
```


| 필드              | 설명                           |
| --------------- | ---------------------------- |
| `walletAddress` | 5-1에서 받은 주소 (5-2 요청과 동일해야 함) |
| `signature`     | 5-3 `signMessage` 결과         |
| `nonce`         | 5-2 응답의 `nonce`              |


**성공 응답**

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "342h-43_0iO6gNts3PYxhPiX...",
  "tokenType": "bearer",
  "expiresIn": 900
}
```

**프론트에서 꼭 할 일**

- `accessToken`, `refreshToken`을 **안전하게 저장** (메모리, httpOnly 쿠키 등 팀 정책에 따름)
- `expiresIn`은 액세스 토큰 유효 시간(초). 기본 **900초(15분)** 근처

**서버 동작 (참고)**

- 서명이 지갑 주소와 맞는지 검증
- nonce가 유효·미사용인지 확인 후 **1회용으로 소진**
- 해당 지갑 사용자가 없으면 **자동 회원가입**

**에러 예**


| 상태  | 의미                | 프론트 대응                     |
| --- | ----------------- | -------------------------- |
| 400 | nonce 만료·없음·이미 사용 | `/auth/nonce`부터 다시         |
| 401 | 서명 검증 실패          | 주소·message·signature 다시 확인 |
| 403 | 비활성 계정            | 관리자 문의                     |


---

### 5-5. 로그인 후 API 호출

MetaMask는 **더 이상 필요 없습니다.**  
보호된 API마다 헤더만 추가합니다.

```http
GET {API_BASE}/users/me
Authorization: Bearer {accessToken}
```

**예: 내 정보 조회**

```javascript
const res = await fetch(`${API_BASE}/users/me`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
const me = await res.json();
// walletAddress, name, role, status 등
```

**토큰이 필요한 API 예**

- `GET /users/me`, `PATCH /users/me`
- NFT 등록·조회 등 (팀 API 명세 참고)

---

## 6. 토큰 갱신·로그아웃

### 6-1. 액세스 토큰 만료 시 — `POST /auth/refresh`

`accessToken`이 만료되면(401) **리프레시**로 새 토큰을 받습니다.

```http
POST {API_BASE}/auth/refresh
Content-Type: application/json
```

```json
{
  "refreshToken": "저장해 둔 refreshToken"
}
```

**응답:** 새 `accessToken`, 새 `refreshToken` (이전 refresh는 서버에서 폐기)

```javascript
async function refreshTokens() {
  const data = await apiJson("/auth/refresh", {
    method: "POST",
    body: { refreshToken },
  });
  accessToken = data.accessToken;
  refreshToken = data.refreshToken;
}
```

리프레시도 실패하면 → **처음부터 로그인(5-1 ~ 5-4)**.

---

### 6-2. 로그아웃 — `POST /auth/logout`

```http
POST {API_BASE}/auth/logout
Content-Type: application/json
```

```json
{
  "refreshToken": "저장해 둔 refreshToken"
}
```

**응답:** `{ "status": "ok" }`

프론트는 **로컬의 accessToken·refreshToken을 삭제**하고 로그인 화면으로 이동합니다.

---

## 7. API 한눈에 보기


| 메서드   | 경로              | 인증                  | 설명                   |
| ----- | --------------- | ------------------- | -------------------- |
| POST  | `/auth/nonce`   | 없음                  | 서명용 message·nonce 발급 |
| POST  | `/auth/login`   | 없음                  | 서명 검증 후 JWT 발급       |
| POST  | `/auth/refresh` | body `refreshToken` | 액세스 토큰 재발급           |
| POST  | `/auth/logout`  | body `refreshToken` | 리프레시 토큰 폐기           |
| GET   | `/users/me`     | Bearer              | 내 프로필 조회             |
| PATCH | `/users/me`     | Bearer              | 이름·이메일 수정            |


**JSON 필드명:** 요청·응답 모두 **camelCase** (`walletAddress`, `accessToken` 등).

---

## 8. 복사해서 쓸 수 있는 최소 예제!

```javascript
const API_BASE = "https://smzhmk8lch.execute-api.ap-northeast-2.amazonaws.com";

async function loginWithMetaMask() {
  if (!window.ethereum) throw new Error("MetaMask 필요");

  await window.ethereum.request({ method: "eth_requestAccounts" });
  const { BrowserProvider } = await import("ethers");
  const provider = new BrowserProvider(window.ethereum);
  const signer = await provider.getSigner();
  const walletAddress = await signer.getAddress();

  // 1) nonce
  const nonceRes = await fetch(`${API_BASE}/auth/nonce`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ walletAddress }),
  });
  if (!nonceRes.ok) throw new Error("nonce 실패");
  const { nonce, message } = await nonceRes.json();

  // 2) sign
  const signature = await signer.signMessage(message);

  // 3) login
  const loginRes = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ walletAddress, signature, nonce }),
  });
  if (!loginRes.ok) throw new Error("login 실패");
  const { accessToken, refreshToken } = await loginRes.json();

  return { accessToken, refreshToken, walletAddress };
}
```

---

## 9. 자주 하는 실수


| 실수                           | 올바른 방법                                           |
| ---------------------------- | ------------------------------------------------ |
| 지갑만 연결하고 끝냄                  | `/auth/nonce` + 서명 + `/auth/login`까지 해야 로그인 완료   |
| `message`를 프론트에서 새로 만듦       | 반드시 `/auth/nonce` 응답의 `message` 그대로 서명           |
| nonce를 빼거나 다른 nonce 사용       | login 요청의 `nonce`는 nonce API 응답과 동일              |
| 로그인 후에도 매 API마다 MetaMask 서명  | JWT `Bearer`만 사용 (만료 시 refresh)                  |
| `walletAddress` 대소문자·체크섬 불일치 | 연결한 주소와 login body 주소 동일하게                       |
| CORS 오류                      | API Gateway·백엔드 CORS에 프론트 origin 등록 여부 백엔드 팀과 확인 |


