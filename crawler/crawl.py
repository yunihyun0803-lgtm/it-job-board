"""
IT 보안 채용 크롤러
- 사람인 OpenAPI
- 원티드 비공개 API
- jobs.json 으로 저장 → GitHub Pages에서 서빙
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────
SARAMIN_API_KEY = os.environ.get("SARAMIN_API_KEY", "")   # GitHub Secrets에서 주입
OUTPUT_FILE     = "docs/jobs.json"                         # GitHub Pages 서빙 경로
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}

# 검색할 키워드 목록
KEYWORDS = [
    "정보보안",
    "보안 엔지니어",
    "침투테스트",
    "보안관제",
    "DevSecOps",
    "클라우드 보안",
    "보안 개발자",
    "악성코드 분석",
    "취약점 분석",
    "ISMS",
]

# 직군 분류 키워드
CAT_RULES = {
    "sec": ["보안","security","침투","모의해킹","취약점","soc","siem","isms",
            "악성코드","forensic","포렌식","firewall","방화벽","암호화",
            "컴플라이언스","secops","devsecops","해킹"],
    "dev": ["개발","developer","engineer","backend","frontend","fullstack",
            "java","python","golang","node","react","spring","kotlin","ios","android"],
    "inf": ["인프라","infrastructure","devops","kubernetes","k8s","docker",
            "aws","gcp","azure","cloud","클라우드","네트워크","network","sre","linux"],
}

def classify(company: str, position: str, keyword: str = "") -> str:
    txt = f"{company} {position} {keyword}".lower()
    for cat, kws in CAT_RULES.items():
        if any(k in txt for k in kws):
            return cat
    return "dev"

def make_id(source: str, company: str, position: str) -> str:
    raw = f"{source}::{company}::{position}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── 사람인 API ────────────────────────────────────────
def fetch_saramin(keyword: str, count: int = 100) -> list[dict]:
    if not SARAMIN_API_KEY:
        log.warning("SARAMIN_API_KEY 없음 — 사람인 크롤링 건너뜀")
        return []

    url = "https://oapi.saramin.co.kr/job-search"
    params = {
        "access-key": SARAMIN_API_KEY,
        "keywords":   keyword,
        "job_type":   1,
        "count":      count,
        "sort":       "pd",   # 최신순
        "fields":     "expiration-date,posting-date,job-category",
    }
    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=15)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        log.error(f"사람인 API 오류 ({keyword}): {e}")
        return []

    jobs_raw = data.get("jobs", {}).get("job", [])
    if isinstance(jobs_raw, dict):
        jobs_raw = [jobs_raw]

    results = []
    for j in jobs_raw:
        company  = j.get("company", {}).get("detail", {}).get("name", "")
        position = j.get("position", {}).get("title", "")
        exp_ts   = j.get("expiration-date", {}).get("time")
        post_ts  = j.get("posting-date", {}).get("time")
        exp_date = datetime.fromtimestamp(int(exp_ts)).strftime("%Y.%m.%d") if exp_ts else ""
        post_date= datetime.fromtimestamp(int(post_ts)).strftime("%Y.%m.%d") if post_ts else ""
        exp_level= j.get("position", {}).get("experience-level", {})
        results.append({
            "id":          make_id("saramin", company, position),
            "company":     company,
            "position":    position,
            "experience":  exp_level.get("name", "경력무관"),
            "exp_min":     int(exp_level.get("min", 0)),
            "location":    j.get("position", {}).get("location", {}).get("name", "").replace("&gt;", ">"),
            "expire_date": exp_date,
            "post_date":   post_date,
            "url":         j.get("url", ""),
            "source":      "사람인",
            "keyword":     keyword,
            "cat":         classify(company, position, keyword),
        })

    log.info(f"사람인 [{keyword}]: {len(results)}건")
    return results


# ── 원티드 API (비공개 API — 변경될 수 있음) ────────────
def fetch_wanted(keyword: str) -> list[dict]:
    url = "https://www.wanted.co.kr/api/v4/jobs"
    params = {
        "country":    "kr",
        "tag_type_id": 669,   # IT 보안 태그
        "limit":      100,
        "offset":     0,
        "years":      -1,
        "query":      keyword,
    }
    try:
        res = requests.get(url, params=params, headers={
            **HEADERS,
            "Referer":          "https://www.wanted.co.kr",
            "wanted-user-agent":"user-web",
        }, timeout=15)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        log.error(f"원티드 오류 ({keyword}): {e}")
        return []

    results = []
    for j in data.get("data", []):
        company  = j.get("company", {}).get("name", "")
        position = j.get("position", "")
        deadline = j.get("deadline", "") or ""
        if deadline == "2999-12-31":
            deadline = ""   # 상시 채용
        results.append({
            "id":          make_id("wanted", company, position),
            "company":     company,
            "position":    position,
            "experience":  j.get("experience_requirement", "경력무관") or "경력무관",
            "exp_min":     0,
            "location":    j.get("address", {}).get("location", ""),
            "expire_date": deadline,
            "post_date":   (j.get("created_time") or "")[:10],
            "url":         f"https://www.wanted.co.kr/wd/{j.get('id','')}",
            "source":      "원티드",
            "keyword":     keyword,
            "cat":         classify(company, position, keyword),
        })

    log.info(f"원티드 [{keyword}]: {len(results)}건")
    return results


# ── 중복 제거 ─────────────────────────────────────────
def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = {}
    for j in jobs:
        key = j["id"]
        if key not in seen:
            seen[key] = j
    return list(seen.values())


# ── 기존 데이터 로드 (증분 업데이트) ──────────────────
def load_existing() -> list[dict]:
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("jobs", [])
    except FileNotFoundError:
        return []
    except Exception as e:
        log.warning(f"기존 데이터 로드 실패: {e}")
        return []


# ── 저장 ──────────────────────────────────────────────
def save(jobs: list[dict]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    payload = {
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "total":      len(jobs),
        "jobs":       jobs,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info(f"저장 완료: {OUTPUT_FILE} ({len(jobs)}건)")


# ── 메인 ──────────────────────────────────────────────
def main() -> None:
    log.info("=== IT 보안 채용 크롤러 시작 ===")
    start = time.time()

    new_jobs: list[dict] = []

    for kw in KEYWORDS:
        new_jobs += fetch_saramin(kw, count=100)
        new_jobs += fetch_wanted(kw)
        time.sleep(1)   # 서버 부하 방지

    log.info(f"수집 총계 (중복 포함): {len(new_jobs)}건")

    # 기존 데이터와 병합
    existing = load_existing()
    merged   = deduplicate(existing + new_jobs)

    # 마감된 공고 제거 (만료일이 오늘 이전인 것)
    today = datetime.now().strftime("%Y.%m.%d")
    def is_valid(j: dict) -> bool:
        exp = j.get("expire_date", "")
        if not exp:
            return True   # 상시 채용
        return exp.replace("-",".") >= today

    active = [j for j in merged if is_valid(j)]
    log.info(f"유효 공고: {len(active)}건 (마감 제거 후)")

    save(active)
    log.info(f"=== 완료 ({time.time()-start:.1f}초) ===")


if __name__ == "__main__":
    main()
