import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

from config import BRANDING
from auth import require_auth, get_permissions, get_user_branch_id, get_current_role, show_user_info_sidebar
from equipment.db import load_data, apply_photo_status, apply_filters, get_branch_name, get_branches
from ui_tabs import (
    render_tab_equipment,
    render_tab_events,
    render_tab_cafe,
    render_tab_blog,
    render_tab_dashboard,
    render_admin_panel,
    render_tab_guide,
)

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="유앤아이의원 장비 현황",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 글로벌 CSS  +  다크 모드 CSS (CSS 변수 시스템)
# ============================================================
st.markdown("""<style>
/* ================================================================
   CSS 변수 — 라이트 모드 (기본값)
   ================================================================ */
:root {
    --bg-primary: #FFFFFF;
    --bg-secondary: #F8FAFC;
    --bg-card: #FFFFFF;
    --border: #E2E8F0;
    --border-light: #F1F5F9;
    --text-primary: #1E293B;
    --text-secondary: #64748B;
    --text-muted: #94A3B8;
    --accent: #2563EB;
    --accent-light: #DBEAFE;
    --accent-hover: #1D4ED8;
    --success: #059669;
    --success-light: #D1FAE5;
    --warning: #D97706;
    --warning-light: #FEF3C7;
    --danger: #DC2626;
    --danger-light: #FEE2E2;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
    --radius-sm: 6px;
    --radius: 10px;
    --radius-lg: 14px;
}

/* ================================================================
   CSS 변수 — 다크 모드
   ================================================================ */
html.dark-theme {
    --bg-primary: #0F172A;
    --bg-secondary: #1E293B;
    --bg-card: #1E293B;
    --border: #334155;
    --border-light: #1E293B;
    --text-primary: #F1F5F9;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    --accent: #3B82F6;
    --accent-light: #1E3A5F;
    --accent-hover: #60A5FA;
    --success: #34D399;
    --success-light: #064E3B;
    --warning: #FBBF24;
    --warning-light: #78350F;
    --danger: #F87171;
    --danger-light: #7F1D1D;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.2);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.25), 0 2px 4px -2px rgba(0,0,0,0.15);
}

/* ================================================================
   공통 레이아웃 — 뷰포트 100vh 완전 맞춤 (스크롤 자체 차단)
   ================================================================ */
html, body, .stApp {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
}
[data-testid="stToolbar"] > div > div:last-child { display: none !important; }
.block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}

/* 상단 여백 압축 — Streamlit 위젯 간격 최소화 */
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div {
    margin-bottom: -0.25rem;
}
[data-testid="stMain"] .stSelectbox,
[data-testid="stMain"] .stTextInput {
    margin-bottom: 0 !important;
}
[data-testid="stMain"] .stRadio {
    margin-top: -0.25rem !important;
    margin-bottom: -0.25rem !important;
}

/* 사이드바: 100vh 맞춤 */
section[data-testid="stSidebar"] > div {
    max-height: 100vh !important;
    overflow: hidden !important;
}

/* 메인: 100vh 맞춤, 스크롤 자체 차단 */
[data-testid="stMain"] {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
}

/* sticky 탭을 위한 overflow 해제 (stMain 하위만) */
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlockBorderWrapper"],
.main .block-container {
    overflow: visible !important;
}

/* ================================================================
   페이지 배경 + 텍스트
   ================================================================ */
.stApp,
[data-testid="stAppViewContainer"] {
    background-color: var(--bg-secondary) !important;
}
html.dark-theme .stApp,
html.dark-theme [data-testid="stAppViewContainer"] {
    background-color: var(--bg-primary) !important;
}
/* 헤더: 배경은 숨기되 사이드바 토글 버튼은 유지 */
header[data-testid="stHeader"] {
    background: transparent !important;
    border: none !important;
    height: auto !important;
    min-height: 0 !important;
}
/* 헤더 내부 장식 요소만 숨김 (토글 버튼 제외) */
header[data-testid="stHeader"] [data-testid="stDecoration"] {
    display: none !important;
}
/* 사이드바 토글(열기) 버튼 항상 표시 */
button[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    z-index: 9999 !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    box-shadow: var(--shadow-md) !important;
}

/* 텍스트 컬러 */
html.dark-theme .stApp p, html.dark-theme .stApp span,
html.dark-theme .stApp label, html.dark-theme .stApp div,
html.dark-theme [data-testid="stMarkdownContainer"] *,
html.dark-theme [data-testid="stWidgetLabel"] *,
html.dark-theme .stRadio label span,
html.dark-theme .stSelectbox label,
html.dark-theme .stMultiSelect label,
html.dark-theme h1, html.dark-theme h2, html.dark-theme h3,
html.dark-theme h4, html.dark-theme h5, html.dark-theme h6 {
    color: var(--text-primary) !important;
}

/* ================================================================
   사이드바
   ================================================================ */
section[data-testid="stSidebar"] > div {
    background-color: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
}

/* 사이드바 브랜드 */
.sidebar-brand {
    padding: 0.25rem 0 0.5rem 0;
    margin-bottom: 0.25rem;
    border-bottom: 2px solid var(--accent);
}
.sidebar-brand h3 {
    color: var(--text-primary) !important;
    font-size: 1.05rem !important;
    margin: 0 !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}
.sidebar-brand p {
    color: var(--text-muted) !important;
    font-size: 0.72rem !important;
    margin: 0.1rem 0 0 0 !important;
    font-weight: 400 !important;
}

/* 사이드바 필터 그룹 카드 */
.filter-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.85rem;
    margin-bottom: 0.75rem;
}
html.dark-theme .filter-card {
    background: var(--bg-primary);
}
.filter-label {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    margin-bottom: 0.4rem !important;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

/* ================================================================
   사이드바 내비게이션 라디오 (관리 포탈 스타일)
   ================================================================ */
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
    gap: 0.125rem !important;
    padding: 0 !important;
}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
    background: transparent !important;
    border: none !important;
    border-radius: 0.375rem !important;
    border-left: 3px solid transparent !important;
    padding: 0.5rem 0.75rem !important;
    margin: 0 !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    display: flex !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label p,
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label span {
    color: var(--text-secondary) !important;
    transition: color 0.15s ease !important;
}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
    background: var(--accent-light) !important;
    border-left-color: var(--accent) !important;
}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover p,
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover span {
    color: var(--accent) !important;
}
/* 선택된 항목 */
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) {
    background: var(--accent) !important;
    border-left-color: var(--accent) !important;
    box-shadow: 0 1px 3px rgba(37,99,235,0.3) !important;
}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) p,
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) span,
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) div {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
/* 라디오 원형 숨김 */
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}

/* ================================================================
   탭 — 필(Pill) 스타일 (서브뷰용)
   ================================================================ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem !important;
    background: var(--bg-card) !important;
    border-radius: 0 !important;
    padding: 0.35rem 0.5rem !important;
    border: none !important;
    border-bottom: 1px solid var(--border) !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.06) !important;
    position: sticky !important;
    top: 0 !important;
    z-index: 999 !important;
}
html.dark-theme .stTabs [data-baseweb="tab-list"] {
    background: var(--bg-card) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) !important;
    padding: 0.55rem 1.1rem !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
    background: transparent !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: var(--accent-light) !important;
    color: var(--accent) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: var(--shadow-sm) !important;
}
html.dark-theme .stTabs [aria-selected="true"] {
    color: white !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 0.75rem; }

/* ================================================================
   메트릭 카드
   ================================================================ */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 0.9rem 1.1rem !important;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stMetric"]:hover {
    box-shadow: var(--shadow-md) !important;
    border-color: var(--accent) !important;
}
[data-testid="stMetric"] label {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    color: var(--text-muted) !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
}

/* ================================================================
   버튼
   ================================================================ */
.stButton button {
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1rem !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    transition: all 0.2s ease !important;
    box-shadow: var(--shadow-sm) !important;
}
.stButton button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: var(--shadow-md) !important;
    transform: translateY(-1px);
}
.stButton button[kind="primary"] {
    background: var(--accent) !important;
    color: white !important;
    border-color: var(--accent) !important;
}
.stButton button[kind="primary"]:hover {
    background: var(--accent-hover) !important;
    color: white !important;
}

/* ================================================================
   입력 필드 / 셀렉트
   ================================================================ */
html.dark-theme .stTextInput input,
html.dark-theme .stTextArea textarea,
html.dark-theme [data-baseweb="select"] > div,
html.dark-theme [data-baseweb="input"] > div {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
/* 다크모드 placeholder 텍스트 */
html.dark-theme .stTextInput input::placeholder,
html.dark-theme .stTextArea textarea::placeholder {
    color: var(--text-muted) !important;
    opacity: 1 !important;
}
/* 다크모드 인라인 코드 (역할 뱃지 등) */
html.dark-theme code,
html.dark-theme .stMarkdown code {
    color: var(--accent) !important;
    background-color: var(--accent-light) !important;
}
html.dark-theme [data-baseweb="tag"] { background-color: var(--accent-light) !important; }
html.dark-theme [data-baseweb="popover"] > div,
html.dark-theme [data-baseweb="menu"] { background-color: var(--bg-card) !important; }
html.dark-theme [data-baseweb="menu"] li { color: var(--text-primary) !important; }
html.dark-theme [data-baseweb="menu"] li:hover { background-color: var(--accent-light) !important; }

[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
.stTextInput input {
    border-radius: var(--radius-sm) !important;
}

/* ================================================================
   툴팁
   ================================================================ */
html.dark-theme [data-testid="stTooltipContent"],
html.dark-theme [data-baseweb="tooltip"] [role="tooltip"],
html.dark-theme [data-testid="stTooltipContent"] p,
html.dark-theme [data-testid="stTooltipContent"] div {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
}

/* ================================================================
   데이터프레임 / 테이블
   ================================================================ */
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-sm) !important;
}
/* 다크모드: dataframe iframe 내부 배경 강제 */
html.dark-theme [data-testid="stDataFrame"] iframe {
    filter: none !important;
}
html.dark-theme [data-testid="stDataFrame"] {
    background: var(--bg-card) !important;
}

/* ================================================================
   다크모드: number_input / slider
   ================================================================ */
html.dark-theme .stNumberInput input,
html.dark-theme .stNumberInput [data-baseweb="input"] > div {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
html.dark-theme .stNumberInput button {
    background-color: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
html.dark-theme .stSlider [data-baseweb="slider"] div {
    color: var(--text-primary) !important;
}

/* ================================================================
   다크모드: 서브뷰 라디오 (horizontal)
   ================================================================ */
html.dark-theme .stRadio[data-testid="stRadio"] > div[role="radiogroup"][aria-label] > label {
    color: var(--text-secondary) !important;
}
html.dark-theme .stRadio > div[role="radiogroup"] > label:has(input:checked) {
    color: white !important;
}

/* ================================================================
   다크모드: multiselect
   ================================================================ */
html.dark-theme .stMultiSelect [data-baseweb="select"] > div {
    background-color: var(--bg-primary) !important;
    border-color: var(--border) !important;
}
html.dark-theme .stMultiSelect [data-baseweb="tag"] {
    background-color: var(--accent) !important;
    color: white !important;
}
html.dark-theme .stMultiSelect [data-baseweb="tag"] span {
    color: white !important;
}

/* ================================================================
   다크모드: expander / info / warning / success
   ================================================================ */
html.dark-theme [data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border-color: var(--border) !important;
}
html.dark-theme [data-testid="stExpander"] summary,
html.dark-theme [data-testid="stExpander"] p,
html.dark-theme [data-testid="stExpander"] li,
html.dark-theme [data-testid="stExpander"] td,
html.dark-theme [data-testid="stExpander"] th,
html.dark-theme [data-testid="stExpander"] strong,
html.dark-theme [data-testid="stExpander"] span,
html.dark-theme [data-testid="stExpander"] ol,
html.dark-theme [data-testid="stExpander"] ul {
    color: var(--text-primary) !important;
}
html.dark-theme [data-testid="stExpander"] table {
    border-color: var(--border) !important;
}
html.dark-theme [data-testid="stExpander"] td,
html.dark-theme [data-testid="stExpander"] th {
    border-color: var(--border) !important;
}
html.dark-theme [data-testid="stAlert"] {
    background: var(--bg-secondary) !important;
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
}
html.dark-theme .stDownloadButton button {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}

/* ================================================================
   다크모드: plotly 차트 배경
   ================================================================ */
html.dark-theme [data-testid="stPlotlyChart"] {
    background: transparent !important;
}

/* ================================================================
   구분선 / 기타
   ================================================================ */
hr, [data-testid="stDivider"] { border-color: var(--border) !important; opacity: 0.6 !important; }
html.dark-theme [data-testid="stCaptionContainer"] * { color: var(--text-muted) !important; }
.stProgress > div > div { background-color: var(--accent) !important; border-radius: 4px !important; }
.stProgress > div { background-color: var(--border) !important; border-radius: 4px !important; }

/* ================================================================
   다이얼로그 (관련 이벤트 팝업) — 중앙 정렬 + 크기 확장
   ================================================================ */
[data-testid="stModal"] > div {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stModal"] > div > div {
    width: 92vw !important;
    max-width: 1300px !important;
    min-width: 800px !important;
    max-height: 90vh !important;
}
[data-testid="stModal"] [data-testid="stVerticalBlock"] {
    width: 100% !important;
}
/* 다이얼로그 내부 AG-Grid iframe 높이 확장 */
[data-testid="stModal"] iframe {
    min-height: 55vh !important;
    height: 60vh !important;
}
/* dialog fallback selectors */
div[role="dialog"] {
    max-width: 90vw !important;
    width: 90vw !important;
    min-width: 800px !important;
}
div[role="dialog"] > div {
    width: 100% !important;
    max-height: 90vh !important;
    overflow-y: auto !important;
}
</style>""", unsafe_allow_html=True)

