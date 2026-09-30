# 🎪 축제 찾아줘

2026년 전국 지역축제를 지도와 카드로 보여주는 모바일 웹앱 (Streamlit).
공공데이터포털의 「2026년 지역축제 개최 계획 현황(공개용)」 엑셀을 CSV로 바꿔 **앱에 포함**해서 씁니다. (구글 시트·API·자동 갱신 없음)

```
엑셀 → tools/build_festival_data.py (1회용) → data/festivals_2026.csv → app.py (Streamlit) → 폰
```

## 폴더 구조
| 경로 | 역할 |
|---|---|
| `app.py` | 앱 본체 (지도 + 카드 갤러리 + 필터) |
| `data/festivals_2026.csv` | 앱이 읽는 데이터 (1,266건) |
| `tools/build_festival_data.py` | 엑셀 → CSV 변환기 (1회용, 좌표 조회 포함) |
| `2026년 지역축제 개최 계획 현황(공개용).xlsx` | 원본 자료 |
| `sample_data.csv` | `data/festivals_2026.csv`가 없을 때 쓰는 데모 |

## CSV 컬럼 (1행 고정)
`축제명 | 카테고리 | 시작일 | 종료일 | 주소 | 위도 | 경도 | 참고_링크 | 이미지_URL`

## 데이터에 대해 알아둘 점
- **좌표는 "동네 중심"이에요.** 엑셀에 좌표가 없어서 OpenStreetMap(Nominatim, 무료)으로 `읍면동 → 시군구 → 시도` 순서로 찾았어요. 행사장 정확한 위치가 아니라서, 같은 동네 축제 핀은 겹치지 않게 살짝 흩어 놨어요.
- **일자 미정 축제가 많아요.** 월까지만 정해지고 일(日)이 미정인 축제는 `2026-09-미정`, 월까지 미정이면 `2026-미정`으로 들어가요. 앱에는 노란 "일정 미정" 뱃지로 나와요.
- **이미지가 없어요.** 카드는 그라데이션 + 이모지로 보여요. `이미지_URL` 칸을 채우면 자동으로 사진이 떠요.
- **참고_링크는 네이버 검색**(`축제명 + 시군구`)으로 연결돼요. 지자체가 낸 계획이라 일정이 바뀔 수 있어요.
- 카테고리는 엑셀의 축제 유형(문화예술·자연생태·주민화합·전통역사·지역특산물) 그대로예요. 지역 필터는 `주소` 앞부분(서울·부산…)에서 앱이 자동으로 뽑아요.

## 데이터 고치기
`data/festivals_2026.csv`를 엑셀/메모장으로 열어 수정 후 저장하고, 저장소에 올리면 배포된 앱에 반영돼요.
(엑셀로 저장할 땐 "CSV UTF-8" 형식으로! `2026-09-미정` 같은 칸이 날짜로 바뀌지 않게 주의하세요.)

## 실행 / 배포
```bash
pip install -r requirements.txt
python -m streamlit run app.py
```
배포(Streamlit Community Cloud): 새 GitHub 저장소에 올리고 → share.streamlit.io → 저장소 선택, Branch `main`, Main file `app.py` → Deploy. (Secrets 설정은 필요 없어요.)

## 엑셀에서 CSV 다시 만들기 (필요할 때만)
```bash
pip install pandas openpyxl requests
python tools/build_festival_data.py            # 좌표 조회에 20분쯤 (이미 조회한 곳은 캐시라 재실행은 빨라요)
python tools/build_festival_data.py --limit 15 # 빠른 시험
```
