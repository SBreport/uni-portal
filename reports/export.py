"""보고서 HTML 내보내기."""

from reports.generator import get_branch_report


def render_html_report(branch_id: int) -> str:
    """지점별 보고서를 HTML로 렌더링."""
    data = get_branch_report(branch_id)
    if not data:
        return "<html><body><h1>지점을 찾을 수 없습니다</h1></body></html>"

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{data['branch_name']} — 마케팅 보고서</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #334155; line-height: 1.6; padding: 40px; max-width: 800px; margin: 0 auto; }}
  h1 {{ font-size: 24px; margin-bottom: 8px; color: #1e293b; }}
  h2 {{ font-size: 18px; margin: 32px 0 12px; color: #475569; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
  .subtitle {{ font-size: 14px; color: #94a3b8; margin-bottom: 32px; }}
  .card {{ background: #f8fafc; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
  .stat {{ display: inline-block; margin-right: 24px; }}
  .stat-value {{ font-size: 24px; font-weight: 700; color: #3b82f6; }}
  .stat-label {{ font-size: 12px; color: #94a3b8; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }}
  th {{ text-align: left; padding: 8px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; font-weight: 600; }}
  td {{ padding: 8px; border-bottom: 1px solid #f1f5f9; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; }}
  .badge-blue {{ background: #dbeafe; color: #2563eb; }}
  .badge-green {{ background: #dcfce7; color: #16a34a; }}
  .badge-yellow {{ background: #fef9c3; color: #ca8a04; }}
  .badge-slate {{ background: #f1f5f9; color: #64748b; }}
  .print-btn {{ position: fixed; top: 20px; right: 20px; padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; }}
  @media print {{ .print-btn {{ display: none; }} }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">PDF 다운로드</button>
<h1>{data['branch_name']}</h1>
<p class="subtitle">마케팅 종합 보고서</p>
"""

    # 보유장비
    eq = data.get("equipment", {})
    html += f"""
<h2>보유장비</h2>
<div class="card">
  <div class="stat"><span class="stat-value">{eq.get('total', 0)}</span><br><span class="stat-label">전체 장비</span></div>
  <div class="stat"><span class="stat-value">{eq.get('with_photo', 0)}</span><br><span class="stat-label">사진 보유</span></div>
</div>
"""

    # 이벤트
    ev = data.get("events", {})
    html += f"""
<h2>이벤트</h2>
<div class="card">
  <div class="stat"><span class="stat-value">{ev.get('total', 0)}</span><br><span class="stat-label">등록 이벤트</span></div>
</div>
"""
    if ev.get("items"):
        html += "<table><tr><th>이벤트명</th><th>카테고리</th><th>이벤트가</th></tr>"
        for item in ev["items"][:10]:
            price = f"{int(item.get('event_price', 0) or 0):,}원" if item.get('event_price') else '-'
            html += f"<tr><td>{item.get('display_name', '')}</td><td>{item.get('category', '')}</td><td>{price}</td></tr>"
        html += "</table>"

    # 플레이스
    pl = data.get("place", {})
    html += f"""
<h2>플레이스 상위노출</h2>
<div class="card">
  <div class="stat"><span class="stat-value">{pl.get('exposed_days', 0)}</span><br><span class="stat-label">노출일</span></div>
  <div class="stat"><span class="stat-value">{pl.get('exposure_rate', 0)}%</span><br><span class="stat-label">노출률</span></div>
</div>
"""

    # 웹페이지
    wp = data.get("webpage", {})
    html += f"""
<h2>웹페이지 노출</h2>
<div class="card">
  <div class="stat"><span class="stat-value">{wp.get('exposed_days', 0)}</span><br><span class="stat-label">노출일</span></div>
  <div class="stat"><span class="stat-value">{wp.get('exposure_rate', 0)}%</span><br><span class="stat-label">노출률</span></div>
</div>
"""

    # 카페
    cafe = data.get("cafe", {})
    html += f"""
<h2>카페 마케팅</h2>
<div class="card">
  <div class="stat"><span class="stat-value">{cafe.get('total', 0)}</span><br><span class="stat-label">총 원고</span></div>
</div>
"""

    # 블로그
    blog = data.get("blog", {})
    html += f"""
<h2>블로그</h2>
<div class="card">
  <div class="stat"><span class="stat-value">{blog.get('total', 0)}</span><br><span class="stat-label">게시글</span></div>
</div>
"""

    # 민원
    comp = data.get("complaints", {})
    sc = comp.get("status_counts", {})
    html += f"""
<h2>민원 현황</h2>
<div class="card">
  <div class="stat"><span class="stat-value">{comp.get('total', 0)}</span><br><span class="stat-label">총 민원</span></div>
  <div class="stat"><span class="stat-value">{sc.get('received', 0) + sc.get('processing', 0)}</span><br><span class="stat-label">처리 대기</span></div>
  <div class="stat"><span class="stat-value">{sc.get('resolved', 0) + sc.get('closed', 0)}</span><br><span class="stat-label">처리 완료</span></div>
</div>
"""

    html += """
<p style="margin-top: 48px; text-align: center; font-size: 12px; color: #94a3b8;">
  Generated by 유앤아이의원 통합 관리 시스템
</p>
</body></html>"""

    return html
