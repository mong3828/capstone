#======================================================================
# [ logging.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.18
#======================================================================

import logging
import uuid
from contextvars import ContextVar

#======================================================================

_request_id: ContextVar[str] = ContextVar("request_id", default="")

# getID & setID는 사용자가 보낸 request_id가 존재하면 이를 사용하고, 없다면 uuid4().hex로 무작위 문자열을 새로 발급
def set_request_id(incoming: str | None) -> str:
    rid = (incoming or "").strip() or uuid.uuid4().hex
    _request_id.set(rid)
    return rid
def get_request_id() -> str:
    rid = _request_id.get()
    return rid or uuid.uuid4().hex

# 파이썬의 로깅 과정에 개입해 해당 로그가 어떤 request_id에서 발생했는지에 대한 정보를 추가하는 클래스
# 참고: https://velog.io/@qlgks1/python-python-logging-%ED%95%B4%EB%B6%80
class RequestIdFilter(logging.Filter):
    # 로그에 저장되는 객체에 request_id 칸을 추가
    def filter(self, record: logging.LogRecord) -> bool:
        # 현재 작업중인 request_id를 해당 칸에 출력함
        record.request_id = get_request_id()
        return True

# main.py 최초 실행시 함께 실행되어 로그 형식을 정의하는 함수
def configure_logging(*, log_level: str) -> None:
    # 로그 형식 정의
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s request_id=%(request_id)s %(name)s: %(message)s",
    )
    # 모든 핸들러에게 해당 로그 형식을 따르도록 설정
    for handler in logging.getLogger().handlers:
        handler.addFilter(RequestIdFilter())
        
#======================================================================