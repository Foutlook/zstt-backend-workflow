from __future__ import annotations

import re
from pathlib import Path


INVALID_NAME_PATTERN = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff_-]+")


def sanitize_feature_name(feature_name: str) -> str:
    normalized = INVALID_NAME_PATTERN.sub("-", feature_name.strip())
    normalized = re.sub(r"-+", "-", normalized).strip("-_")
    if not normalized:
        raise ValueError("需求名称不能为空")
    return normalized


def feature_directory(
    repo_root: Path,
    mode: str,
    feature_name: str,
    date_text: str,
) -> Path:
    if not re.fullmatch(r"\d{8}", date_text):
        raise ValueError("日期必须使用 YYYYMMDD 格式")
    if mode not in {"full", "quick"}:
        raise ValueError(f"未知工作流模式: {mode}")

    category = "features" if mode == "full" else "quick"
    base = (repo_root.resolve() / ".zstt" / category).resolve()
    target = (base / f"{date_text}-{sanitize_feature_name(feature_name)}").resolve()
    if not target.is_relative_to(base):
        raise ValueError("需求目录不能超出业务仓库的 .zstt 范围")
    return target
