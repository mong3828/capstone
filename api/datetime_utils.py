# =================================================================================
# 파일명:   datetime_utils.py
# 목적:     datetime(naive)와 UTC aware now 비교 시 TypeError 방지
# =================================================================================

'''
TypeError: can't compare offset-naive and offset-aware datetimes
datetime에는 naive한 객체(절대 시간)와 aware한 객체(utc 기준의 상대 시간)가 존재함
SQLite에서 읽은 expires_at은 naive 객체이고, Python의 now는 timezone.utc가 붙어 있어 aware 객체임
따라서 DB에서 불러온 시간을 파이썬 코드에서 <= 비교 시 TypeError가 발생하게 되는 것 
그러므로 DB에서 읽은 시각을 UTC aware로 정규화하는 헬퍼를 추가할 필요가 있음
*참고: https://diane073.tistory.com/163
'''


from __future__ import annotations

from datetime import datetime, timezone

# ORM에서 로드한 값이 naive이면 UTC로 간주하고, aware이면 UTC로 변환함
def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
