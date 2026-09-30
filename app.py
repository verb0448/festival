"""
🎪 축제 찾아줘 - 2026 전국 지역축제
=========================================

## 📂 데이터는 어디서 읽나요?
앱과 같은 저장소에 들어 있는 **`data/festivals_2026.csv`** 를 바로 읽어요. (구글 시트·secrets 설정이 필요 없어요!)

- 컬럼(1행): `축제명 | 카테고리 | 시작일 | 종료일 | 주소 | 위도 | 경도 | 참고_링크 | 이미지_URL`
- 날짜는 `2026-10-01`, `2026.10.01`, `2026/10/1` 다 OK.
  일(日)이 미정이면 `2026-10-미정`, 월까지 미정이면 `2026-미정` → "일정 미정"으로 표시해요. 비어 있으면 "상시".
- 지역(서울·부산…) 필터는 `주소` 앞부분에서 자동으로 뽑아요.
- 데이터를 고치려면 CSV를 수정해서 저장소에 올리면 돼요. (`이미지_URL` 칸을 채우면 카드에 사진이 떠요)
- CSV가 없으면 `sample_data.csv` 로 **데모 모드**가 켜져요.
"""

from __future__ import annotations

import calendar
import html
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import pydeck as pdk
import streamlit as st

# ──────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="🎪 축제 찾아줘 - 2026 전국 지역축제",
    page_icon="🎪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

COLUMNS = ["축제명", "카테고리", "시작일", "종료일", "주소", "위도", "경도", "참고_링크", "이미지_URL"]
DATA_CSV = Path(__file__).parent / "data" / "festivals_2026.csv"
SAMPLE_CSV = Path(__file__).parent / "sample_data.csv"
KST = timezone(timedelta(hours=9))
PAGE_SIZE = 9

CAT_EMOJI = {"문화예술": "🎨", "자연생태": "🌿", "주민화합": "🤝", "전통역사": "🏯", "지역특산물": "🍎"}
# 주소 앞부분 → 짧은 지역명
REGION_PREFIX = [
    ("서울", "서울"), ("부산", "부산"), ("대구", "대구"), ("인천", "인천"), ("광주", "광주"), ("대전", "대전"),
    ("울산", "울산"), ("세종", "세종"), ("경기", "경기"), ("강원", "강원"), ("충청북", "충북"), ("충북", "충북"),
    ("충청남", "충남"), ("충남", "충남"), ("전북", "전북"), ("전라북", "전북"), ("전남", "전남"), ("전라남", "전남"),
    ("경상북", "경북"), ("경북", "경북"), ("경상남", "경남"), ("경남", "경남"), ("제주", "제주"),
]
REGION_ORDER = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
                "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
STATUS_RGB = {"open": [255, 61, 113], "soon": [25, 211, 162], "tbd": [255, 176, 0], "ended": [166, 158, 150]}
GRADIENTS = [
    "linear-gradient(135deg,#FFE0B8,#FFB3C7)",
    "linear-gradient(135deg,#C8F7E6,#FFF0A8)",
    "linear-gradient(135deg,#FFD6A5,#FF9DB8)",
    "linear-gradient(135deg,#FFF0A8,#FFC9A8)",
]

