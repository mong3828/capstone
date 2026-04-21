# =================================================================================
# 파일명:   test_mintmark_stats.py
# 목적:     워터마크 모듈 내 통계 유틸 단위 테스트
# =================================================================================

from core.watermark import calculate_z_score, hash_mod

# 비밀키, 고유키가 같으면 난수 결과도 똑같이 나오는가?
def test_hash_mod_deterministic():
    assert hash_mod("k", "row1", 7) == hash_mod("k", "row1", 7)

# 전체 데이터 10개의 green:red 비율이 5:5이면 z검정 결과가 0에 가깝게 나오는가?
def test_calculate_z_score_symmetric():
    z = calculate_z_score(5, 10)
    assert abs(z) < 0.01
