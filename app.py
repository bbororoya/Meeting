# -*- coding: utf-8 -*-
"""
미팅 동선 공유 지도 (참석자별 색 구분 + 비밀번호 잠금 버전)
- 앱 진입 시 비밀번호 확인
- 여러 사람이 같은 링크에서 미팅 정보를 입력
- 구글 시트에 저장 (공유 저장소)
- 카카오 API로 국내 주소를 좌표로 변환
- 참석자별로 마커 색과 동선 색을 다르게 표시
- 새로고침하면 지도에 마커 + 동선이 갱신됨
"""

import datetime as dt

import folium
import gspread
import pandas as pd
import requests
import streamlit as st
from folium.plugins import AntPath
from google.oauth2.service_account import Credentials
from streamlit_folium import st_folium

# ──────────────────────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="2026년 고양시 미팅 지도", page_icon="📍", layout="wide")

SHEET_HEADERS = ["미팅명", "주소", "일시", "참석자", "메모", "작성자", "lat", "lng"]

# 참석자별로 돌아가며 배정할 색 팔레트
# (folium 마커가 지원하는 색 이름, 동선 선에 쓸 hex 색)
COLOR_PALETTE = [
    ("blue", "#2A81CB"),
    ("red", "#CB2B3E"),
    ("green", "#2AAD27"),
    ("purple", "#9C2BCB"),
    ("orange", "#CB8427"),
    ("darkblue", "#214E76"),
    ("cadetblue", "#436978"),
    ("darkgreen", "#728224"),
]


# ──────────────────────────────────────────────────────────────
# 비밀번호 확인
# ──────────────────────────────────────────────────────────────
def check_password():
    """비밀번호가 맞아야 통과. 틀리거나 미입력이면 여기서 멈춤."""
    # secrets에 app_password가 없으면 잠금 비활성화(그냥 통과)
    if "app_password" not in st.secrets:
        return

    if st.session_state.get("password_ok"):
        return

    st.markdown("### 🔒 비밀번호를 입력하세요")
    pw = st.text_input("비밀번호", type="password", label_visibility="collapsed")
    if pw == "":
        st.stop()  # 아직 입력 안 함
    if pw == st.secrets["app_password"]:
        st.session_state["password_ok"] = True
        st.rerun()
    else:
        st.error("비밀번호가 틀렸습니다.")
        st.stop()


# ──────────────────────────────────────────────────────────────
# 구글 시트 연결
# ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["sheet_id"])
    ws = sh.sheet1
    if ws.row_values(1) != SHEET_HEADERS:
        ws.clear()
        ws.append_row(SHEET_HEADERS)
    return ws


def load_data(ws) -> pd.DataFrame:
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=SHEET_HEADERS)
    return df


# ──────────────────────────────────────────────────────────────
# 카카오 주소 → 좌표 (지오코딩)
# ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def geocode_kakao(address: str):
    """국내 주소를 (lat, lng)로 변환. 실패 시 (None, None)."""
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {st.secrets['kakao_rest_api_key']}"}
    try:
        resp = requests.get(url, headers=headers, params={"query": address}, timeout=5)
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        if not docs:
            return None, None
        return float(docs[0]["y"]), float(docs[0]["x"])  # (lat, lng)
    except Exception:
        return None, None


# ──────────────────────────────────────────────────────────────
# 참석자 → 색 매핑
# ──────────────────────────────────────────────────────────────
def build_color_map(participants):
    """참석자 이름 목록을 받아 {이름: (마커색, 선색hex)} 딕셔너리 반환."""
    uniq = sorted({(p if str(p).strip() else "미지정") for p in participants})
    return {name: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, name in enumerate(uniq)}