# ──────────────────────────────────────────────
# 스타일 (HTML/CSS 주입) — 따뜻한 축제 톤: 오렌지 · 라즈베리 · 민트 · 선샤인
# ──────────────────────────────────────────────
CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
:root{--ink:#2A1B14;--orange:#FF7A1A;--berry:#FF3D71;--mint:#19D3A2;--sun:#FFD23F;--line:#F3E4D3;--muted:#8A7565;}
.stApp, .stMarkdown, .stMarkdown p, label, button, input{
  font-family:'Pretendard Variable',Pretendard,-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;
}
.stApp{
  background:
    radial-gradient(520px 300px at 95% -4%, rgba(255,122,26,.16), transparent 60%),
    radial-gradient(520px 320px at -8% 6%, rgba(25,211,162,.14), transparent 60%),
    radial-gradient(2px 2px at 20px 30px, rgba(255,61,113,.25) 50%, transparent 51%) 0 0/90px 90px,
    #FFF9F0;
}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"]{display:none !important;}
header[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:1040px;margin:0 auto;padding:1.2rem 1rem 4rem;}

/* hero */
.hero{position:relative;overflow:hidden;padding:22px 20px 22px;border-radius:28px;color:#fff;margin-bottom:14px;
  background:linear-gradient(135deg,#FF7A1A 0%,#FF4F5E 55%,#FF3D71 100%);
  box-shadow:0 14px 32px -14px rgba(255,90,60,.6);}
.hero:before{content:"";position:absolute;right:-40px;top:-50px;width:170px;height:170px;border-radius:50%;
  background:var(--sun);opacity:.6;filter:blur(24px);}
.hero:after{content:"🎪";position:absolute;right:18px;top:12px;font-size:46px;opacity:.95;transform:rotate(8deg);}
.hero .kicker{position:relative;display:inline-block;font-size:11px;font-weight:800;letter-spacing:.09em;
  background:rgba(255,255,255,.24);padding:4px 10px;border-radius:99px;}
.hero .title{position:relative;margin:10px 0 4px;font-size:36px;line-height:1.08;font-weight:900;letter-spacing:-.035em;}
.hero .title em{font-style:normal;background:var(--mint);color:var(--ink);padding:0 8px;border-radius:12px;margin-left:2px;}
.hero .sub{position:relative;margin:0;font-size:14px;font-weight:500;opacity:.95;max-width:70%;}
.sticker{position:absolute;right:16px;bottom:16px;transform:rotate(-6deg);background:var(--sun);color:var(--ink);
  font-weight:900;font-size:13px;line-height:1.25;text-align:center;padding:9px 13px;border-radius:16px;
  box-shadow:0 8px 18px -8px rgba(0,0,0,.35);}
.sticker b{display:block;font-size:22px;letter-spacing:-.02em;}

/* filters */
.st-key-filters{background:#fff;border:1px solid var(--line);border-radius:22px;padding:14px 16px;margin-bottom:14px;
  box-shadow:0 8px 22px -14px rgba(150,80,20,.3);}
.flabel{font-size:12px;font-weight:800;color:var(--muted);letter-spacing:.04em;margin:0 0 -4px;}

/* section title */
.sec{display:flex;align-items:baseline;gap:8px;margin:18px 2px 8px;font-size:19px;font-weight:900;letter-spacing:-.02em;color:var(--ink);}
.sec small{font-size:12px;font-weight:600;color:var(--muted);}

/* map */
.st-key-mapwrap{border-radius:24px;overflow:hidden;border:1px solid var(--line);box-shadow:0 14px 30px -18px rgba(150,80,20,.45);}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin:8px 4px 0;font-size:12px;font-weight:600;color:var(--muted);}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px;}

/* cards */
[class*="st-key-card_"]{background:#fff;border:1px solid var(--line);border-radius:24px;padding:10px 10px 12px;gap:.55rem;
  box-shadow:0 8px 22px -16px rgba(150,80,20,.35);transition:transform .2s ease, box-shadow .2s ease;margin-bottom:6px;}
[class*="st-key-card_"]:hover{transform:translateY(-3px);box-shadow:0 18px 32px -16px rgba(255,90,60,.45);}
[class*="st-key-card_"] [data-testid="stMarkdownContainer"]{margin-bottom:0 !important;}
.pp-thumb{position:relative;aspect-ratio:4/3;border-radius:18px;background-size:cover;background-position:center;
  display:flex;align-items:center;justify-content:center;overflow:hidden;}
