"""
[1회용] 공공데이터포털 "2026년 지역축제 개최 계획 현황(공개용).xlsx" → 앱용 CSV(data/festivals_2026.csv) 만들기

  python tools/build_festival_data.py            # 전체 (좌표 조회에 20분쯤 걸려요)
  python tools/build_festival_data.py --limit 15 # 빠른 시험

결과
  data/festivals_2026.csv    앱이 바로 읽는 전체 데이터 (BOM UTF-8)
  tools/geocode_cache.json   좌표 조회 캐시 (다시 돌려도 이미 조회한 곳은 건너뛰어요)

좌표: 엑셀에 좌표가 없어서 OpenStreetMap Nominatim(무료, 키 불필요)으로 "읍면동 → 시군구 → 시도" 순서로 찾아요.
      → 정확한 행사장 위치가 아니라 "그 동네 중심"이에요. 같은 동네 축제 핀이 겹치지 않게 살짝 흩어 놓아요.
날짜: 일(日)이 '미정'인 축제는 "2026-09-미정", 월까지 미정이면 "2026-미정" 으로 적어요. (앱이 '일정 미정'으로 표시)
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
CACHE = TOOLS / "geocode_cache.json"
COLUMNS = ["축제명", "카테고리", "시작일", "종료일", "주소", "위도", "경도", "참고_링크", "이미지_URL"]
HEADERS = {"User-Agent": "FestivalFinderPersonal/1.0 (one-time import; https://github.com/verb0448)"}


def clean(v) -> str:
    s = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()
    return "" if s in ("nan", "-", "NaN") else s


def strip_no(v) -> str:
    return re.sub(r"^\d+\.\s*", "", clean(v))


def to_int(v) -> int | None:
    try:
        return int(float(clean(v)))
    except ValueError:
        return None


def when(y, m, d) -> str:
    """연/월/일 → 'YYYY-MM-DD' | 'YYYY-MM-미정' | 'YYYY-미정' | ''"""
    y, m, d = to_int(y), to_int(m), to_int(d)
    if not y:
        return ""
    if m and d:
        try:
            return f"{y:04d}-{m:02d}-{d:02d}" if pd.Timestamp(y, m, d) else ""
        except ValueError:
            return f"{y:04d}-{m:02d}-미정"
    if m:
        return f"{y:04d}-{m:02d}-미정"
    return f"{y:04d}-미정"


def load_excel() -> pd.DataFrame:
    path = glob.glob(str(ROOT / "2026*.xlsx"))
    if not path:
        sys.exit("엑셀 파일(2026…xlsx)을 축제찾아줘 폴더에서 못 찾았어요")
    raw = pd.read_excel(path[0], sheet_name="조사표", header=None, dtype=str)
    d = raw.iloc[8:, [2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16]].copy()
    d.columns = ["광역", "기초", "축제명", "유형", "장소", "시도", "시군구", "읍면동", "sy", "sm", "sd", "ey", "em", "ed"]
    return d[d["축제명"].notna() & (d["축제명"].astype(str).str.strip() != "")].reset_index(drop=True)


# ──────────────────────────────────────────────
# 좌표 (Nominatim, 캐시 + 1초 간격)
# ──────────────────────────────────────────────
def load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def nominatim(q: str, session: requests.Session) -> tuple[float, float] | None:
    for attempt in range(4):
        try:
            r = session.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "kr", "accept-language": "ko"},
                headers=HEADERS, timeout=30,
            )
            time.sleep(1.1)  # 이용 정책: 초당 1건 이하
            if r.status_code == 200:
                j = r.json()
                return (float(j[0]["lat"]), float(j[0]["lon"])) if j else None
        except (requests.RequestException, ValueError):
            pass
        time.sleep(3 * (attempt + 1))
    return None


def locate(sido: str, gu: str, dong: str, cache: dict, session: requests.Session) -> tuple[float, float] | None:
    """읍면동 → 시군구 → 시도 순으로 첫 성공 좌표."""
    for level, q in (("dong", f"{sido} {gu} {dong}"), ("gu", f"{sido} {gu}"), ("sido", sido)):
        if level == "dong" and not dong:
            continue
        if level == "gu" and not gu:
            continue
        key = q.strip()
        if key not in cache:
            hit = nominatim(key, session)
            cache[key] = list(hit) if hit else None
            if len(cache) % 25 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        if cache[key]:
            return tuple(cache[key])  # type: ignore[return-value]
    return None


def jitter(name: str) -> tuple[float, float]:
    """같은 동네 핀이 한 점에 겹치지 않게, 축제명 기반으로 ±약 350m 고정 오프셋."""
    h = hashlib.md5(name.encode("utf-8")).digest()
    return ((h[0] / 255 - 0.5) * 0.007, (h[1] / 255 - 0.5) * 0.007)


# ──────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    d = load_excel()
    if args.limit:
        d = d.sample(args.limit, random_state=7).reset_index(drop=True)
    print(f"엑셀 {len(d)}건")

    cache, session = load_cache(), requests.Session()
    rows, miss = [], 0
    for i, r in d.iterrows():
        sido, gu, dong = strip_no(r["시도"]), clean(r["시군구"]), clean(r["읍면동"])
        name = clean(r["축제명"])
        pos = locate(sido, gu, dong, cache, session)
        lat = lng = ""
        if pos:
            dy, dx = jitter(name)
            lat, lng = round(pos[0] + dy, 6), round(pos[1] + dx, 6)
        else:
            miss += 1
        addr = " ".join(x for x in (sido, gu, dong, clean(r["장소"])) if x)
        rows.append({
            "축제명": name,
            "카테고리": strip_no(r["유형"]) or "기타",
            "시작일": when(r["sy"], r["sm"], r["sd"]),
            "종료일": when(r["ey"], r["em"], r["ed"]),
            "주소": addr,
            "위도": lat,
            "경도": lng,
            "참고_링크": f"https://search.naver.com/search.naver?query={quote(f'{name} {gu}'.strip())}",
            "이미지_URL": "",
        })
        if (i + 1) % 100 == 0:
            print(f"  … {i + 1}/{len(d)} (좌표 실패 {miss})")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    # 같은 축제(이름+시작일+주소) 중복 제거 후 시작일 순으로
    uniq = {(r["축제명"], r["시작일"], r["주소"]): r for r in rows}
    out = sorted(uniq.values(), key=lambda r: (r["시작일"] or "9999", r["축제명"]))
    (ROOT / "data").mkdir(exist_ok=True)
    path = ROOT / "data" / ("festivals_2026.csv" if not args.limit else "festivals_test.csv")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)
    print(f"저장: {path} ({len(out)}건, 좌표 실패 {miss}건)")


if __name__ == "__main__":
    main()
