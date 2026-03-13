# ============================================================
# 유앤아이의원 장비 현황 대시보드 — 설정 (NAS 버전)
# Developed by smartbranding
# ============================================================

BRANDING = "Developed by smartbranding"

# ============================================================
# 역할 정의
# ============================================================
# viewer  : 읽기 전용 (전체 지점 조회)
# branch  : 지점 담당자 — 자기 지점만 조회/편집 가능 (branch_id 기반 필터링)
# editor  : 본사 편집자 — 전체 지점 편집 가능
# admin   : 관리자 — 모든 기능 + 사용자 관리 + 동기화
ROLES = {
    "viewer": {
        "label": "뷰어",
        "can_edit_photo": False,
        "can_save": False,
        "can_sync": False,
        "can_manage_users": False,
        "can_edit_dictionary": False,
    },
    "branch": {
        "label": "지점담당",
        "can_edit_photo": True,
        "can_save": True,
        "can_sync": False,
        "can_manage_users": False,
        "can_edit_dictionary": False,
    },
    "editor": {
        "label": "편집자",
        "can_edit_photo": True,
        "can_save": True,
        "can_sync": False,
        "can_manage_users": False,
        "can_edit_dictionary": True,
    },
    "admin": {
        "label": "관리자",
        "can_edit_photo": True,
        "can_save": True,
        "can_sync": True,
        "can_manage_users": True,
        "can_edit_dictionary": True,
    },
}

# ============================================================
# 이벤트 수집 설정
# ============================================================
# EVENT_SHEET_ID, GOOGLE_CREDENTIALS_FILE은 환경변수 또는
# docker-compose.yml의 environment에서 설정합니다.

# braw CSV URL (Google Sheets 공개 CSV — 동기화용)
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vT7kB-eQbBWxfLRB4mCoCfw-2nz7J2QhA5xmiwSxer2U8IPuNdqnm_"
    "-TR2i-BGqwpuoUeW6y8RzRdXV/pub"
    "?gid=1543424723&single=true&output=csv"
)

# 사진 있음 판정 값
PHOTO_YES = {"0", "0.0", "1", "1.0", "o", "O", "ㅇ", "있음", "v", "완료", "y", "yes"}

# 기기명 정규화 (유사 장비 그룹핑)
DEVICE_ALIASES = {
    "슈링크 유니버스": ["슈링크 유니버스", "슈링크유니버스", "유니버스슈링크", "유니버스 슈링크"],
    "울쎄라피 프라임": ["울쎄라피 프라임", "울쎄라피프라임", "울쎄라피 프라임/", "울쎄라"],
    "써마지FLX": ["써마지FLX", "써마지 FLX", "써마지flx", "써마지 flx", "미니 써마지"],
    "써마지": ["써마지"],
    "인모드": ["인모드"],
    "바디인모드": ["바디인모드", "바디 인모드", "인모드 (바디", "인모드(바디"],
    "클라리티2": ["클라리티2", "클라리티 2"],
    "클라리티 롱펄": ["클라리티 롱펄", "클라리티롱펄"],
    "보톡스": ["보톡스"],
    "리쥬란": ["리쥬란"],
    "쥬베룩": ["쥬베룩"],
    "올리지오X": ["올리지오X", "올리지오x", "올리지오 X"],
    "볼뉴머": ["볼뉴머"],
    "온다리프팅": ["온다리프팅", "온다 리프팅"],
    "필러": ["필러"],
}
