#======================================================================
# [ authorization.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.19
#======================================================================

from __future__ import annotations

from fastapi import HTTPException, status

from app.api.deps import Subject
from app.models import Job, Role

'''
앞서 사용자가 서버에 업로드된 파일을 열람하기 위한 조건은 아래와 같이 정의하였음:
    1. 파일을 업로드한 유저와 같은 소속이어야 함        (tenant_id가 같음)
    2. 파일을 업로드한 유저 본인이거나 관리자여야 함    (user_id=user_id || user_id=admin)
ensure_job_access는 이러한 조건을 if문으로 그대로 구현한 함수임
'''

def ensure_job_access(subject: Subject, job: Job) -> None:
    """
    Week2 권한 모델(authz-model-v1.md)의 최소 구현.
    - 동일 tenant + (소유자 또는 admin)만 접근 허용
    """
    if subject.tenant_id != job.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if subject.user_id != job.user_id and subject.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

#======================================================================