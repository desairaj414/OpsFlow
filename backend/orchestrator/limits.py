"""Turn caps + explicit termination conditions per agent (PRD §3.3 "more turns ≠ better" —
ITBench finding, MAST's "unaware of termination conditions" failure mode). An agent forced past
its cap terminates with an explicit reason, never silently.
"""

TURN_CAPS = {
    "enrichment": 3,
    "diagnosis": 3,
    "planner": 2,
    "verification": 2,
    "sync": 1,
    "knowledge": 1,
}

TERMINATION_CAP_EXCEEDED = "turn_cap_exceeded"


class TurnCapExceeded(Exception):
    def __init__(self, agent_name: str, cap: int):
        self.agent_name = agent_name
        self.cap = cap
        super().__init__(f"{agent_name} exceeded its turn cap of {cap}")


class TurnTracker:
    """Agents call use_turn() once per reasoning/tool-call step. Raises TurnCapExceeded the
    instant the cap is crossed — the agent must catch this and return an explicit
    termination_reason, never let it propagate as an unhandled crash."""

    def __init__(self, agent_name: str):
        if agent_name not in TURN_CAPS:
            raise ValueError(f"no turn cap registered for agent '{agent_name}' — add one to TURN_CAPS")
        self.agent_name = agent_name
        self.cap = TURN_CAPS[agent_name]
        self.turns_used = 0

    def use_turn(self) -> int:
        self.turns_used += 1
        if self.turns_used > self.cap:
            raise TurnCapExceeded(self.agent_name, self.cap)
        return self.turns_used

    def remaining(self) -> int:
        return max(0, self.cap - self.turns_used)
