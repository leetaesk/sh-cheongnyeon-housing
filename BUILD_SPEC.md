# SH 청년안심주택 뷰어 — BUILD SPEC & 진행상황

> 목적: 2026년 1차 청년 매입임대주택 공고의 **주택 리스트 + 위치(지도) + 가격 + 사진**을
> 한 화면에서 볼 수 있는 로컬 HTML 앱. 서버 없이 `index.html`을 브라우저로 열면 동작.
> 이 문서는 **작업 인수인계/재개용 단일 진실 문서**. 컨텍스트가 리셋돼도 이 파일만 보면 이어서 작업 가능.

## 0. 사용자 확정 결정
- **지도**: 키 없이 — Leaflet + OSM 인라인 지도(마커) + 각 건물 "네이버 지도에서 보기" 링크. (네이버 정식 임베드는 iframe 차단 + NCP 키 필요라 제외)
- **가격 표시**: 4종 전부 동등 표 — 1순위(시세30%)·2~3순위(시세50%) × 청년·대학생 각 {보증금, 임대료}.
- 사이드바 = 건물(147개) 리스트, 클릭 시 상세(지도+가격표+사진).

## 1. 데이터 소스 (원본, ~/Downloads)
- `2_ [주택목록] 2026년 1차 청년 매입임대주택 입주자 모집공고(홈페이지 공개용).pdf` — **가격표**(14p, 849호). 텍스트 레이어 존재, `pdftotext -layout`로 파싱.
- `3_ [첨부] 도면 및 사진(링크).pdf` — 구별 다운로드 링크(이미 처리 완료).
- 다운로드/해제된 도면·사진: `~/Desktop/sh청년주택/{구}_{신규|재공급}/{건물폴더}/...`

## 2. 폴더 레이아웃 (~/Desktop/sh청년주택)
```
{구}_{신규|재공급}/{건물폴더}/[도면]....pdf , [사진]..../ (webp들) 또는 [사진]....pdf 등
common.py            → 공용 헬퍼 (WORK 경로 = 스크립트 위치, natkey)
download.sh          → zips/ (34개 구별 zip 다운로드)
extract.py           → 1차(구별 zip)+2차(중첩 [사진] zip) 압축해제
extract_pdf_photos.py→ 사진이 PDF에만 있는 건물에서 페이지별 이미지 추출
to_webp.sh           → 모든 jpg/png를 WebP(q80, 최장변 2000px)로 변환 후 원본 삭제
parse_prices.py      → units.json     (849호 · 가격)
catalog_media.py     → media.json     (150 폴더 · 파일 분류)
merge.py             → data.json      (147 건물 카드 · units+media 병합)
geocode.py           → data.json 에 lat/lng 추가 (+ geocode_cache.json)
build.py             → data.js        (window.DATA = data.json 내용)
index.html           → 최종 앱 (data.js + Leaflet CDN)
logs/                → 각 단계 실행 로그
BUILD_SPEC.md        → 이 문서
```

## 3. 데이터 모델

### units.json (849) — 호 단위
```
{ 연번, 구분("신규공급"|"재공급"), 구, 호, 주택명, 주소, 도로명, 지번,
  주택형, 주택구조, 성별("-"|"남성"|"여성"), 전용면적(float),
  가격: { "1순위_청년":{보증금,임대료}, "1순위_대학생":{...},
          "2~3순위_청년":{...}, "2~3순위_대학생":{...} } }   # 값 없으면 null (예: 청년전용동은 대학생 null)
```

### data.json (147) — 건물(=위치) 카드
```
{ id, 구분, 구, 주택명(대표), 주택명들[], 도로명, 지번,
  geocode_addr, 주택구조들[], 면적_min, 면적_max, 호수,
  folders[], lat, lng, geo_source,
  media: { images[], domyeon_pdfs[], sajin_pdfs[], combined_pdfs[], others[] },  # 경로는 프로젝트 루트 기준 상대경로
  units[] }   # 이 위치의 모든 호 (여러 동 포함 가능)
```