.pp-thumb.ended{filter:grayscale(.9) brightness(.95);}
.pp-emoji{font-size:44px;filter:drop-shadow(0 6px 10px rgba(0,0,0,.15));}
.pp-badge{position:absolute;left:10px;top:10px;font-size:11px;font-weight:800;letter-spacing:.03em;padding:5px 10px;border-radius:99px;}
.b-open{background:var(--berry);color:#fff;}
.b-soon{background:var(--mint);color:var(--ink);}
.b-tbd{background:var(--sun);color:var(--ink);}
.b-ended{background:#3A2A22;color:#fff;}
.pp-cat{position:absolute;right:10px;top:10px;font-size:11px;font-weight:700;padding:5px 10px;border-radius:99px;
  background:rgba(255,255,255,.9);color:var(--ink);backdrop-filter:blur(6px);}
.pp-body{padding:2px 6px 0;}
/* 카드 높이 통일: 제목·주소는 2줄 고정(넘치면 …), 기간은 1줄 */
.pp-name{font-size:17px;font-weight:800;letter-spacing:-.02em;color:var(--ink);line-height:1.3;margin:2px 0 6px;
  min-height:2.6em;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;}
.pp-meta{font-size:13px;color:var(--muted);margin:2px 0;line-height:1.4;font-weight:500;}
.pp-period{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.pp-addr{min-height:2.8em;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;}
.pp-meta b{color:var(--ink);font-weight:700;}
[class*="st-key-card_"] a{background:var(--ink) !important;border:0 !important;border-radius:999px !important;
  color:#fff !important;font-weight:700;min-height:42px;transition:background .15s ease, transform .1s ease;}
[class*="st-key-card_"] a:hover{background:var(--orange) !important;}
[class*="st-key-card_"] a:active{transform:scale(.97);}
[class*="st-key-card_"] a p, [class*="st-key-card_"] a span{color:#fff !important;}

.count{font-size:13px;font-weight:600;color:var(--muted);margin:2px 4px 4px;}
.count b{color:var(--berry);font-weight:900;}
.empty{text-align:center;padding:42px 12px;background:#fff;border:1px dashed #EBCFB2;border-radius:24px;color:var(--muted);font-weight:600;}
.empty span{display:block;font-size:40px;margin-bottom:6px;}
.foot{text-align:center;font-size:12px;color:var(--muted);margin-top:26px;}

@media (max-width:640px){
  .block-container{padding:.6rem .8rem 3rem;}
  .hero .title{font-size:31px;}
  .hero .sub{max-width:62%;font-size:13px;}
}
</style>
"""


# ──────────────────────────────────────────────
# 데이터 로딩 & 방어 코드
# ──────────────────────────────────────────────
def today_kst() -> date:
    return datetime.now(KST).date()


def parse_date(value) -> date | None:
    """다양한 날짜 표기(2026-10-01 / 2026.10.1 / 2026년 10월 1일 / 20261001 …)를 date로. 실패하면 None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{8}", text):
        nums = [text[:4], text[4:6], text[6:]]
    else:
        nums = re.findall(r"\d+", text)
    if len(nums) < 3:
        return None
    try:
        y, m, d = (int(n) for n in nums[:3])
        if y < 100:
            y += 2000
        return date(y, m, d)
    except ValueError:
        return None


def parse_loose(value, end: bool) -> tuple[date | None, str]:
    """날짜 + 정밀도('day'|'month'|'year'|''). '2026-09-미정'은 그 달 1일/말일, '2026-미정'은 1/1·12/31로 본다."""
    d = parse_date(value)
    if d:
        return d, "day"
    text = str(value or "").strip()
    m = re.match(r"^(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]?\s*미정", text)
    if m and 1 <= int(m[2]) <= 12:
        y, mo = int(m[1]), int(m[2])
        return date(y, mo, calendar.monthrange(y, mo)[1] if end else 1), "month"
    m = re.match(r"^(\d{4})\s*[-./]?\s*미정", text)
    if m:
        y = int(m[1])
        return (date(y, 12, 31) if end else date(y, 1, 1)), "year"
    return None, ""


def safe_url(value) -> str:
    """http(s) 링크만 허용 (javascript: 등 차단)."""
    text = str(value or "").strip()
    return text if re.match(r"^https?://", text, re.I) else ""


def region_of(address: str) -> str:
    addr = str(address or "").strip()
    for prefix, short in REGION_PREFIX:
        if addr.startswith(prefix):
            return short
    return "기타"


@st.cache_data(show_spinner="축제 불러오는 중… 🎪")
def load_raw() -> tuple[pd.DataFrame, bool]:
    """data/festivals_2026.csv → DataFrame. 파일이 없으면 샘플 CSV(데모 모드)."""
    if DATA_CSV.exists():
        return pd.read_csv(DATA_CSV, encoding="utf-8-sig", dtype=str), False
    return pd.read_csv(SAMPLE_CSV, encoding="utf-8-sig", dtype=str), True


def classify(start: date | None, end: date | None, today: date, tbd: bool = False) -> tuple[str, str]:
    """(상태코드, 뱃지 문구). tbd=True는 일자가 '미정'인 축제."""
    if tbd:
        if end and today > end:
            return "ended", "종료"
        if start and end and (start.year, start.month) == (end.year, end.month):
            return "tbd", f"{start.month}월 · 일정 미정"
        return "tbd", "일정 미정"
    if start and today < start:
        return "soon", f"예정 · {start:%m.%d} 개막"
    if end and today > end:
        return "ended", "종료"
    if end is None:
        return "open", "진행중 · 상시"
    left = (end - today).days
    return "open", "오늘 마지막 날!" if left == 0 else f"진행중 · D-{left}"


def period_text(start: date | None, end: date | None, ps: str = "day", pe: str = "day") -> str:
    def fmt(d: date, prec: str) -> str:
        return f"{d:%Y.%m.%d}" if prec == "day" else f"{d:%Y.%m}" if prec == "month" else f"{d:%Y}"

    if start and end:
        a, b = fmt(start, ps), fmt(end, pe)
        text = a if a == b else f"{a} – {b}"
    elif end:
        text = f"~ {fmt(end, pe)}"
    elif start:
        text = f"{fmt(start, ps)} ~"
    else:
        return "상시 운영"
    return text + (" (일자 미정)" if ps != "day" or pe != "day" else "")


def prepare(raw: pd.DataFrame, today: date) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None

    for col in ("축제명", "카테고리", "주소", "참고_링크", "이미지_URL"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    df = df[df["축제명"] != ""].copy()
    df["카테고리"] = df["카테고리"].replace("", "지역축제")

    parsed_s = [parse_loose(v, end=False) for v in df["시작일"]]
    parsed_e = [parse_loose(v, end=True) for v in df["종료일"]]
    df["시작일"] = [p[0] for p in parsed_s]
    df["종료일"] = [p[0] for p in parsed_e]
    loose = [ps[1] in ("month", "year") or pe[1] in ("month", "year") for ps, pe in zip(parsed_s, parsed_e)]
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")

    # 위도/경도가 뒤바뀐 경우 보정 (한국 위도는 33~39, 경도는 124~132)
    swapped = (df["위도"] > 90) | ((df["위도"] > 100) & (df["경도"] < 60))
    df.loc[swapped, ["위도", "경도"]] = df.loc[swapped, ["경도", "위도"]].to_numpy()
    df.loc[(df["위도"].abs() > 90) | (df["경도"].abs() > 180), ["위도", "경도"]] = float("nan")

    df["region"] = df["주소"].map(region_of)
    status = [classify(s, e, today, t) for s, e, t in zip(df["시작일"], df["종료일"], loose)]
    df["status"] = [s[0] for s in status]
    df["badge"] = [s[1] for s in status]
    df["period"] = [
        period_text(s, e, ps[1] or "day", pe[1] or "day")
        for s, e, ps, pe in zip(df["시작일"], df["종료일"], parsed_s, parsed_e)
    ]

    # 정렬: 진행중(마감 임박순) → 개막 예정(빠른순) → 일정 미정(빠른 달순) → 종료(최근순)
    far = date(2999, 12, 31)
    order = {"open": 0, "soon": 1, "tbd": 2, "ended": 3}
    df["_o"] = df["status"].map(order)
    df["_k"] = [
        (e or far).toordinal() if st_ == "open"
        else (s or far).toordinal() if st_ in ("soon", "tbd")
        else -(e or far).toordinal()
        for s, e, st_ in zip(df["시작일"], df["종료일"], df["status"])
    ]
    return df.sort_values(["_o", "_k"]).drop(columns=["_o", "_k"]).reset_index(drop=True)


# ──────────────────────────────────────────────
# 지도 (pydeck)
# ──────────────────────────────────────────────
def build_map(df: pd.DataFrame) -> pdk.Deck | None:
    geo = df.dropna(subset=["위도", "경도"])
    if geo.empty:
        return None

    data = pd.DataFrame(
        {
            "name": geo["축제명"],
            "cat": geo["카테고리"],
            "badge": geo["badge"],
            "period": geo["period"],
            "lat": geo["위도"],
            "lon": geo["경도"],
            "color": geo["status"].map(STATUS_RGB),
        }
    )

    glow = pdk.Layer(
        "ScatterplotLayer", data, pickable=True, get_position="[lon, lat]",
        get_radius=1500, radius_min_pixels=14, radius_max_pixels=28,
        get_fill_color="[color[0], color[1], color[2], 70]",
    )
    pin = pdk.Layer(
        "ScatterplotLayer", data, pickable=True, auto_highlight=True, get_position="[lon, lat]",
        get_radius=500, radius_min_pixels=6, radius_max_pixels=12,
        stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=2.5,
        get_fill_color="[color[0], color[1], color[2], 255]",
    )

    lat_span = float(data["lat"].max() - data["lat"].min())
    lon_span = float(data["lon"].max() - data["lon"].min())
    span = max(lat_span, lon_span, 0.02)
    zoom = min(14.0, max(5.6, math.log2(400 / span)))  # 전국 → 약 6, 한 지역 → 확대
    view = pdk.ViewState(
        latitude=float(data["lat"].mean()), longitude=float(data["lon"].mean()), zoom=zoom, pitch=0
    )

    tooltip = {
        "html": (
            "<div style='font-family:Pretendard Variable,sans-serif;padding:2px 2px'>"
            "<div style='font-size:14px;font-weight:800;margin-bottom:3px'>{name}</div>"
            "<div style='font-size:12px;opacity:.85'>{cat} · {badge}</div>"
            "<div style='font-size:12px;margin-top:2px'>🗓 {period}</div></div>"
        ),
        "style": {
            "backgroundColor": "#2A1B14", "color": "#fff", "borderRadius": "14px",
            "padding": "8px 12px", "boxShadow": "0 8px 20px rgba(0,0,0,.25)",
        },
    }
    return pdk.Deck(
        layers=[glow, pin], initial_view_state=view, tooltip=tooltip,
        map_provider="carto", map_style="light",  # 토큰 필요 없는 깔끔한 라이트 지도
    )


# ──────────────────────────────────────────────
# 카드 (HTML)
# ──────────────────────────────────────────────
def css_url(value: str) -> str:
    url = safe_url(value)
    return quote(url, safe=":/?&=%#@+,;~!*$-._") if url else ""


def card_html(r: dict) -> str:
    name = html.escape(r["축제명"])
    cat = html.escape(r["카테고리"])
    addr = html.escape(r["주소"])
    emoji = CAT_EMOJI.get(r["카테고리"], "🎪")
    grad = GRADIENTS[sum(map(ord, r["축제명"])) % len(GRADIENTS)]
    img = css_url(r["이미지_URL"])

    bg = f"url(\"{img}\") center/cover no-repeat, {grad}" if img else grad
    inner = "" if img else f"<span class='pp-emoji'>{emoji}</span>"
    ended = " ended" if r["status"] == "ended" else ""

    return (
        f"<div class='pp-thumb{ended}' style='background:{bg}'>{inner}"
        f"<span class='pp-badge b-{r['status']}'>{html.escape(r['badge'])}</span>"
        f"<span class='pp-cat'>{emoji} {cat}</span></div>"
        f"<div class='pp-body'><div class='pp-name' title='{name}'>{name}</div>"
        f"<div class='pp-meta pp-period'>🗓 <b>{html.escape(r['period'])}</b></div>"
        f"<div class='pp-meta pp-addr' title='{addr}'>📍 {addr or '주소 준비중'}</div></div>"
    )


def render_card(r: dict, idx: int) -> None:
    link = safe_url(r["참고_링크"])
    with st.container(key=f"card_{idx}"):
        st.markdown(card_html(r), unsafe_allow_html=True)
        if link:
            st.link_button("상세보기 →", link, use_container_width=True)
        else:  # 링크가 없으면 네이버 검색으로 대체
            st.link_button("검색해서 보기 🔎", f"https://search.naver.com/search.naver?query={quote(r['축제명'])}", use_container_width=True)


# ──────────────────────────────────────────────
# 화면
# ──────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

try:
    raw, is_demo = load_raw()
except Exception as exc:  # CSV가 깨졌거나 읽을 수 없을 때
    st.error("축제 데이터를 불러오지 못했어요 😢 data/festivals_2026.csv 파일을 확인해 주세요.")
    with st.expander("에러 자세히 보기"):
        st.code(str(exc))
    st.stop()

today = today_kst()
df_all = prepare(raw, today)
open_count = int((df_all["status"] == "open").sum())

st.markdown(
    f"""<div class="hero"><span class="kicker">LIVE · FESTIVAL RADAR</span>
<div class="title">축제 <em>찾아줘</em></div>
<p class="sub">이번 주말 어디 갈까? 2026 전국 지역축제, 한눈에 콕!</p>
<div class="sticker">지금 열리는 축제<b>{open_count}곳</b></div></div>""",
    unsafe_allow_html=True,
)

if is_demo:
    st.info("🧪 데모 모드: data/festivals_2026.csv 가 없어서 샘플 데이터를 보여주고 있어요.")

# 필터 (화면 상단)
present = set(df_all["region"])
regions = [r for r in REGION_ORDER if r in present] + (["기타"] if "기타" in present else [])
categories = sorted(df_all["카테고리"].unique().tolist())


def pick(label: str, options: list[str]) -> list[str]:
    if hasattr(st, "pills"):
        return st.pills(label, options, selection_mode="multi", label_visibility="collapsed") or []
    return st.multiselect(label, options, placeholder="전체", label_visibility="collapsed")


with st.container(key="filters"):
    only_open = st.toggle("🟢 지금 열리는 축제만 보기", value=True)
    include_tbd = st.toggle("📅 이번 달 '일정 미정' 축제도 같이 보기", value=False, disabled=not only_open)
    st.markdown("<div class='flabel'>REGION · 지역 (안 고르면 전국)</div>", unsafe_allow_html=True)
    picked_regions = pick("지역 선택", regions)
    st.markdown("<div class='flabel'>CATEGORY · 종류 (안 고르면 전체)</div>", unsafe_allow_html=True)
    picked = pick("카테고리 선택", categories)

df = df_all
if only_open:
    now_tbd = (df["status"] == "tbd") & df["시작일"].map(lambda d: d is not None and d <= today) if include_tbd else False
    df = df[(df["status"] == "open") | now_tbd]
if picked_regions:
    df = df[df["region"].isin(picked_regions)]
if picked:
    df = df[df["카테고리"].isin(picked)]
df = df.reset_index(drop=True)

# 필터가 바뀌면 "더 보기" 초기화
sig = (only_open, include_tbd, tuple(sorted(picked)), tuple(sorted(picked_regions)))
if st.session_state.get("sig") != sig:
    st.session_state["sig"] = sig
    st.session_state["limit"] = PAGE_SIZE

# 지도
st.markdown("<div class='sec'>🗺️ 축제 지도 <small>핀을 탭하면 정보가 떠요</small></div>", unsafe_allow_html=True)
deck = build_map(df)
if deck is None:
    st.markdown("<div class='empty'><span>🫥</span>지도에 표시할 축제가 없어요</div>", unsafe_allow_html=True)
else:
    with st.container(key="mapwrap"):
        st.pydeck_chart(deck, height=380)
    st.markdown(
        "<div class='legend'>"
        "<span><i style='background:#FF3D71'></i>진행중</span>"
        "<span><i style='background:#19D3A2'></i>개막 예정</span>"
        "<span><i style='background:#FFB000'></i>일정 미정</span>"
        "<span><i style='background:#A69E96'></i>종료</span></div>",
        unsafe_allow_html=True,
    )

# 갤러리
st.markdown("<div class='sec'>🔥 지금 핫한 축제 <small>진행중 → 예정 → 일정 미정 → 종료 순</small></div>", unsafe_allow_html=True)
st.markdown(f"<div class='count'>총 <b>{len(df)}</b>곳 발견!</div>", unsafe_allow_html=True)

if df.empty:
    st.markdown(
        "<div class='empty'><span>🫥</span>조건에 맞는 축제가 없어요<br>필터를 바꿔볼까요?</div>",
        unsafe_allow_html=True,
    )
else:
    limit = st.session_state.get("limit", PAGE_SIZE)
    records = df.head(limit).to_dict("records")
    for start in range(0, len(records), 3):  # 데스크톱 3열 / 모바일은 자동으로 1열
        cols = st.columns(3)
        for offset, rec in enumerate(records[start : start + 3]):
            with cols[offset]:
                render_card(rec, start + offset)
    if limit < len(df):
        if st.button(f"더 보기 ({len(df) - limit}곳 남음) 👇", use_container_width=True, type="primary"):
            st.session_state["limit"] = limit + PAGE_SIZE
            st.rerun()

st.markdown(
    f"<div class='foot'>기준일 {today:%Y.%m.%d} · 자료: 공공데이터포털 「2026년 지역축제 개최 계획 현황」<br>"
    "지자체 제출 계획이라 일정은 바뀔 수 있어요. 가기 전에 꼭 확인하세요!</div>",
    unsafe_allow_html=True,
)
