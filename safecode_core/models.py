from dataclasses import dataclass, field

SEV_ORDER = {"medium": 1, "high": 2, "critical": 3}


@dataclass
class Fix:
    before: str
    after: str
    source: str = "Rule-based fix"  # LLM never writes fixes in this MVP
    suggestion_ok: bool = True  # False -> shown as a normal code block ("manual fix")
    note: str = ""


@dataclass
class Finding:
    id: str
    rule: str
    severity: str
    cwe: str
    file: str
    line: int
    end_line: int
    snippet: str
    ctx: dict = field(default_factory=dict)  # facts for the FP filter
    fix: Fix | None = None
    filtered: bool = False
    reason_key: str = ""
    reason: str = ""  # human text (rule hint, or LLM verdict)
    ai_verdict: bool = False

    def ingest(self):
        return {"id": self.id, "rule": self.rule, "severity": self.severity, "file": self.file,
                "line": self.line, "filtered": self.filtered, "reason": self.reason_key or self.reason,
                "fix_source": self.fix.source if self.fix else None}
