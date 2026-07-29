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
        "zstt-requirement-clarification",
        (),
    ),
    StageContract(
        "repo_research",
        "01-research.md",
        "zstt-repo-research",
        ("requirement_clarification",),
    ),
    StageContract(
        "technical_design",
        "02-design.md",
        "zstt-technical-design",
        ("requirement_clarification", "repo_research"),
    ),
    StageContract(
        "task_breakdown",
        "03-tasks.md",
        "zstt-task-breakdown",
        ("requirement_clarification", "repo_research", "technical_design"),
    ),
    StageContract(
        "implementation",
        "04-implementation.md",
        "zstt-implementation",
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
        "zstt-code-review",
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
        "zstt-test-verify",
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
        "zstt-requirement-clarification",
        (),
    ),
    StageContract(
        "implementation",
        "01-implementation.md",
        "zstt-implementation",
        ("requirement_clarification",),
    ),
    StageContract(
        "code_review",
        "02-code-review.md",
        "zstt-code-review",
        ("requirement_clarification", "implementation"),
    ),
    StageContract(
        "test_verify",
        "03-test-report.md",
        "zstt-test-verify",
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


def recommended_next_skills(
    mode: str,
    completed_stages: list[str],
) -> tuple[str, ...]:
    completed = set(completed_stages)
    if mode == "full":
        for stage in FULL_STAGES:
            if stage.key not in completed:
                # 两个质量门禁是可选 handoff，不进入固定阶段；用户可直接选择固定下一阶段。
                if stage.key == "repo_research":
                    return ("zstt-requirement-checklist", stage.skill)
                if stage.key == "implementation":
                    return ("zstt-artifact-analysis", stage.skill)
                return (stage.skill,)
        return ()

    if mode != "quick":
        raise ValueError(f"未知工作流模式: {mode}")

    requirement = get_contract("quick", "requirement_clarification")
    implementation = get_contract("quick", "implementation")
    review = get_contract("quick", "code_review")
    verification = get_contract("quick", "test_verify")
    if requirement.key not in completed:
        return (requirement.skill,)
    if implementation.key not in completed:
        return (implementation.skill,)
    # Quick 的 Review 与测试都是用户可选分支；测试完成后流程结束，不能倒退推荐 Review。
    if verification.key in completed:
        return ()
    if review.key in completed:
        return (verification.skill,)
    return (review.skill, verification.skill)


def recommended_next_skill(mode: str, completed_stages: list[str]) -> str | None:
    recommendations = recommended_next_skills(mode, completed_stages)
    return recommendations[0] if recommendations else None
