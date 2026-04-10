# =================================================================================
# 파일명:   bulid_exe.py
# 목적:     실행파일 패키징 작업 자동화
# =================================================================================

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# =================================================================================

# 로컬 장치의 프로젝트 폴더 위치(루트) 확인
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    root = _repo_root()
    dist_dir = root / "dist"
    build_dir = root / "build"
    spec_path = root / "watermark.spec"

    # 로컬에 Pyinstaller가 설치되어 있는지 확인
    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        print("error: pyinstaller 가 설치되어 있지 않습니다. `python -m pip install -e \".[dev]\"` 를 실행하세요.", file=sys.stderr)
        return 2

    # 로컬에 cli/main.py 파일이 올바른 위치에 정상적으로 존재하는지 확인
    entry = root / "cli" / "main.py"
    if not entry.exists():
        print(f"error: entrypoint not found: {entry}", file=sys.stderr)
        return 2

    # 이전 빌드 결과물 파일 정리
    '''
    매 실행파일 패키징 작업마다 /dist, /build 폴더와 .spec 파일이 생성되므로,
    패키징 작업 수행 전 이전 패키징 결과로 생성된 폴더와 파일들을 삭제할 필요가 있음(필수는 아님)
    '''
    for p in (dist_dir, build_dir, spec_path):
        try:
            if p.is_dir():
                shutil.rmtree(p)
            elif p.is_file():
                p.unlink()
        except OSError:
            pass

# =================================================================================
# 파일명:   패키징 작업 지시사항 정리
# =================================================================================

    cmd = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--onefile",

        # 로컬에 본 프로젝트에서 사용되지 않는 라이브러리가(matplotlib 등) 설치되어 있으면 
        # 불필요한 hook으로 빌드가 깨질 수 있어 제외
        "--exclude-module",
        "matplotlib",

        # 일부 환경에서 setuptools/pkg_resources hook이 깨지는 사례가 있어 제외
        "--exclude-module",
        "setuptools",
        "--exclude-module",
        "pkg_resources",

        # 테스트 도구(pytest 등)는 실행파일에 불필요
        "--exclude-module",
        "pytest",

        # 실행파일 이름
        "--name",
        "watermark",
        str(entry),
    ]

    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(root))
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

