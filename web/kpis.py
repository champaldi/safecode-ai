"""SIMULATED September 2027 KPIs (spec section 2). Statuses are computed, never hardcoded."""


def status(kind: str, target: float, sim: float) -> str:
    r = round(sim / target, 9) if target else 0
    if kind == "higher":  # revenue, teams, activation
        return "green" if r >= 0.95 else "yellow" if r >= 0.85 else "red"
    if kind == "burn":  # lower is better, relative to ceiling
        return "green" if r <= 1.05 else "yellow" if r <= 1.15 else "red"
    if kind == "churn":  # lower is better, absolute %
        return "green" if sim <= 2 else "yellow" if sim <= 3 else "red"
    if kind == "uptime":  # absolute %
        return "green" if sim >= 99.5 else "yellow" if sim >= 99.0 else "red"
    raise ValueError(kind)


KPIS = [
    ("F1", "Revenue", "higher", 1.125, 0.875, "KZT m", "Close stalled trials", "Aruzhan", "31 Oct 2027", False, ""),
    ("F2", "Net burn", "burn", 4.5, 4.9, "KZT m", "Cap model usage; cache fixes", "Aslan", "15 Oct 2027", True, "target is a ceiling"),
    ("C1", "Paying teams", "higher", 9, 7, "teams", "Setup calls and first-fix checklist", "Aruzhan", "31 Oct 2027", False, ""),
    ("C2", "Monthly churn", "churn", 2, 0, "%", "Continue monitoring", "Aruzhan", "monthly", True, "target is a ceiling"),
    ("O1", "Uptime", "uptime", 99.5, 99.7, "%", "Continue monitoring", "Aldiyar", "weekly", False, ""),
    ("O2", "Activation (first merged fix <=24h)", "higher", 40, 30.8, "%", "Fix installation blockers", "Aslan", "31 Oct 2027", False, "8 of 26"),
]


def cards():
    out = []
    for id_, name, kind, target, sim, unit, action, owner, due, lower, note in KPIS:
        out.append({"id": id_, "name": name, "unit": unit, "target": target, "simulated": sim,
                    "deviation": round(sim - target, 4), "deviation_pct": round((sim - target) / target * 100, 1),
                    "status": status(kind, target, sim), "lower_is_better": lower, "note": note,
                    "action": action, "owner": owner, "deadline": due})
    return out