# ──────────────────────────────────────────────────────────────
# 입력 폼 (사이드바)
# ──────────────────────────────────────────────────────────────
def render_form(ws):
    st.sidebar.header("➕ 미팅 추가")
    with st.sidebar.form("add_meeting", clear_on_submit=True):
        name = st.text_input("미팅명 *")
        address = st.text_input("주소 *", placeholder="예: 서울 강남구 테헤란로 152")
        col1, col2 = st.columns(2)
        date = col1.date_input("날짜", dt.date.today())
        time = col2.time_input("시간", dt.time(10, 0))
        people = st.text_input("참석자 (색 구분 기준)")
        memo = st.text_area("메모", height=80)
        author = st.text_input("작성자 *")
        submitted = st.form_submit_button("지도에 추가", use_container_width=True)

    if submitted:
        if not (name and address and author):
            st.sidebar.error("미팅명 · 주소 · 작성자는 필수입니다.")
            return
        lat, lng = geocode_kakao(address)
        if lat is None:
            st.sidebar.error("주소를 찾지 못했습니다. 주소를 다시 확인해 주세요.")
            return
        when = f"{date.isoformat()} {time.strftime('%H:%M')}"
        ws.append_row([name, address, when, people, memo, author, lat, lng])
        st.sidebar.success(f"'{name}' 추가 완료!")
        st.rerun()


# ──────────────────────────────────────────────────────────────
# 지도 그리기
# ──────────────────────────────────────────────────────────────
def render_map(df: pd.DataFrame):
    df = df.dropna(subset=["lat", "lng"]).copy()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    df = df.dropna(subset=["lat", "lng"])
    if "참석자" not in df.columns:
        df["참석자"] = "미지정"
    df["참석자"] = df["참석자"].apply(lambda p: p if str(p).strip() else "미지정")
    if "일시" in df.columns:
        df = df.sort_values("일시")
    df = df.reset_index(drop=True)

    if df.empty:
        st.info("아직 등록된 미팅이 없습니다. 왼쪽에서 추가해 보세요.")
        return

    color_map = build_color_map(df["참석자"].tolist())

    # 범례
    chips = "  ".join(
        f"<span style='display:inline-block;width:12px;height:12px;"
        f"background:{hexc};border-radius:50%;margin-right:4px;'></span>{name}"
        for name, (_, hexc) in color_map.items()
    )
    st.markdown(f"**참석자별 색 구분:** {chips}", unsafe_allow_html=True)

    center = [df["lat"].mean(), df["lng"].mean()]
    m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

    all_coords = []
    # 마커 (참석자 색)
    for i, row in df.iterrows():
        order = i + 1
        marker_color, _ = color_map[row["참석자"]]
        all_coords.append((row["lat"], row["lng"]))
        popup_html = (
            f"<b>{order}. {row['미팅명']}</b><br>"
            f"🕒 {row.get('일시', '')}<br>"
            f"📍 {row['주소']}<br>"
            f"👥 {row['참석자']}<br>"
            f"📝 {row.get('메모', '')}<br>"
            f"<small>by {row.get('작성자', '')}</small>"
        )
        folium.Marker(
            [row["lat"], row["lng"]],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{order}. {row['미팅명']} | {row.get('일시', '')} | {row['주소']}",
            icon=folium.Icon(color=marker_color, icon="info-sign"),
        ).add_to(m)

    # 동선 (참석자별로 따로, 각자 색으로 시간순 연결)
    for name, group in df.groupby("참석자"):
        coords = list(zip(group["lat"], group["lng"]))
        if len(coords) >= 2:
            _, hexc = color_map[name]
            AntPath(coords, color=hexc, weight=4, delay=800).add_to(m)

    if len(all_coords) > 1:
        m.fit_bounds(all_coords)
    else:
        m.location = all_coords[0]
        m.zoom_start = 15

    st_folium(m, use_container_width=True, height=560, returned_objects=[])


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
def main():
    st.title("📍 미팅 동선 공유 지도")

    check_password()  # 비밀번호 통과해야 아래 내용이 보임

    st.caption("주소를 입력하면 지도에 위치와 동선이 표시됩니다. 참석자별로 색이 나뉘어요. 새로고침하면 갱신됩니다.")

    try:
        ws = get_worksheet()
    except Exception as e:
        st.error(
            "구글 시트에 연결하지 못했습니다. secrets 설정을 확인해 주세요.\n\n"
            f"상세: {e}"
        )
        st.stop()

    render_form(ws)

    if st.button("🔄 새로고침"):
        st.rerun()

    df = load_data(ws)
    render_map(df)

    with st.expander(f"📋 등록된 미팅 목록 ({len(df)}건)"):
        show_cols = [c for c in ["미팅명", "일시", "주소", "참석자", "메모", "작성자"] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
