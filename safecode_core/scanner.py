"""Python rules (stdlib ast, no external deps). Emits raw findings plus facts in `ctx` for the FP filter."""
import ast
import hashlib
import re

from . import fixes
from .models import Finding, Fix

RULES = {"sql-injection": ("critical", "CWE-89"), "hardcoded-secret": ("high", "CWE-798"),
         "weak-hash": ("high", "CWE-327"), "insecure-random": ("high", "CWE-338"),
         "shell-injection": ("high", "CWE-78")}
SECRET_NAME = re.compile(r"password|passwd|secret|token|api_?key|private_key|access_key", re.I)
PASS_CTX = re.compile(r"pass(word|wd|phrase)|pwd", re.I)
SEC_CTX = re.compile(r"token|secret|passw|pwd|otp|reset|session|nonce|salt|csrf|api_?key|auth", re.I)
TEST_PATH = re.compile(r"(^|/)tests?/|(^|/)test_[^/]*$|_test\.py$")
RANDOM_FNS = {"random", "randint", "choice", "choices", "getrandbits", "randrange", "sample"}
SUBPROC = {"run", "call", "check_call", "check_output", "Popen"}


def _has_import(src, name):
    return bool(re.search(rf"^\s*(import [^\n#]*\b{name}\b|from {name} import)", src, re.M))


class _V(ast.NodeVisitor):
    def __init__(self, path, src):
        self.path, self.src, self.lines = path, src, src.split("\n")
        self.funcs, self.stmt, self.out = [], None, []

    def visit(self, node):
        if isinstance(node, ast.stmt):
            prev, self.stmt = self.stmt, node
            super().visit(node)
            self.stmt = prev
        else:
            super().visit(node)

    def visit_FunctionDef(self, n):
        self.funcs.append(n.name)
        self.generic_visit(n)
        self.funcs.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def seg(self, n):
        return ast.get_source_segment(self.src, n)

    def text(self, n):
        return "\n".join(self.lines[n.lineno - 1:n.end_lineno])

    def near(self, n):
        s = self.stmt
        if s is None or isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            s = n
        return self.text(s) + " " + " ".join(self.funcs)

    def in_test(self):
        return bool(TEST_PATH.search(self.path)) or any(f.startswith("test_") for f in self.funcs)

    def add(self, rule, n, new=None, inner=None, imp=None, **ctx):
        """new/inner: replace source `inner` inside node `n` with `new` (the fix); imp: import the fix needs."""
        sev, cwe = RULES[rule]
        snippet = self.text(n)
        fid = hashlib.sha1(f"{rule}|{self.path}|{' '.join(snippet.split())}".encode()).hexdigest()[:12]
        fix = None
        if new is not None:
            s = self.seg(n)
            i = s.rfind(inner)
            new_node = s[:i] + new + s[i + len(inner):]
            first = self.lines[n.lineno - 1].encode()[:n.col_offset].decode()
            last = self.lines[n.end_lineno - 1].encode()[n.end_col_offset:].decode()
            ok = imp is None or _has_import(self.src, imp)
            fix = Fix(snippet, first + new_node + last, suggestion_ok=ok,
                      note="" if ok else f"add `import {imp}`")
        ctx["in_test"] = self.in_test()
        self.out.append(Finding(fid, rule, sev, cwe, self.path, n.lineno, n.end_lineno, snippet, ctx, fix))

    def visit_Call(self, n):
        f = n.func
        if isinstance(f, ast.Attribute):
            self.sql(n, f)
            self.hashcall(n, f)
            self.rand(n, f)
            self.shell(n, f)
        self.generic_visit(n)

    def sql(self, n, f):
        if f.attr != "execute" or len(n.args) != 1 or n.keywords:
            return
        a = n.args[0]
        const = (isinstance(a, ast.Constant) and isinstance(a.value, str)) or \
                (isinstance(a, ast.JoinedStr) and not any(isinstance(v, ast.FormattedValue) for v in a.values))
        new = fixes.parametrize(self.seg(a)) if isinstance(a, ast.JoinedStr) and not const else None
        self.add("sql-injection", n, new, self.seg(a), constant_sql=const)

    def hashcall(self, n, f):
        if isinstance(f.value, ast.Name) and f.value.id == "hashlib" and f.attr in ("md5", "sha1"):
            self.add("weak-hash", n, "hashlib.sha256", self.seg(f), password_ctx=bool(PASS_CTX.search(self.near(n))))

    def rand(self, n, f):
        if not (isinstance(f.value, ast.Name) and f.value.id == "random" and f.attr in RANDOM_FNS):
            return
        a = [self.seg(x) for x in n.args]
        new = None
        if f.attr == "choice" and len(a) == 1:
            new = f"secrets.choice({a[0]})"
        elif f.attr == "randint" and len(a) == 2:
            new = f"({a[0]} + secrets.randbelow({a[1]} - {a[0]} + 1))"
        elif f.attr == "getrandbits" and len(a) == 1:
            new = f"secrets.randbits({a[0]})"
        self.add("insecure-random", n, new, self.seg(n), "secrets", sec_ctx=bool(SEC_CTX.search(self.near(n))))

    def shell(self, n, f):
        if not (isinstance(f.value, ast.Name) and f.value.id == "subprocess" and f.attr in SUBPROC):
            return
        if not any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True
                   for k in n.keywords):
            return
        a = n.args[0] if n.args else None
        lit = isinstance(a, ast.Constant) or (isinstance(a, (ast.List, ast.Tuple))
                                              and all(isinstance(e, ast.Constant) for e in a.elts))
        full, new = self.seg(n), None
        lst = fixes.shell_list(self.seg(a)) if isinstance(a, ast.JoinedStr) else None
        if lst:
            new = re.sub(r",\s*shell\s*=\s*True", "", full, count=1).replace(self.seg(a), lst, 1)
            if new == full:
                new = None
        self.add("shell-injection", n, new, full, literal_cmd=lit)

    def _secret(self, n, name, value):
        if isinstance(value, ast.Constant) and isinstance(value.value, str) and len(value.value) >= 8 \
                and not any(c.isspace() for c in value.value) and SECRET_NAME.search(name):
            self.add("hardcoded-secret", n, f'os.environ["{name.upper()}"]', self.seg(value), "os")

    def visit_Assign(self, n):
        if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            self._secret(n, n.targets[0].id, n.value)
        self.generic_visit(n)

    def visit_AnnAssign(self, n):
        if isinstance(n.target, ast.Name) and n.value is not None:
            self._secret(n, n.target.id, n.value)
        self.generic_visit(n)


def scan_source(path: str, source: str) -> list[Finding]:
    """Raises SyntaxError on unparseable files (caller decides)."""
    source = source.replace("\r\n", "\n")
    v = _V(path, source)
    v.visit(ast.parse(source))
    return v.out