# ============================================================
# 다크 모드 JS 토글 (페이지 리로드 없이 CSS 클래스만 전환)
# ============================================================
components.html("""
<script>
(function() {
  var pd = window.parent.document;
  var html = pd.documentElement;
  var KEY = 'uandi_dark_mode';

  /* 1. localStorage → 즉시 클래스 적용 */
  var isDark = localStorage.getItem(KEY) === 'true';
  if (isDark) html.classList.add('dark-theme');
  else html.classList.remove('dark-theme');

  /* 2. iframe + Streamlit 테마 변수 동기화 */
  function syncIframes(dark) {
    pd.querySelectorAll('iframe').forEach(function(f) {
      try {
        var d = f.contentDocument || f.contentWindow.document;
        if (dark) d.documentElement.classList.add('dark-theme');
        else d.documentElement.classList.remove('dark-theme');
      } catch(e) {}
    });
    /* Streamlit 내부 CSS 변수 변경 — dataframe(Glide) 테마 반영 */
    var root = pd.documentElement.style;
    if (dark) {
      root.setProperty('--primary-color', '#3B82F6');
      root.setProperty('--background-color', '#0F172A');
      root.setProperty('--secondary-background-color', '#1E293B');
      root.setProperty('--text-color', '#F1F5F9');
    } else {
      root.setProperty('--primary-color', '#2563EB');
      root.setProperty('--background-color', '#F8FAFC');
      root.setProperty('--secondary-background-color', '#FFFFFF');
      root.setProperty('--text-color', '#1E293B');
    }
  }
  syncIframes(isDark);

  /* 3. 플로팅 토글 버튼 */
  var old = pd.getElementById('dark-toggle');
  if (old) old.remove();

  var btn = pd.createElement('button');
  btn.id = 'dark-toggle';
  function applyBtnStyle() {
    var d = html.classList.contains('dark-theme');
    btn.textContent = d ? '\\u2600\\uFE0F' : '\\uD83C\\uDF19';
    btn.style.background = d ? '#262730' : '#F0F2F6';
    btn.style.borderColor = d ? '#3A3A5A' : '#D0D0D0';
    btn.style.color = d ? '#FFF' : '#000';
  }
  btn.style.cssText = 'position:fixed;right:0;top:50%;transform:translateY(-50%);z-index:999999;'
    + 'font-size:18px;border:1px solid;border-radius:8px 0 0 8px;width:32px;height:48px;'
    + 'display:flex;align-items:center;justify-content:center;cursor:pointer;'
    + 'box-shadow:-2px 0 6px rgba(0,0,0,.2);transition:background .2s,color .2s;';
  applyBtnStyle();

  btn.addEventListener('click', function() {
    html.classList.toggle('dark-theme');
    var nowDark = html.classList.contains('dark-theme');
    localStorage.setItem(KEY, nowDark);
    applyBtnStyle();
    syncIframes(nowDark);
  });
  pd.body.appendChild(btn);

  /* 4. 새로 추가되는 iframe 자동 동기화 (AG-Grid 지연 렌더링 대응) */
  new MutationObserver(function() {
    syncIframes(html.classList.contains('dark-theme'));
  }).observe(pd.body, { childList: true, subtree: true });

  /* 5. 탭 전환 잔상 방지 — 사이드바 라디오 변경 시 메인 영역 즉시 숨김 */
  (function() {
    var sb = pd.querySelector('[data-testid="stSidebar"]');
    if (!sb) return;
    var lastVal = '';
    sb.addEventListener('change', function(e) {
      if (e.target.type !== 'radio') return;
      var cur = e.target.value || '';
      if (lastVal && cur !== lastVal) {
        var main = pd.querySelector('[data-testid="stMain"]');
        if (main) {
          main.style.opacity = '0';
          main.style.transition = 'none';
        }
      }
      lastVal = cur;
    });
    /* Streamlit 렌더링 완료 감지 → 메인 영역 복원 */
    new MutationObserver(function() {
      var main = pd.querySelector('[data-testid="stMain"]');
      if (!main || main.style.opacity !== '0') return;
      var status = pd.querySelector('[data-testid="stStatusWidget"]');
      var isRunning = status && status.querySelector('[data-testid="stLoading"]');
      if (!isRunning) {
        main.style.transition = 'opacity 0.12s ease';
        main.style.opacity = '1';
      }
    }).observe(pd.body, { childList: true, subtree: true, attributes: true });
  })();

  /* 6. 뷰포트 맞춤 — 그리드 iframe 높이를 동적으로 계산 */
  (function() {
    function fitGrids() {
      var vh = window.innerHeight || pd.documentElement.clientHeight;
      var grids = pd.querySelectorAll('.equip-grid, .evt-grid');
      grids.forEach(function(wrap) {
        var iframe = wrap.querySelector('iframe');
        if (!iframe) return;
        /* iframe 상단 위치 측정 */
        var rect = iframe.getBoundingClientRect();
        /* 하단 여백 130px (선택 정보 바 + 버튼 행) */
        var h = vh - rect.top - 130;
        if (h < 300) h = 300;
        iframe.style.height = h + 'px';
      });
    }
    /* 초기 + DOM 변경 시 재계산 */
    var timer = null;
    function debouncedFit() {
      clearTimeout(timer);
      timer = setTimeout(fitGrids, 200);
    }
    new MutationObserver(debouncedFit).observe(pd.body, { childList: true, subtree: true });
    window.addEventListener('resize', debouncedFit);
    setTimeout(fitGrids, 500);
    setTimeout(fitGrids, 1500);
  })();
})();
</script>
""", height=0)

