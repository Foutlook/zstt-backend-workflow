from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageContract:
    key: str
    artifact: str
    skill: str
    required: tuple[str, ...]


FULL_STAGES = (
    StageContract(
        "requirement_clarification",
        "00-requirement.md",
        "zztt-requirement-clarification",
        (),
    ),
    StageContract(
        "repo_research",
        "01-research.md",
        "zztt-repo-research",
        ("requirement_clarification",),
    ),
    StageContract(
        "technical_design",
        "02-design.md",
        "zztt-technical-design",
        ("requirement_clarification", "repo_research"),
    ),
    StageContract(
        "task_breakdown",
        "03-tasks.md",
        "zztt-task-breakdown",
        ("requirement_clarification", "repo_research", "technical_design"),
    ),
    StageContract(
        "implementation",
        "04-implementation.md",
        "zztt-implementation",
        (
            "requirement_clarification",
            "repo_research",
            "technical_design",
            "task_breakdown",
        ),
    ),
    StageContract(
        "code_review",
        "05-code-review.md",
        "zztt-code-review",
        (
            "requirement_clarification",
            "repo_research",
            "technical_design",
            "task_breakdown",
            "implementation",
        ),
    ),
    StageContract(
        "test_verify",
        "06-test-report.md",
        "zztt-test-verify",
        (
            "requirement_clarification",
            "repo_research",
            "technical_design",
            "task_breakdown",
            "implementation",
            "code_review",
        ),
    ),
)

QUICK_STAGES = (
    StageContract(
        "requirement_clarification",
        "00-requirement.md",
        "zztt-requirement-clarification",
        (),
    ),
    StageContract(
        "implementation",
        "01-implementation.md",
        "zztt-implementation",
        ("requirement_clarification",),
    ),
    StageContract(
        "code_review",
        "02-code-review.md",
        "zztt-code-review",
        ("requirement_clarification", "implementation"),
    ),
    StageContract(
        "test_verify",
        "03-test-report.md",
        "zztt-test-verify",
        ("requirement_clarification", "implementation"),
    ),
)


def stages_for(mode: str) -> tuple[StageContract, ...]:
    if mode == "full":
        return FULL_STAGES
    if mode == "quick":
        return QUICK_STAGES
    raise ValueError(f"未知工作流模式: {mode}")


def get_contract(mode: str, stage_key: str) -> StageContract:
    for stage in stages_for(mode):
        if stage.key == stage_key:
            return stage
    raise ValueError(f"未知阶段: {stage_key}")


def required_predecessors(mode: str, stage_key: str) -> tuple[str, ...]:
    return get_contract(mode, stage_key).required


def recommended_next_skill(mode: str, completed_stages: list[str]) -> str | None:
    completed = set(completed_stages)
    for stage in stages_for(mode):
        if stage.key not in completed:
            return stage.skill
    return None
