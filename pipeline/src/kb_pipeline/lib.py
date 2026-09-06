"""Shared helpers for the xmg-kb cleaning pipeline."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(os.environ.get("XMG_KB_ROOT", "/srv/xmg-kb"))
RAW = Path(os.environ.get("XMG_KB_RAW_EVIDENCE", "/srv/xmg-kb/evidence"))
LEGACY = Path(os.environ.get("XMG_KB_LEGACY_ROOT", "/srv/xmg-kb/legacy"))
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"
PARSED = ROOT / "parsed"
NORMALIZED = ROOT / "normalized"
DOCS = ROOT / "docs"

TEXT_EXT = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".csv"}
HTML_EXT = {".html", ".htm"}
OFFICE_EXT = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}
PDF_EXT = {".pdf"}
DOC_EXT = TEXT_EXT | HTML_EXT | OFFICE_EXT | PDF_EXT | {".xml", ".log", ".conf"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff",
             ".mp4", ".mov", ".avi", ".mkv", ".wav", ".mp3"}
ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz"}
EXEC_EXT = {".exe", ".dll", ".so", ".bin", ".msi", ".deb", ".rpm", ".apk", ".pyc"}
CONTROL_NAMES = {"cookies.json", "thumbs.db", ".ds_store"}

PRODUCT_DIR = {
    "SafeLine": "01-雷池-SafeLine", "X-Ray": "02-洞鉴-X-Ray",
    "CloudWalker": "03-牧云-CloudWalker", "DSensor": "04-谛听-DSensor",
    "T-Answer": "05-全悉-T-Answer", "Cosmos": "06-万象-Cosmos",
    "ApiSec": "07-ApiSec", "HostSecurity-CSK": "09-主机安全-CSK",
    "硬件知识": "10-硬件知识", "FK01": "12-FK01-网盾", "Yuntu": "13-云图",
    "Reversi": "14-墨攻-Reversi", "CT-DA": "15-CT-DA-数据库审计",
    "CT-AC": "16-CT-AC-上网行为管理", "Matrix": "17-Matrix-纵横",
    "CT-LA": "18-CT-LA-日志审计", "CTDSG-E": "19-CTDSG-E-防火墙",
    "CT-OAM": "20-CT-OAM-堡垒机", "TrafficAnalysis": "21-流量分析预警",
    "CTDSG": "22-CTDSG-深度安全网关", "产品联动": "91-产品联动",
    "FDE": "FDE", "通用基础": "00-通用基础",
}
INGEST_MODULE = "90-原始文档增量"

PRODUCT_PATTERNS = [
    ("SafeLine", re.compile(r"雷池|SafeLine|safeline|Safeline|SL[-_ ]?\d+")),
    ("X-Ray", re.compile(r"洞鉴|X[-_ ]?Ray|x-ray|X-Ray")),
    ("CloudWalker", re.compile(r"牧云|CloudWalker|cloudwalker")),
    ("DSensor", re.compile(r"谛听|D[-_ ]?Sensor")),
    ("T-Answer", re.compile(r"全悉|T[-_ ]?Answer|TotalAware")),
    ("Cosmos", re.compile(r"万象|Cosmos|cosmos")),
    ("ApiSec", re.compile(r"ApiSec|apisec|API\s*安全")),
    ("HostSecurity-CSK", re.compile(r"CSK|主机安全|云主机安全")),
    ("Yuntu", re.compile(r"云图|Yuntu")),
    ("Reversi", re.compile(r"墨攻|Reversi")),
    ("CT-DA", re.compile(r"CT[-_ ]?DA|数据库审计")),
    ("CT-AC", re.compile(r"CT[-_ ]?AC|上网行为管理")),
    ("Matrix", re.compile(r"Matrix|纵横")),
    ("CT-LA", re.compile(r"CT[-_ ]?LA|日志审计")),
    ("CTDSG-E", re.compile(r"CTDSG[-_ ]?E|第二代防火墙")),
    ("CT-OAM", re.compile(r"CT[-_ ]?OAM|堡垒机")),
    ("TrafficAnalysis", re.compile(r"流量分析预警")),
    ("CTDSG", re.compile(r"CTDSG|深度安全网关")),
    ("FK01", re.compile(r"FK0?1|网盾")),
    ("FDE", re.compile(r"\bFDE\b|全盘加密")),
]


# Single source of truth for credential detection AND masking.  Do NOT add \b:
# in Chinese text "密码：" is usually preceded by a CJK word character, so a
# \b anchor silently fails to match, which makes the detector flag a secret
# that the masker then cannot find (leak).  Detection and masking must agree.
CREDENTIAL_RE = re.compile(
    r"(?i)(password|passwd|token|secret|api[_-]?key|密码|口令)\s*([:=：])\s*([^\s<>{}]{4,})")

# Replacement token.  It must be single-sourced: the detector has to recognise
# it as safe, otherwise an already-masked document is flagged forever (the
# token itself matches the "looks like a real secret" character class).
MASK_TOKEN = "***MASKED***"

# Public defaults / documentation placeholders.  Shared so the detector and the
# masker agree: a value in this set is NOT a real secret and must not be flagged
# (outline task 06: do not treat a documented default password as a leak).
PLACEHOLDER_VALUE = re.compile(
    r"(?i)^(?:admin|root|test|demo|example|changeme|password|passwd|123456|1234|111111"
    r"|x{3,}|\*{3,}|xxx|your[_-]?password|<[^>]*>|\{\{[^}]*\}\}|\"[^\"]*\"|'[^']*')$")
REAL_SECRET = re.compile(r"[A-Za-z0-9!@#$%^&*_+\-./=]{6,}")

# Only explicit identity assignments are sensitive; a generic mention of
# 客户环境 / 客户现场 in a procedure is not a leak.
CUSTOMER_ID_RE = re.compile(r"(客户名称|客户地址|客户单位|客户联系人)\s*[:：]\s*(\S+)")


# Legacy/curated front matter carries free-form product strings.  Map the known
# variants onto the canonical taxonomy; anything unrecognised is left untouched
# (never guessed) so it can be surfaced for review instead of fabricated.
PRODUCT_ALIASES = {
    "雷池": "SafeLine", "safeline": "SafeLine", "雷池-safeline": "SafeLine",
    "洞鉴": "X-Ray", "x-ray": "X-Ray", "xray": "X-Ray",
    "牧云": "CloudWalker", "cloudwalker": "CloudWalker",
    "谛听": "DSensor", "dsensor": "DSensor",
    "全悉": "T-Answer", "t-answer": "T-Answer", "totalaware": "T-Answer",
    "万象": "Cosmos", "cosmos": "Cosmos",
    "apisec": "ApiSec", "apisec（api安全系统）": "ApiSec", "api安全": "ApiSec",
    "主机安全": "HostSecurity-CSK", "csk": "HostSecurity-CSK",
    "云图": "Yuntu", "墨攻": "Reversi",
    "数据库审计": "CT-DA", "上网行为管理": "CT-AC",
    "日志审计": "CT-LA", "堡垒机": "CT-OAM",
    "纵横": "Matrix", "网盾": "FK01",
    "深度安全网关": "CTDSG", "第二代防火墙": "CTDSG-E",
    "流量分析预警": "TrafficAnalysis",
    "通用基础": "通用基础", "硬件知识": "硬件知识", "产品联动": "产品联动",
}


def canonical_product(value: str) -> tuple[str, bool]:
    """Return (canonical_value, changed). Unrecognised values pass through."""
    if not value:
        return value, False
    if value in PRODUCT_DIR:
        return value, False
    key = value.strip()
    if key in PRODUCT_ALIASES:
        return PRODUCT_ALIASES[key], True
    lowered_map = {k.lower(): v for k, v in PRODUCT_ALIASES.items()}
    lowered = key.lower()
    if lowered in lowered_map:
        return lowered_map[lowered], True
    # tolerate "07-ApiSec" / "01-雷池-SafeLine" style directory prefixes
    stripped = re.sub(r"^\d{2}-", "", key)
    if stripped in PRODUCT_DIR:
        return stripped, True
    if stripped.lower() in lowered_map:
        return lowered_map[stripped.lower()], True
    return value, False


def ensure_dirs() -> None:
    for d in (DATA, REPORTS, LOGS, PARSED, NORMALIZED, REVIEW_DIR):
        d.mkdir(parents=True, exist_ok=True)


REVIEW_DIR = ROOT / "review"


def normalize(t: str) -> str:
    """Byte-identical to the historical preprocess.normalize()."""
    t = unicodedata.normalize("NFKC", t).replace("\x00", "")
    t = re.sub(r"^---\s*\n.*?\n---\s*\n", "", t, 1, flags=re.S)
    t = re.sub(r"https?://\S+", " URL ", t)
    t = re.sub(r"\s+", "", t).lower()
    return t


def normalized_sha(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, 1, flags=re.S)


def norm_body(text: str) -> str:
    """Normalize a document body with its front matter removed."""
    return normalize(strip_frontmatter(text))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def connect(db_name: str) -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATA / db_name, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=60000")
    return con


def classify_product(text: str, path_hint: str = "") -> tuple[str, float]:
    sample = (path_hint + "\n" + text[:60000])
    scores = {}
    for name, rx in PRODUCT_PATTERNS:
        hits = len(rx.findall(sample))
        if hits:
            scores[name] = hits
    if not scores:
        return "unknown", 0.0
    best = max(scores, key=scores.get)
    mx = scores[best]
    ties = sum(1 for v in scores.values() if v == mx)
    if ties > 1:
        return "unknown", 0.4
    conf = 0.9 if mx >= 3 else (0.75 if mx >= 2 else 0.5)
    return best, conf


def write_manifest(path: Path, records: list[dict], key: str = "original_path") -> int:
    """Merge records into a manifest, preserving entries from earlier runs.

    Overwriting would silently drop the provenance of files archived by a
    previous run once that run's decisions no longer reproduce (outline task 04
    requires archived material to stay traceable).
    """
    merged: dict[str, dict] = {}
    if path.exists():
        for line in path.open():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if key in rec:
                merged[rec[key]] = rec
    for rec in records:
        if key in rec:
            merged[rec[key]] = rec
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for rec in merged.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(merged)


def log_event(con: sqlite3.Connection, stage: str, file_id: str,
              status: str, message: str = "") -> None:
    con.execute(
        "INSERT INTO events(stage,file_id,status,message,created_at) VALUES(?,?,?,?,?)",
        (stage, file_id, status, message[:500], _now()))
    con.commit()


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