# ============================================================
# 인증 게이트
# ============================================================
if not require_auth():
    st.stop()
permissions = get_permissions()

# ============================================================
# 지점 목록 (가벼운 쿼리 — 장비 전체 데이터는 장비 탭에서만 로딩)
# ============================================================
all_branches = sorted(b["name"] for b in get_branches())

# branch 역할 확인
is_branch_role = get_current_role() == "branch"
user_branch_name = None
if is_branch_role:
    user_branch_name = get_branch_name(get_user_branch_id())

# ============================================================
# 사이드바 — 내비게이션 + 지점 필터
# ============================================================
with st.sidebar:
    st.markdown("""<style>
    section[data-testid="stSidebar"] .block-container { padding-top: 0.5rem; }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { margin-bottom: -0.35rem; }
    section[data-testid="stSidebar"] hr { margin: 0.4rem 0 !important; opacity: 0.2; }
    section[data-testid="stSidebar"] .stSelectbox { margin-top: 0rem; margin-bottom: 0rem; }
    section[data-testid="stSidebar"] .filter-label { margin-top: 0.2rem !important; }
    </style>""", unsafe_allow_html=True)

    # 브랜드 섹션
    st.markdown("""
    <div class="sidebar-brand">
        <h3>유앤아이의원</h3>
        <p>통합 관리 시스템</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 지점 필터 (모든 탭에서 노출) ──
    st.markdown('<div class="filter-label">지점</div>', unsafe_allow_html=True)
    if is_branch_role and user_branch_name:
        st.info(f"담당 지점: {user_branch_name}")
        st.session_state["_shared_branches"] = [user_branch_name]
    else:
        b_set = set(all_branches)
        try:
            from events.db import load_evt_branches as _leb
            b_set.update(b["name"] for b in _leb())
        except Exception:
            pass
        b_opts = sorted(b_set)
        sel_bs = st.multiselect("지점", b_opts, default=[], key="_sb_branches",
                                 placeholder="전체 (지점 선택)", label_visibility="collapsed")
        st.session_state["_shared_branches"] = sel_bs

    st.markdown("---")

    # ── 내비게이션 ──
    st.markdown('<div class="filter-label" style="margin-bottom:0.15rem !important;">메뉴</div>', unsafe_allow_html=True)
    menu_items = ["HOME", "보유장비", "이벤트", "카페", "블로그", "가이드"]
    if permissions["can_manage_users"]:
        menu_items.append("사용자 관리")

    # 대시보드 카드 클릭 → _goto_menu 플래그 → radio 기본값 설정
    _goto = st.session_state.pop("_goto_menu", None)
    if _goto and _goto in menu_items:
        st.session_state["nav_menu"] = _goto

    selected_menu = st.radio(
        "메뉴", menu_items, key="nav_menu", label_visibility="collapsed",
    )

    # 푸터
    st.markdown(f"""
    <div style="margin-top:0.5rem; padding-top:0.5rem; border-top:1px solid var(--border);
                text-align:center; font-size:0.65rem; color:var(--text-muted);">
        마지막 로딩: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
        {len(all_branches)}개 지점 · v2.0
    </div>
    """, unsafe_allow_html=True)
    show_user_info_sidebar()
    st.markdown(f"<div style='text-align:center;font-size:0.65rem;color:var(--text-muted);margin-top:0.25rem;'>{BRANDING}</div>", unsafe_allow_html=True)

# ============================================================
# 메인 영역 라우팅
# ============================================================
_main = st.empty()
with _main.container():
    if selected_menu == "HOME":
        render_tab_dashboard(permissions)

    elif selected_menu == "보유장비":
        df = load_data()
        df = apply_photo_status(df)
        if is_branch_role and user_branch_name:
            df = df[df["지점명"] == user_branch_name].copy()
        _branches = st.session_state.get("_shared_branches", [])
        branch_df = apply_filters(df, _branches, [], "", "전체")
        render_tab_equipment(branch_df, df, _branches, permissions)

    elif selected_menu == "이벤트":
        render_tab_events()

    elif selected_menu == "카페":
        render_tab_cafe()

    elif selected_menu == "블로그":
        render_tab_blog()

    elif selected_menu == "가이드":
        render_tab_guide()

    elif selected_menu == "사용자 관리":
        render_admin_panel()
