#======================================================================
# [ config.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.18
#======================================================================

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 설정값은 .env 파일에서 찾고, 오류 발생 시 ignore
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 해당 프로젝트가 현재 로컬 기반인지, 또는 실제 운영중인지 결정하는 값
    ENV: str = "local"
    # 로그응 어느 수준까지 출력할지 결정하는 값
    LOG_LEVEL: str = "INFO"

settings = Settings()

#======================================================================