## 4. 파싱/매칭 규칙 (해결한 엣지케이스)
- **가격 파싱**: 양끝 앵커링 — 좌(연번·구분·구·호), 주소는 "서울특별시"~"(지번)", 우(가격 8칸·면적·성별).
  대학생 가격이 `-`인 청년전용동 → null 처리 (삼화에코빌2차 17호).
- **폴더 지번 파싱**: 괄호 여러 개면 `숫자+동/가/리` 패턴인 그룹을 지번으로 선택 (삼화에코빌2차 이중괄호).
- **매칭**: 위치키 = (구분, 구, norm지번). norm지번은 "외 N필지"/공백 제거.
  폴더→위치 해석 폴백: **지번 → 주택명 → 도로명**.
  - 도로명 폴백: 블루밍하우스(PDF 괄호가 지번 아님) 처리.
  - 지번 그룹핑: 같은 지번 여러 동(아트라움 101/102동, 서도휴빌 103/104/105동 등) 한 카드로.
  - 한 지번에 폴더 여러 개(가동/나동, A/B동)면 미디어를 한 카드로 합침.
- **검증 결과**: 849/849호 매칭, 미매칭 위치 0, 미디어 없는 카드 0. 111개 카드 WebP 갤러리, 전체 이미지 2559장(HEIC 21장 변환 + PDF 추출 560장 포함). 나머지 36개 카드는 원본에 도면 PDF만 존재.

## 5. HTML 앱 사양
- **로딩**: `data.js`(=window.DATA)를 `<script src>`로 로드 → file:// 에서도 CORS 문제 없음. 이미지/PDF는 상대경로 + `encodeURI`.
- **레이아웃**: 좌 사이드바(검색/필터 + 건물리스트), 우 상세(지도 + 사진 갤러리 + 호별 가격표).
- **필터**: 구분(신규/재공급), 자치구, 텍스트 검색, 사진있음 토글, 가격/면적 정렬.
- **지도**: Leaflet + OSM(CartoDB Positron) 타일. 상세에 단일 마커, 개요에 전체 마커. "네이버 지도에서 보기" = `https://map.naver.com/p/search/{주소}`.
- **가격표**: 호별 행 × (주택형·면적·구조·성별 + 4가격). 원화 콤마 포맷, 만원 단위 요약.
- CDN: Leaflet unpkg. (로컬 파일이므로 인터넷 있으면 동작)

## 6. 진행 체크리스트  ✅ 전체 완료
- [x] 다운로드(34개 zip) + 1·2차 압축해제 + 원본/중첩 zip 정리
- [x] parse_prices.py → units.json (849, 0 err)
- [x] HEIC 21장 → JPG 변환 (브라우저 미지원 포맷 복원)
- [x] extract_pdf_photos.py → 사진이 PDF에만 있던 43개 건물에서 560장 추출
- [x] to_webp.sh → 전체 2559장 WebP 변환 (이미지 4.07GB → 0.34GB, 원본 삭제)
- [x] catalog_media.py → media.json (150 폴더, 이미지 2559)
- [x] merge.py → data.json (147 카드, 849/849 매칭)
- [x] geocode.py → lat/lng (147/147, Nominatim)
- [x] build.py → data.js (~1MB, inline)
- [x] index.html 작성 (Leaflet + 갤러리 + 4종 가격표)
- [x] 검증(QA) verify.py: 이미지경로 0누락, 지오 147/147 서울내, 가격 849/0누락 · 브라우저 실동작(개요·상세·갤러리·라이트박스·가격표 대조) 확인
- [x] GitHub 공개(leetaesk/sh-cheongnyeon-housing) + Vercel 배포(sh-cheongnyeon-housing.vercel.app)
- [x] 완료

## 7. 재개(Resume) 방법
컨텍스트 리셋 시: 이 폴더에서 `python3 parse_prices.py && python3 catalog_media.py && python3 merge.py && python3 geocode.py && python3 build.py` 순서로 재생성 가능. 각 스크립트는 요약을 stdout에 출력. data.json이 최신이면 build.py + index.html만 손보면 됨.
