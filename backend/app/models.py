#======================================================================
# [ models.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.19
#======================================================================

# 함수 인자와 반환값의 데이터타입을 알기 어려워 어노테이션을 추가함
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

#======================================================================

'''
실제 테이블(SQLModel)에 추가로 ENUM을 구현함.
ENUM은 실수나 악의적인 의도로 중요 데이터(Role, JobStatus)에 올바르지 않은 값(예: Error)이 삽입될 경우
이를 판단하고 차단하는 역할을 수행함.
'''

class Role(str, Enum):
    admin = "admin"
    user = "user"


class JobStatus(str, Enum):
    Queued = "Queued"
    Running = "Running"
    Done = "Done"
    Fail = "Fail"


class Tenant(SQLModel, table=True):
    tenant_id: str = Field(primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class User(SQLModel, table=True):
    user_id: str = Field(primary_key=True)
    tenant_id: str = Field(index=True)
    username: str = Field(index=True)
    password_hash: str
    role: Role = Field(default=Role.user)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class File(SQLModel, table=True):
    file_id: str = Field(primary_key=True)
    tenant_id: str = Field(index=True)
    user_id: str = Field(index=True)
    # 파일 경로를 의미. 파일 경로는 중복되면 안되므로 고유값 강제(unique=True) 옵션을 설정함.
    object_key: str = Field(index=True, unique=True)
    content_type: str
    size_bytes: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Job(SQLModel, table=True):
    job_id: str = Field(primary_key=True)
    tenant_id: str = Field(index=True)
    user_id: str = Field(index=True)
    source_object_key: str
    result_object_key: Optional[str] = None
    status: JobStatus = Field(default=JobStatus.Queued, index=True)
    fail_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(SQLModel, table=True):
    event_id: str = Field(primary_key=True)
    tenant_id: str = Field(index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    action: str = Field(index=True)
    target_type: str
    target_id: Optional[str] = Field(default=None, index=True)
    request_id: str = Field(index=True)
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)

#======================================================================