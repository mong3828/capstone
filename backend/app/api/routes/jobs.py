#======================================================================
# [ main.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.19
#======================================================================

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import Subject, get_current_subject, get_db
from app.models import Job, JobStatus
from app.security.authorization import ensure_job_access

#======================================================================

router = APIRouter(prefix="/jobs", tags=["jobs"])

class CreateJobRequest(BaseModel):
    source_object_key: str

class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus

#======================================================================

# 작업 생성 함수
@router.post("", response_model=CreateJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    body: CreateJobRequest,
    # 사용자의 신원(subject)과 DB 작업 세션을 인가받음
    subject: Subject = Depends(get_current_subject),
    db: Session = Depends(get_db),
):
    # 작업에 고유 번호 할당
    job_id = uuid4().hex
    # 작업에 대한 유저의 소유권 정보 기록
    job = Job(
        job_id=job_id,
        tenant_id=subject.tenant_id,
        user_id=subject.user_id,
        source_object_key=body.source_object_key,
        status=JobStatus.Queued,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    # DB에 작업 저장
    db.add(job)
    db.commit()
    return CreateJobResponse(job_id=job_id, status=job.status)

#======================================================================

# 작업 조회 및 
@router.get("/{job_id}")
def get_job(
    job_id: str,
    subject: Subject = Depends(get_current_subject),
    db: Session = Depends(get_db),
):
    # 유저가 제시한 작업 번호를 DB에 검색
    job = db.exec(select(Job).where(Job.job_id == job_id)).first()
    # 해당 작업번호에 해당하는 작업이 존재하지 않을 경우 에러코드 404
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    # 유저가 데이터 조회 권한을 만족하는지 확인
    ensure_job_access(subject, job)
    return job

#======================================================================