# IT 보안 채용 대시보드

사람인 · 원티드 채용 공고를 매일 자동 수집해서 GitHub Pages로 서빙하는 무료 대시보드입니다.

## 구조

```
├── .github/
│   └── workflows/
│       └── crawl.yml       # GitHub Actions 자동화 (매일 오전 9시)
├── crawler/
│   ├── crawl.py            # Python 크롤러
│   └── requirements.txt
└── docs/
    ├── index.html          # 대시보드 (GitHub Pages 서빙)
    └── jobs.json           # 수집된 공고 데이터 (자동 생성)
```

## 배포 방법

### 1단계 — GitHub 저장소 생성
```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_ID/it-job-board.git
git push -u origin main
```

### 2단계 — GitHub Pages 설정
- Settings → Pages → Source: **GitHub Actions** 선택

### 3단계 — API 키 등록 (Secrets)
- Settings → Secrets and variables → Actions → **New repository secret**
- `SARAMIN_API_KEY` : 사람인 개발자센터(oapi.saramin.co.kr)에서 발급
- `SLACK_WEBHOOK_URL` : (선택) 실패 알림용

### 4단계 — 수동 실행 테스트
- Actions 탭 → "채용 공고 자동 수집" → **Run workflow**

배포 후 `https://YOUR_ID.github.io/it-job-board/` 에서 확인 가능합니다.

## 로컬 테스트
```bash
cd crawler
pip install -r requirements.txt
SARAMIN_API_KEY=your_key python crawl.py
# → docs/jobs.json 생성됨

# 브라우저 확인 (CORS 때문에 서버 필요)
cd docs
python -m http.server 8080
# → http://localhost:8080
```

## 자동 실행 일정
- 매일 **오전 9시 (KST)** = UTC 00:00
- `cron: "0 0 * * *"` 으로 설정
- Actions 탭에서 수동 실행도 가능

## 데이터 소스
| 소스 | 방식 | 제한 |
|------|------|------|
| 사람인 | 공식 OpenAPI | 무료, API 키 필요 |
| 원티드 | 비공개 API | 구조 변경 시 수정 필요 |
