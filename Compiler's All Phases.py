import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont
import re
import ast
import operator as op

APP_TITLE = "Compiler Construction Lab — Phase Analyzer"

# ----------------------------- Utilities -----------------------------

def safe_eval(expr):
    """Evaluate simple arithmetic expressions without executing arbitrary code."""
    tree = ast.parse(expr, mode="eval")

    allowed_bin = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
        ast.Div: op.truediv, ast.FloorDiv: op.floordiv,
        ast.Mod: op.mod, ast.Pow: op.pow
    }
    allowed_unary = {ast.UAdd: op.pos, ast.USub: op.neg}

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_bin:
            return allowed_bin[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_unary:
            return allowed_unary[type(node.op)](walk(node.operand))
        raise ValueError("Only numeric arithmetic expressions are supported.")

    return walk(tree)


def show_text(value):
    if isinstance(value, list):
        return "\n".join(str(x) for x in value)
    return str(value)


# ----------------------------- Lexer -----------------------------

KEYWORDS = {
    "int", "float", "char", "string", "bool", "if", "else",
    "while", "for", "return", "void", "true", "false"
}

TOKEN_RE = re.compile(
    r'(?P<SPACE>\s+)'
    r'|(?P<COMMENT>//[^\n]*)'
    r'|(?P<NUMBER>\d+(?:\.\d+)?)'
    r'|(?P<STRING>"[^"\n]*"|\'[^\'\n]*\')'
    r'|(?P<ID>[A-Za-z_][A-Za-z0-9_]*)'
    r'|(?P<OP>==|!=|<=|>=|\+\+|--|&&|\|\||[+\-*/%=<>!])'
    r'|(?P<SYM>[(){}\[\],;:])'
)

def lexical_analysis(source):
    tokens = []
    errors = []
    line = 1
    pos = 0

    while pos < len(source):
        match = TOKEN_RE.match(source, pos)
        if not match:
            errors.append(f"Line {line}: Invalid character '{source[pos]}'")
            pos += 1
            continue

        text = match.group(0)
        kind = match.lastgroup

        if kind in ("SPACE", "COMMENT"):
            line += text.count("\n")
        else:
            if kind == "ID":
                token_type = "KEYWORD" if text in KEYWORDS else "IDENTIFIER"
            elif kind == "NUMBER":
                token_type = "NUMBER"
            elif kind == "STRING":
                token_type = "STRING"
            elif kind == "OP":
                token_type = "OPERATOR"
            else:
                token_type = "SYMBOL"

            tokens.append((len(tokens) + 1, line, token_type, text))
            line += text.count("\n")

        pos = match.end()

    return tokens, errors


# ----------------------------- Syntax Analysis -----------------------------

def syntax_analysis(source):
    """
    Lightweight syntax checker for common C-like constructs.
    It is intentionally simple for a Compiler Construction Lab project.
    """
    errors = []
    lines = source.splitlines()

    # Balanced delimiters
    pairs = {')': '(', '}': '{', ']': '['}
    stack = []
    opening = set("([{")

    for ln, line in enumerate(lines, 1):
        in_string = False
        quote = None
        for ch in line:
            if ch in "\"'" and not in_string:
                in_string, quote = True, ch
            elif in_string and ch == quote:
                in_string = False
            elif not in_string and ch in opening:
                stack.append((ch, ln))
            elif not in_string and ch in pairs:
                if not stack or stack[-1][0] != pairs[ch]:
                    errors.append(f"Line {ln}: Unexpected '{ch}'")
                else:
                    stack.pop()

    for ch, ln in reversed(stack):
        errors.append(f"Line {ln}: Missing closing delimiter for '{ch}'")

    # Basic statement checks
    for ln, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue

        if re.match(r"^(if|while)\s*\(", line) and ")" not in line:
            errors.append(f"Line {ln}: Missing ')' in condition")

        if re.match(r"^for\s*\(", line) and ")" not in line:
            errors.append(f"Line {ln}: Missing ')' in for statement")

        if re.match(r"^(int|float|char|string|bool)\s+\w+", line):
            if "=" in line and not line.endswith(";") and not line.endswith("{"):
                errors.append(f"Line {ln}: Missing ';'")

        if re.match(r"^[A-Za-z_]\w*\s*=", line):
            if not line.endswith(";") and not line.endswith("{"):
                errors.append(f"Line {ln}: Assignment should end with ';'")

    if errors:
        return False, errors

    return True, ["No basic syntax errors found."]


# ----------------------------- Semantic Analysis -----------------------------

TYPE_MAP = {
    "int": "int",
    "float": "float",
    "char": "char",
    "string": "string",
    "bool": "bool"
}

def semantic_analysis(source):
    symbols = []
    errors = []
    declared = {}

    lines = source.splitlines()

    declaration_re = re.compile(
        r"^(int|float|char|string|bool)\s+([A-Za-z_]\w*)"
        r"(?:\s*=\s*(.+?))?;"
    )

    for ln, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue

        m = declaration_re.match(line)
        if m:
            typ, name, value = m.groups()
            if name in declared:
                errors.append(f"Line {ln}: Variable '{name}' already declared.")
            else:
                declared[name] = typ
                symbols.append((name, typ, "local", ln))

            if value:
                value = value.strip()
                if value in declared:
                    pass
                elif typ == "int" and re.fullmatch(r"\d+", value):
                    pass
                elif typ == "float" and re.fullmatch(r"\d+(?:\.\d+)?", value):
                    pass
                elif typ == "string" and re.fullmatch(r'"[^"]*"', value):
                    pass
                elif typ == "char" and re.fullmatch(r"'.'", value):
                    pass
                elif typ == "bool" and value in ("true", "false"):
                    pass
                elif re.fullmatch(r"[\d\s+\-*/().]+", value):
                    try:
                        result = safe_eval(value)
                        if typ == "int" and not isinstance(result, int):
                            errors.append(f"Line {ln}: Type mismatch for '{name}'.")
                    except Exception:
                        errors.append(f"Line {ln}: Invalid initializer for '{name}'.")
                elif re.search(r"[A-Za-z_]\w*", value):
                    # Check identifiers used in the expression.
                    ids = re.findall(r"[A-Za-z_]\w*", value)
                    for ident in ids:
                        if ident not in declared and ident not in {"true", "false"}:
                            errors.append(
                                f"Line {ln}: Variable '{ident}' used before declaration."
                            )

        # Assignment checks
        a = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.+);$", line)
        if a:
            name, value = a.groups()
            if name not in declared:
                errors.append(f"Line {ln}: Variable '{name}' is not declared.")
            else:
                value = value.strip()
                ids = re.findall(r"[A-Za-z_]\w*", value)
                for ident in ids:
                    if ident not in declared and ident not in {"true", "false"}:
                        errors.append(
                            f"Line {ln}: Variable '{ident}' used before declaration."
                        )

    return symbols, errors


# ----------------------------- Intermediate Code -----------------------------

def generate_three_address(source):
    code = []
    temp = 1

    for raw in source.splitlines():
        line = raw.strip().rstrip(";")
        if not line:
            continue

        # declaration with initialization
        m = re.match(r"^(?:int|float|char|string|bool)\s+(\w+)\s*=\s*(.+)$", line)
        if m:
            lhs, rhs = m.groups()
            result, temp = expression_to_tac(lhs, rhs, code, temp)
            if result != lhs:
                code.append(f"{lhs} = {result}")
            continue

        # simple assignment
        m = re.match(r"^(\w+)\s*=\s*(.+)$", line)
        if m:
            lhs, rhs = m.groups()
            result, temp = expression_to_tac(lhs, rhs, code, temp)
            if result != lhs:
                code.append(f"{lhs} = {result}")

    return code


def expression_to_tac(lhs, expr, code, temp):
    """Generates three-address code for an arithmetic expression.

    Uses a small recursive-descent parser so that '*' and '/' bind
    tighter than '+' and '-', and parentheses are respected — e.g.
    '2 + 3 * 4' correctly produces t1 = 3 * 4 ; t2 = 2 + t1, instead
    of evaluating strictly left-to-right.
    """
    expr = expr.strip()
    tokens = re.findall(r"\d+\.\d+|\d+|[A-Za-z_]\w*|[()+\-*/]", expr)

    if not tokens:
        return expr, temp

    state = {"pos": 0, "temp": temp}

    def peek():
        return tokens[state["pos"]] if state["pos"] < len(tokens) else None

    def emit(operator, left, right):
        t = f"t{state['temp']}"
        state["temp"] += 1
        code.append(f"{t} = {left} {operator} {right}")
        return t

    def parse_factor():
        tok = peek()
        if tok == "(":
            state["pos"] += 1
            value = parse_expression()
            if peek() == ")":
                state["pos"] += 1
            return value
        state["pos"] += 1
        return tok

    def parse_term():
        left = parse_factor()
        while peek() in ("*", "/"):
            operator = peek()
            state["pos"] += 1
            right = parse_factor()
            left = emit(operator, left, right)
        return left

    def parse_expression():
        left = parse_term()
        while peek() in ("+", "-"):
            operator = peek()
            state["pos"] += 1
            right = parse_term()
            left = emit(operator, left, right)
        return left

    result = parse_expression()
    return result, state["temp"]


# ----------------------------- Code Optimization -----------------------------

def constant_folding(source):
    result = []
    for raw in source.splitlines():
        line = raw
        m = re.match(r"^(\s*(?:int|float)\s+\w+\s*=\s*)([\d\s+\-*/().]+)(\s*;?\s*)$", line)
        if m:
            try:
                value = safe_eval(m.group(2))
                result.append(m.group(1) + str(value) + m.group(3))
                continue
            except Exception:
                pass

        m2 = re.match(r"^(\s*\w+\s*=\s*)([\d\s+\-*/().]+)(\s*;?\s*)$", line)
        if m2:
            try:
                value = safe_eval(m2.group(2))
                result.append(m2.group(1) + str(value) + m2.group(3))
                continue
            except Exception:
                pass

        result.append(line)
    return "\n".join(result)


def copy_propagation(source):
    lines = source.splitlines()
    copies = {}
    out = []

    for line in lines:
        m = re.match(
            r"^(\s*)(?:(?:int|float|char|string|bool)\s+)?(\w+)\s*=\s*(\w+)\s*;\s*$",
            line
        )
        if m:
            lhs, rhs = m.group(2), m.group(3)
            if lhs != rhs:
                copies[lhs] = rhs
            out.append(line)
            continue

        for lhs, rhs in list(copies.items()):
            line = re.sub(rf"\b{re.escape(lhs)}\b", rhs, line)
        out.append(line)

    return "\n".join(out)


def dead_code_elimination(source):
    lines = source.splitlines()
    assignments = []

    for i, line in enumerate(lines):
        m = re.match(r"^\s*(?:(?:int|float|char|string|bool)\s+)?(\w+)\s*=\s*(.+?);?\s*$", line)
        if m:
            assignments.append((i, m.group(1)))

    used_after = set()
    remove = set()

    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        ids = set(re.findall(r"\b[A-Za-z_]\w*\b", line))

        m = re.match(r"^\s*(?:(?:int|float|char|string|bool)\s+)?(\w+)\s*=\s*(.+?);?\s*$", line)
        if m:
            lhs = m.group(1)
            rhs_ids = set(re.findall(r"\b[A-Za-z_]\w*\b", m.group(2)))

            # If assigned variable is not used later, remove it only when
            # RHS has no obvious side effect.
            if lhs not in used_after and not re.search(r"\b(print|input)\s*\(", line):
                remove.add(i)

            used_after.discard(lhs)
            used_after.update(rhs_ids)
        else:
            used_after.update(ids)

    return "\n".join(line for i, line in enumerate(lines) if i not in remove)


def common_subexpression_elimination(source):
    lines = source.splitlines()
    seen = {}
    out = []

    for line in lines:
        m = re.match(
            r"^(\s*)((?:int|float|char|string|bool)\s+)?(\w+)\s*=\s*(\w+\s*[+\-*/]\s*\w+)\s*;\s*$",
            line
        )
        if not m:
            out.append(line)
            continue

        indent, type_kw, lhs, expr = m.groups()
        type_kw = type_kw or ""
        normalized = re.sub(r"\s+", "", expr)

        if normalized in seen:
            out.append(f"{indent}{type_kw}{lhs} = {seen[normalized]};")
        else:
            seen[normalized] = lhs
            out.append(line)

    return "\n".join(out)


def avoid_unnecessary_calculation(source):
    lines = []
    for line in source.splitlines():
        line = re.sub(r"\b(\w+)\s*\*\s*2\b", r"\1 + \1", line)
        line = re.sub(r"\b2\s*\*\s*(\w+)\b", r"\1 + \1", line)
        line = re.sub(r"\b(\w+)\s*\+\s*0\b", r"\1", line)
        line = re.sub(r"\b0\s*\+\s*(\w+)\b", r"\1", line)
        line = re.sub(r"\b(\w+)\s*\*\s*1\b", r"\1", line)
        line = re.sub(r"\b1\s*\*\s*(\w+)\b", r"\1", line)
        lines.append(line)
    return "\n".join(lines)


# ----------------------------- CFG / FIRST / FOLLOW -----------------------------

# Accepts "->", "-->", and "=>" as a grammar arrow.
# Marks the start of a production rule, e.g. "A ->", "B -->", "Expr =>".
# Used to split grammar text into individual rules no matter whether the
# person separates them with newlines, commas, or semicolons.
RULE_HEAD_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_']*)\s*(?:-+>|=>)")


def parse_grammar(text):
    """Parses grammar rules like 'A -> aaB | bC'.

    Rules may be separated by newlines, commas, or semicolons — all of
    these are equivalent:
        A -> aB
        B -> b
    or
        A -> aB, B -> b
    or
        A -> aB; B -> b

    Each rule's symbols may be written in two notations:
      1. Space-separated tokens (multi-char terminals allowed):
             E -> E + T | T
             T -> id
      2. Concatenated textbook notation, one char per symbol, where
         any string that matches a known nonterminal (a left-hand
         side used somewhere in the grammar) is treated as a single
         nonterminal symbol and everything else as a terminal char:
             A -> aaB | c
             B -> cbC
    """
    matches = list(RULE_HEAD_RE.finditer(text))
    if not matches:
        return {}

    # First pass: collect every left-hand side so concatenated
    # productions can recognize nonterminals (including multi-char
    # ones) rather than only single uppercase letters.
    nonterminal_names = {m.group(1) for m in matches}

    # Longest names first, so a nonterminal like "Expr" is matched
    # before a single-letter nonterminal that happens to be a prefix.
    sorted_nts = sorted(nonterminal_names, key=len, reverse=True)

    def split_alternative(alt):
        alt = alt.strip()
        if not alt or alt in ("ε", "epsilon", "eps"):
            return ["ε"]

        if " " in alt:
            # Traditional space-separated tokens, e.g. "E + T" or "id".
            symbols = alt.split()
            return symbols if symbols else ["ε"]

        # No internal spaces: this is either a single multi-char
        # terminal (e.g. "id", "num") or concatenated textbook
        # notation (e.g. "aaB", by convention uppercase = nonterminal,
        # everything else = terminal). Only enter concatenated mode
        # when there's a real signal for it — a known nonterminal
        # name embedded in the text, or an uppercase letter — so
        # things like "id" keep working exactly as before.
        has_known_nt = any(nt and nt in alt for nt in sorted_nts)
        has_uppercase = any(ch.isupper() for ch in alt)
        if not has_known_nt and not has_uppercase:
            return [alt]

        symbols = []
        i = 0
        while i < len(alt):
            matched = None
            for nt in sorted_nts:
                if nt and alt.startswith(nt, i):
                    matched = nt
                    break
            if matched:
                symbols.append(matched)
                i += len(matched)
            else:
                symbols.append(alt[i])
                i += 1
        return symbols if symbols else ["ε"]

    grammar = {}
    for i, m in enumerate(matches):
        left = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        rhs_text = text[start:end].strip()
        rhs_text = rhs_text.strip(",;").strip()
        if not rhs_text:
            continue
        alternatives = [x.strip() for x in rhs_text.split("|")]
        productions = [split_alternative(alt) for alt in alternatives]
        grammar.setdefault(left, []).extend(productions)

    return grammar


def first_sets(grammar):
    nonterminals = set(grammar)
    first = {nt: set() for nt in nonterminals}

    changed = True
    while changed:
        changed = False
        for nt, productions in grammar.items():
            for prod in productions:
                if prod == ["ε"]:
                    if "ε" not in first[nt]:
                        first[nt].add("ε")
                        changed = True
                    continue

                nullable = True
                for symbol in prod:
                    if symbol not in nonterminals:
                        before = len(first[nt])
                        first[nt].add(symbol)
                        changed |= len(first[nt]) != before
                        nullable = False
                        break

                    before = len(first[nt])
                    first[nt].update(first[symbol] - {"ε"})
                    changed |= len(first[nt]) != before

                    if "ε" not in first[symbol]:
                        nullable = False
                        break

                if nullable:
                    if "ε" not in first[nt]:
                        first[nt].add("ε")
                        changed = True

    return first


def first_of_sequence(seq, grammar, first):
    nonterminals = set(grammar)
    result = set()

    if not seq:
        result.add("ε")
        return result

    nullable = True
    for symbol in seq:
        if symbol not in nonterminals:
            result.add(symbol)
            nullable = False
            break

        result.update(first[symbol] - {"ε"})
        if "ε" not in first[symbol]:
            nullable = False
            break

    if nullable:
        result.add("ε")

    return result


def follow_sets(grammar, first):
    nonterminals = set(grammar)
    follow = {nt: set() for nt in nonterminals}
    start = next(iter(grammar))
    follow[start].add("$")

    changed = True
    while changed:
        changed = False

        for A, productions in grammar.items():
            for prod in productions:
                for i, B in enumerate(prod):
                    if B not in nonterminals:
                        continue

                    beta = prod[i + 1:]
                    beta_first = first_of_sequence(beta, grammar, first)

                    before = len(follow[B])
                    follow[B].update(beta_first - {"ε"})

                    if "ε" in beta_first or not beta:
                        follow[B].update(follow[A])

                    changed |= len(follow[B]) != before

    return follow


def parsing_table(grammar, first, follow):
    table = {}
    conflicts = []
    for A, productions in grammar.items():
        for prod in productions:
            f = first_of_sequence(prod, grammar, first)
            targets = f - {"ε"}

            if "ε" in f:
                targets |= follow[A]

            for terminal in targets:
                key = (A, terminal)
                value = f"{A} -> {' '.join(prod)}"
                if key in table and table[key] != value:
                    conflicts.append(
                        f"Conflict at M[{A}, {terminal}]: "
                        f"{table[key]} / {value}"
                    )
                else:
                    table[key] = value
    return table, conflicts


def ll1_parse_trace(grammar, table, target, max_steps=300):
    """Simulates the classic stack-based LL(1) parsing algorithm driven
    by the generated parsing table: push $ and the start symbol, then
    repeatedly match terminals against the input or expand the top-of-
    stack nonterminal using M[top, lookahead]. Returns (steps, accepted)
    where each step is (stack_str, remaining_input_str, action_str)."""
    if not grammar or not target:
        return [], False

    start = next(iter(grammar))
    stack = ["$", start]
    input_syms = list(target) + ["$"]
    ip = 0
    steps = []

    for _ in range(max_steps):
        top = stack[-1] if stack else "$"
        cur = input_syms[ip] if ip < len(input_syms) else "$"
        stack_str = " ".join(stack) if stack else "ε"
        input_str = " ".join(input_syms[ip:]) if ip < len(input_syms) else "$"

        if top == "$" and cur == "$":
            steps.append((stack_str, input_str, "ACCEPT"))
            return steps, True

        if top not in grammar:
            if top == "$":
                steps.append((stack_str, input_str, f"ERROR: unexpected end of stack, input remaining"))
                return steps, False
            if top == cur:
                steps.append((stack_str, input_str, f"Match '{top}'"))
                stack.pop()
                ip += 1
            else:
                steps.append((stack_str, input_str, f"ERROR: expected '{top}', found '{cur}'"))
                return steps, False
        else:
            entry = table.get((top, cur))
            if entry is None:
                steps.append((stack_str, input_str, f"ERROR: no rule for M[{top}, {cur}]"))
                return steps, False
            prod_symbols = entry.split("->", 1)[1].strip().split()
            steps.append((stack_str, input_str, f"Output: {entry}"))
            stack.pop()
            if prod_symbols != ["ε"]:
                for sym in reversed(prod_symbols):
                    stack.append(sym)

    steps.append(("...", "...", "ERROR: step limit exceeded (possible non-terminating grammar)"))
    return steps, False


# ----------------------------- Ambiguity / Derivations -----------------------------

def left_derivation_example():
    return """Grammar:
E -> E + T | T
T -> id

Input: id + id

Left Most Derivation:
E
=> E + T
=> T + T
=> id + T
=> id + id
"""


def right_derivation_example():
    return """Grammar:
E -> E + T | T
T -> id

Input: id + id

Right Most Derivation:
E
=> E + T
=> E + id
=> T + id
=> id + id
"""


def ambiguity_demo():
    return """Ambiguous Grammar:
E -> E + E | E * E | id

String:
id + id * id

The grammar can create more than one parse tree because
operator precedence is not defined.
Therefore, the grammar is ambiguous.
"""


def extract_target_string(text):
    """Looks for an explicit target string directive such as:
        Input: id + id
        String: id + id
        Target: id + id
    Returns (tokens_or_None, text_with_directive_removed).
    """
    m = re.search(r"(?im)^[ \t]*(?:input|string|target)[ \t]*:[ \t]*(.+)$", text)
    if not m:
        return None, text
    value = m.group(1).strip()
    cleaned = text[:m.start()] + text[m.end():]
    tokens = value.split() if value else None
    return tokens, cleaned


def _nonterminal_index(symbols, nonterminals, rightmost=False):
    positions = range(len(symbols) - 1, -1, -1) if rightmost else range(len(symbols))
    for i in positions:
        if symbols[i] in nonterminals:
            return i
    return -1


def derive_sentence(grammar, rightmost=False, target=None, max_steps=30):
    """Builds a step-by-step derivation from the grammar's start symbol.

    If `target` (a list of terminal tokens) is given, performs a small
    backtracking search to reach exactly that string. Otherwise it
    always expands each nonterminal using its first alternative, which
    gives a simple illustrative derivation (may not terminate for some
    grammars, so it is capped at `max_steps`).

    Returns (steps, reached_target) where `steps` is a list of
    sentential forms (each a list of symbols) and `reached_target` says
    whether the search found the requested target (always True when no
    target was requested and the derivation finished on its own).
    """
    nonterminals = set(grammar)
    start = next(iter(grammar))

    if target is None:
        steps = [[start]]
        current = [start]
        for _ in range(max_steps):
            idx = _nonterminal_index(current, nonterminals, rightmost)
            if idx == -1:
                return steps, True
            nt = current[idx]
            prod = grammar[nt][0]
            replacement = [] if prod == ["ε"] else prod
            current = current[:idx] + replacement + current[idx + 1:]
            steps.append(current[:])
        return steps, (_nonterminal_index(current, nonterminals, rightmost) == -1)

    best = {"steps": None}

    def backtrack(symbols, steps, depth):
        if best["steps"] is not None:
            return True
        if depth > max_steps or len(symbols) > len(target) + max_steps:
            return False

        idx = _nonterminal_index(symbols, nonterminals, rightmost)
        if idx == -1:
            if symbols == target:
                best["steps"] = steps
                return True
            return False

        nt = symbols[idx]
        for prod in grammar.get(nt, []):
            replacement = [] if prod == ["ε"] else prod
            new_symbols = symbols[:idx] + replacement + symbols[idx + 1:]
            if backtrack(new_symbols, steps + [new_symbols], depth + 1):
                return True
        return False

    backtrack([start], [[start]], 0)
    if best["steps"] is not None:
        return best["steps"], True
    return [[start]], False


def format_derivation(grammar, steps, title):
    lines = [title]
    for i, symbols in enumerate(steps):
        rendered = " ".join(symbols) if symbols else "ε"
        lines.append(rendered if i == 0 else f"=> {rendered}")
    return "\n".join(lines)


def remove_left_recursion(grammar_text):
    grammar = parse_grammar(grammar_text)
    result = []

    for A, productions in grammar.items():
        recursive = []
        non_recursive = []

        for p in productions:
            if p and p[0] == A:
                recursive.append(p[1:])
            else:
                non_recursive.append(p)

        if not recursive:
            result.append(f"{A} -> " + " | ".join(" ".join(p) for p in productions))
            continue

        A2 = A + "'"
        if not non_recursive:
            non_recursive = [["x"]]

        result.append(
            f"{A} -> " +
            " | ".join(" ".join(p + [A2]) for p in non_recursive)
        )
        result.append(
            f"{A2} -> " +
            " | ".join(" ".join(p + [A2]) for p in recursive) +
            " | ε"
        )

    return "\n".join(result)


def left_factoring(grammar_text):
    grammar = parse_grammar(grammar_text)
    result = []

    for A, productions in grammar.items():
        if len(productions) < 2:
            result.append(f"{A} -> " + " | ".join(" ".join(p) for p in productions))
            continue

        # Find a common prefix among all alternatives.
        prefix = productions[0][:]
        for p in productions[1:]:
            k = 0
            while k < min(len(prefix), len(p)) and prefix[k] == p[k]:
                k += 1
            prefix = prefix[:k]

        if prefix:
            A2 = A + "'"
            suffixes = []
            for p in productions:
                suffix = p[len(prefix):] or ["ε"]
                suffixes.append(" ".join(suffix))
            result.append(f"{A} -> {' '.join(prefix)} {A2}")
            result.append(f"{A2} -> " + " | ".join(suffixes))
        else:
            result.append(f"{A} -> " + " | ".join(" ".join(p) for p in productions))

    return "\n".join(result)


# ===========================================================================
# ADVANCED COMPILER PIPELINE (formal grammar, AST, scoped semantics, IR, CFG)
# ===========================================================================
# A second, more formal language pipeline layered on top of the lexer above:
# a real recursive-descent parser building an AST, a scope-aware semantic
# analyzer (functions/arrays/return types), a quadruple IR, and a basic
# control-flow-graph + data-flow (liveness) driven optimizer.

# ===========================================================================
# AST
# ===========================================================================

class Node:
    """A generic AST / parse-tree node. `kind` names the construct,
    `value` holds any leaf/meta info, `children` holds nested Nodes."""

    __slots__ = ("kind", "value", "children", "line")

    def __init__(self, kind, value=None, children=None, line=None):
        self.kind = kind
        self.value = value
        self.children = children or []
        self.line = line

    def label(self):
        """A short human-readable label used by the tree printer/viewer."""
        if self.kind in ("Num", "Float", "Bool", "Str", "Char", "Var", "Type"):
            return str(self.value)
        if self.kind == "BinOp":
            return f"BinOp ({self.value})"
        if self.kind == "UnOp":
            return f"UnOp ({self.value})"
        if self.kind == "ArrayAccess":
            return f"ArrayAccess ({self.value})"
        if self.kind == "Call":
            return f"Call ({self.value})"
        if self.kind == "VarDecl":
            t, name, size = self.value
            return f"VarDecl {t} {name}" + (f"[{size}]" if size is not None else "")
        if self.kind == "Assign":
            name, has_index = self.value
            return f"Assign {name}" + ("[..]" if has_index else "")
        if self.kind == "FuncDecl":
            return f"FuncDecl {self.value['return_type']} {self.value['name']}()"
        if self.kind == "Param":
            t, name, is_arr = self.value
            return f"Param {t} {name}" + ("[]" if is_arr else "")
        return self.kind

    def __repr__(self):
        return f"Node({self.label()})"


def ast_to_text(node, indent=0):
    lines = ["  " * indent + node.label()]
    for child in node.children:
        lines.append(ast_to_text(child, indent + 1))
    return "\n".join(lines)


# ===========================================================================
# Token stream helper (built on top of the existing lexical_analysis())
# ===========================================================================

class TokenStream:
    def __init__(self, tokens):
        # tokens: list of (no, line, type, lexeme) from lexical_analysis()
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        i = self.pos + offset
        if i < len(self.tokens):
            return self.tokens[i]
        return None

    def current(self):
        return self.peek(0)

    def at_end(self):
        return self.pos >= len(self.tokens)

    def advance(self):
        tok = self.current()
        self.pos += 1
        return tok

    def check_lexeme(self, *lexemes):
        tok = self.current()
        return tok is not None and tok[3] in lexemes

    def check_type(self, *types):
        tok = self.current()
        return tok is not None and tok[2] in types

    def match_lexeme(self, *lexemes):
        if self.check_lexeme(*lexemes):
            return self.advance()
        return None


TYPE_KEYWORDS = {"int", "float", "bool", "char", "string", "void"}


# ===========================================================================
# Parser
# ===========================================================================

class ParseError(Exception):
    pass


class Parser:
    """Hand-written recursive-descent parser implementing:

        program        := (func_decl | var_decl)*
        func_decl      := type IDENT '(' params? ')' block
        params         := param (',' param)*
        param          := type IDENT ('[' ']')?
        var_decl       := type IDENT ('[' NUMBER ']')? ('=' expr)? ';'
        block          := '{' statement* '}'
        statement      := var_decl | if_stmt | while_stmt | return_stmt
                         | assign_stmt | expr_stmt | block
        if_stmt        := 'if' '(' expr ')' statement ('else' statement)?
        while_stmt     := 'while' '(' expr ')' statement
        return_stmt    := 'return' expr? ';'
        assign_stmt     := IDENT ('[' expr ']')? '=' expr ';'
        expr_stmt      := expr ';'

        expr           := logic_or
        logic_or       := logic_and ('||' logic_and)*
        logic_and      := equality ('&&' equality)*
        equality       := relational (('=='|'!=') relational)*
        relational     := additive (('<'|'<='|'>'|'>=') additive)*
        additive       := term (('+'|'-') term)*
        term           := unary (('*'|'/'|'%') unary)*
        unary          := ('!'|'-') unary | primary
        primary        := NUMBER | STRING | 'true' | 'false'
                         | IDENT ('(' args ')' | '[' expr ']')?
                         | '(' expr ')'
    """

    def __init__(self, tokens):
        self.ts = TokenStream(tokens)
        self.errors = []

    # ---- error handling / recovery ----

    def _line(self):
        tok = self.ts.current()
        return tok[1] if tok else -1

    def error(self, message):
        self.errors.append(f"Line {self._line()}: {message}")

    def expect_lexeme(self, *lexemes):
        tok = self.ts.match_lexeme(*lexemes)
        if tok is None:
            got = self.ts.current()
            got_desc = f"'{got[3]}'" if got else "end of input"
            self.error(f"Expected {' or '.join(repr(l) for l in lexemes)}, found {got_desc}")
            self._resync()
        return tok

    def expect_type(self, type_name, what):
        tok = self.ts.current()
        if tok is None or tok[2] != type_name:
            got_desc = f"'{tok[3]}'" if tok else "end of input"
            self.error(f"Expected {what}, found {got_desc}")
            self._resync()
            return None
        return self.ts.advance()

    def _resync(self):
        """Panic-mode recovery: skip tokens until a statement boundary."""
        while not self.ts.at_end() and not self.ts.check_lexeme(";", "}"):
            self.ts.advance()
        if self.ts.check_lexeme(";"):
            self.ts.advance()

    # ---- entry point ----

    def parse_program(self):
        decls = []
        guard = 0
        while not self.ts.at_end():
            guard += 1
            if guard > 100000:
                self.error("Parser aborted: too many iterations (malformed input).")
                break
            before = self.ts.pos
            decls.append(self.parse_top_level())
            if self.ts.pos == before:
                # Safety net: force progress to avoid infinite loops.
                self.ts.advance()
        return Node("Program", children=[d for d in decls if d is not None])

    def parse_top_level(self):
        if not self.ts.check_type("KEYWORD") or not self.ts.check_lexeme(*TYPE_KEYWORDS):
            self.error(f"Expected a type keyword to start a declaration")
            self._resync()
            return None

        type_tok = self.ts.advance()
        name_tok = self.expect_type("IDENTIFIER", "an identifier")
        if name_tok is None:
            return None

        if self.ts.check_lexeme("("):
            return self.parse_function(type_tok[3], name_tok[3])
        return self.parse_var_decl_rest(type_tok[3], name_tok[3])

    def parse_function(self, return_type, name):
        self.expect_lexeme("(")
        params = []
        if not self.ts.check_lexeme(")"):
            params.append(self.parse_param())
            while self.ts.match_lexeme(","):
                params.append(self.parse_param())
        self.expect_lexeme(")")
        body = self.parse_block()
        return Node(
            "FuncDecl",
            value={
                "name": name,
                "return_type": return_type,
                "params": [p.value for p in params],
            },
            children=[body],
            line=self._line(),
        )

    def parse_param(self):
        if not (self.ts.check_type("KEYWORD") and self.ts.check_lexeme(*TYPE_KEYWORDS)):
            self.error("Expected a parameter type")
            return Node("Param", value=("int", "?", False))
        type_tok = self.ts.advance()
        name_tok = self.expect_type("IDENTIFIER", "a parameter name")
        name = name_tok[3] if name_tok else "?"
        is_array = False
        if self.ts.match_lexeme("["):
            is_array = True
            self.expect_lexeme("]")
        return Node("Param", value=(type_tok[3], name, is_array), line=self._line())

    def parse_var_decl_rest(self, var_type, name):
        size = None
        if self.ts.match_lexeme("["):
            size_tok = self.expect_type("NUMBER", "an array size")
            if size_tok is not None:
                size = int(float(size_tok[3]))
            self.expect_lexeme("]")

        init = None
        if self.ts.match_lexeme("="):
            init = self.parse_expr()

        self.expect_lexeme(";")
        children = [init] if init is not None else []
        return Node("VarDecl", value=(var_type, name, size), children=children, line=self._line())

    def parse_block(self):
        self.expect_lexeme("{")
        stmts = []
        guard = 0
        while not self.ts.at_end() and not self.ts.check_lexeme("}"):
            guard += 1
            if guard > 100000:
                self.error("Parser aborted inside block (malformed input).")
                break
            before = self.ts.pos
            stmts.append(self.parse_statement())
            if self.ts.pos == before:
                self.ts.advance()
        self.expect_lexeme("}")
        return Node("Block", children=[s for s in stmts if s is not None])

    def parse_statement(self):
        tok = self.ts.current()
        if tok is None:
            self.error("Unexpected end of input")
            return None

        if tok[2] == "KEYWORD" and tok[3] in TYPE_KEYWORDS:
            type_tok = self.ts.advance()
            name_tok = self.expect_type("IDENTIFIER", "an identifier")
            if name_tok is None:
                return None
            return self.parse_var_decl_rest(type_tok[3], name_tok[3])

        if tok[3] == "if":
            return self.parse_if()
        if tok[3] == "while":
            return self.parse_while()
        if tok[3] == "return":
            return self.parse_return()
        if tok[3] == "{":
            return self.parse_block()

        if tok[2] == "IDENTIFIER" and self.ts.peek(1) and self.ts.peek(1)[3] in ("=", "["):
            return self.parse_assign()

        return self.parse_expr_stmt()

    def parse_if(self):
        self.expect_lexeme("if")
        self.expect_lexeme("(")
        cond = self.parse_expr()
        self.expect_lexeme(")")
        then_branch = self.parse_statement()
        else_branch = None
        if self.ts.match_lexeme("else"):
            else_branch = self.parse_statement()
        children = [cond, then_branch] + ([else_branch] if else_branch else [])
        return Node("If", children=children, line=self._line())

    def parse_while(self):
        self.expect_lexeme("while")
        self.expect_lexeme("(")
        cond = self.parse_expr()
        self.expect_lexeme(")")
        body = self.parse_statement()
        return Node("While", children=[cond, body], line=self._line())

    def parse_return(self):
        self.expect_lexeme("return")
        expr = None
        if not self.ts.check_lexeme(";"):
            expr = self.parse_expr()
        self.expect_lexeme(";")
        return Node("Return", children=[expr] if expr is not None else [], line=self._line())

    def parse_assign(self):
        name_tok = self.ts.advance()
        index = None
        if self.ts.match_lexeme("["):
            index = self.parse_expr()
            self.expect_lexeme("]")
        self.expect_lexeme("=")
        rhs = self.parse_expr()
        self.expect_lexeme(";")
        children = ([index] if index is not None else []) + [rhs]
        return Node("Assign", value=(name_tok[3], index is not None), children=children, line=self._line())

    def parse_expr_stmt(self):
        expr = self.parse_expr()
        self.expect_lexeme(";")
        return Node("ExprStmt", children=[expr], line=self._line())

    # ---- expressions (precedence climbing) ----

    def parse_expr(self):
        return self.parse_logic_or()

    def _binary_level(self, next_level, ops):
        node = next_level()
        while self.ts.check_lexeme(*ops):
            op_tok = self.ts.advance()
            rhs = next_level()
            node = Node("BinOp", value=op_tok[3], children=[node, rhs], line=op_tok[1])
        return node

    def parse_logic_or(self):
        return self._binary_level(self.parse_logic_and, ("||",))

    def parse_logic_and(self):
        return self._binary_level(self.parse_equality, ("&&",))

    def parse_equality(self):
        return self._binary_level(self.parse_relational, ("==", "!="))

    def parse_relational(self):
        return self._binary_level(self.parse_additive, ("<", "<=", ">", ">="))

    def parse_additive(self):
        return self._binary_level(self.parse_term, ("+", "-"))

    def parse_term(self):
        return self._binary_level(self.parse_unary, ("*", "/", "%"))

    def parse_unary(self):
        if self.ts.check_lexeme("!", "-"):
            op_tok = self.ts.advance()
            operand = self.parse_unary()
            return Node("UnOp", value=op_tok[3], children=[operand], line=op_tok[1])
        return self.parse_primary()

    def parse_primary(self):
        tok = self.ts.current()
        if tok is None:
            self.error("Unexpected end of input in expression")
            return Node("Num", value=0)

        if tok[2] == "NUMBER":
            self.ts.advance()
            if "." in tok[3]:
                return Node("Float", value=float(tok[3]), line=tok[1])
            return Node("Num", value=int(tok[3]), line=tok[1])

        if tok[2] == "STRING":
            self.ts.advance()
            raw = tok[3][1:-1]
            if tok[3].startswith("'") and len(raw) == 1:
                return Node("Char", value=raw, line=tok[1])
            return Node("Str", value=raw, line=tok[1])

        if tok[3] in ("true", "false"):
            self.ts.advance()
            return Node("Bool", value=(tok[3] == "true"), line=tok[1])

        if tok[3] == "(":
            self.ts.advance()
            inner = self.parse_expr()
            self.expect_lexeme(")")
            return inner

        if tok[2] == "IDENTIFIER":
            self.ts.advance()
            if self.ts.match_lexeme("("):
                args = []
                if not self.ts.check_lexeme(")"):
                    args.append(self.parse_expr())
                    while self.ts.match_lexeme(","):
                        args.append(self.parse_expr())
                self.expect_lexeme(")")
                return Node("Call", value=tok[3], children=args, line=tok[1])
            if self.ts.match_lexeme("["):
                idx = self.parse_expr()
                self.expect_lexeme("]")
                return Node("ArrayAccess", value=tok[3], children=[idx], line=tok[1])
            return Node("Var", value=tok[3], line=tok[1])

        self.error(f"Unexpected token '{tok[3]}' in expression")
        self.ts.advance()
        return Node("Num", value=0)


def parse_source(source):
    tokens, lex_errors = lexical_analysis(source)
    parser = Parser(tokens)
    program = parser.parse_program()
    return program, lex_errors, parser.errors


# ===========================================================================
# Semantic Analysis (scoped, functions, arrays, return types)
# ===========================================================================

NUMERIC_TYPES = {"int", "float"}


class SemanticError(Exception):
    pass


class Symbol:
    def __init__(self, name, type_, is_array=False, size=None):
        self.name = name
        self.type = type_
        self.is_array = is_array
        self.size = size

    def __repr__(self):
        arr = f"[{self.size}]" if self.is_array else ""
        return f"{self.type}{arr} {self.name}"


class SemanticAnalyzer:
    """Walks the AST maintaining a stack of lexical scopes. Reports:
       - undeclared / redeclared variables
       - type mismatches in declarations, assignments, and expressions
       - array usage errors (indexing a non-array, non-integer index)
       - function-call errors (unknown function, arg count/type mismatch)
       - return-type mismatches (including missing return in non-void
         functions, checked with a simple, non-path-sensitive scan)
    """

    def __init__(self):
        self.errors = []
        self.scopes = [{}]
        self.functions = {}
        self.current_function = None
        self.symbol_table_log = []  # (scope_depth, name, symbol, line) for display

    # ---- scope helpers ----

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        self.scopes.pop()

    def declare(self, name, symbol, line):
        scope = self.scopes[-1]
        if name in scope:
            self.errors.append(f"Line {line}: Redeclaration of '{name}' in the same scope.")
            return
        scope[name] = symbol
        self.symbol_table_log.append((len(self.scopes) - 1, name, symbol, line))

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    # ---- entry point ----

    def analyze(self, program):
        # First pass: register every function signature so calls
        # (including forward references and recursion) can be checked.
        for decl in program.children:
            if decl.kind == "FuncDecl":
                info = decl.value
                if info["name"] in self.functions:
                    self.errors.append(f"Function '{info['name']}' is already defined.")
                    continue
                self.functions[info["name"]] = info

        for decl in program.children:
            if decl.kind == "FuncDecl":
                self._analyze_function(decl)
            elif decl.kind == "VarDecl":
                self._analyze_var_decl(decl)

        return self.errors, self.symbol_table_log

    # ---- declarations ----

    def _analyze_function(self, node):
        info = node.value
        self.current_function = info
        self.push_scope()

        for (ptype, pname, is_array) in info["params"]:
            self.declare(pname, Symbol(pname, ptype, is_array), node.line)

        block = node.children[0]
        self._has_return = False
        self._analyze_block(block, new_scope=False)

        if info["return_type"] != "void" and not self._contains_return(block):
            self.errors.append(
                f"Function '{info['name']}': non-void function may not return "
                f"a value on all paths (no 'return' statement found)."
            )

        self.pop_scope()
        self.current_function = None

    def _contains_return(self, node):
        """Shallow, non-path-sensitive check: is there a 'return' anywhere
        reachable in this block (including inside if/while bodies)?"""
        if node.kind == "Return":
            return True
        return any(self._contains_return(c) for c in node.children if isinstance(c, Node))

    def _analyze_var_decl(self, node):
        var_type, name, size = node.value
        is_array = size is not None
        self.declare(name, Symbol(name, var_type, is_array, size), node.line)
        if node.children:
            init_type = self._expr_type(node.children[0])
            if not self._compatible(var_type, init_type):
                self.errors.append(
                    f"Line {node.line}: Cannot initialize '{name}' of type "
                    f"'{var_type}' with value of type '{init_type}'."
                )

    # ---- statements ----

    def _analyze_block(self, node, new_scope=True):
        if new_scope:
            self.push_scope()
        for stmt in node.children:
            self._analyze_stmt(stmt)
        if new_scope:
            self.pop_scope()

    def _analyze_stmt(self, node):
        if node.kind == "VarDecl":
            self._analyze_var_decl(node)
        elif node.kind == "Assign":
            self._analyze_assign(node)
        elif node.kind == "If":
            cond_type = self._expr_type(node.children[0])
            if cond_type not in ("bool", "error"):
                self.errors.append(f"Line {node.line}: 'if' condition must be bool, got '{cond_type}'.")
            self._analyze_stmt(node.children[1])
            if len(node.children) > 2:
                self._analyze_stmt(node.children[2])
        elif node.kind == "While":
            cond_type = self._expr_type(node.children[0])
            if cond_type not in ("bool", "error"):
                self.errors.append(f"Line {node.line}: 'while' condition must be bool, got '{cond_type}'.")
            self._analyze_stmt(node.children[1])
        elif node.kind == "Return":
            expected = self.current_function["return_type"] if self.current_function else "void"
            if node.children:
                actual = self._expr_type(node.children[0])
                if expected == "void":
                    self.errors.append(f"Line {node.line}: 'void' function must not return a value.")
                elif not self._compatible(expected, actual):
                    self.errors.append(
                        f"Line {node.line}: Return type mismatch — expected '{expected}', got '{actual}'."
                    )
            else:
                if expected != "void":
                    self.errors.append(f"Line {node.line}: Missing return value of type '{expected}'.")
        elif node.kind == "Block":
            self._analyze_block(node, new_scope=True)
        elif node.kind == "ExprStmt":
            self._expr_type(node.children[0])

    def _analyze_assign(self, node):
        name, has_index = node.value
        sym = self.lookup(name)
        if sym is None:
            self.errors.append(f"Line {node.line}: Assignment to undeclared variable '{name}'.")
            # still type-check the RHS to surface further errors
            self._expr_type(node.children[-1])
            return

        if has_index:
            if not sym.is_array:
                self.errors.append(f"Line {node.line}: '{name}' is not an array.")
            idx_type = self._expr_type(node.children[0])
            if idx_type not in ("int", "error"):
                self.errors.append(f"Line {node.line}: Array index must be int, got '{idx_type}'.")
            rhs_type = self._expr_type(node.children[-1])
            if sym.is_array and not self._compatible(sym.type, rhs_type):
                self.errors.append(
                    f"Line {node.line}: Cannot assign '{rhs_type}' to element of "
                    f"'{sym.type}' array '{name}'."
                )
        else:
            if sym.is_array:
                self.errors.append(f"Line {node.line}: '{name}' is an array; index it to assign an element.")
            rhs_type = self._expr_type(node.children[-1])
            if not self._compatible(sym.type, rhs_type):
                self.errors.append(
                    f"Line {node.line}: Cannot assign '{rhs_type}' to '{name}' of type '{sym.type}'."
                )

    # ---- expressions ----

    def _compatible(self, declared, actual):
        if actual == "error":
            return True
        if declared == actual:
            return True
        if declared == "float" and actual == "int":
            return True
        return False

    def _expr_type(self, node):
        if node is None:
            return "error"

        if node.kind == "Num":
            return "int"
        if node.kind == "Float":
            return "float"
        if node.kind == "Bool":
            return "bool"
        if node.kind == "Str":
            return "string"
        if node.kind == "Char":
            return "char"

        if node.kind == "Var":
            sym = self.lookup(node.value)
            if sym is None:
                self.errors.append(f"Line {node.line}: Use of undeclared variable '{node.value}'.")
                return "error"
            if sym.is_array:
                self.errors.append(f"Line {node.line}: Array '{node.value}' used without an index.")
                return "error"
            return sym.type

        if node.kind == "ArrayAccess":
            sym = self.lookup(node.value)
            idx_type = self._expr_type(node.children[0])
            if idx_type not in ("int", "error"):
                self.errors.append(f"Line {node.line}: Array index must be int, got '{idx_type}'.")
            if sym is None:
                self.errors.append(f"Line {node.line}: Use of undeclared array '{node.value}'.")
                return "error"
            if not sym.is_array:
                self.errors.append(f"Line {node.line}: '{node.value}' is not an array.")
                return "error"
            return sym.type

        if node.kind == "Call":
            if node.value in ("print", "input"):
                for arg in node.children:
                    self._expr_type(arg)
                return "int" if node.value == "input" else "void"

            info = self.functions.get(node.value)
            if info is None:
                self.errors.append(f"Line {node.line}: Call to undefined function '{node.value}'.")
                for arg in node.children:
                    self._expr_type(arg)
                return "error"

            expected_params = info["params"]
            if len(node.children) != len(expected_params):
                self.errors.append(
                    f"Line {node.line}: '{node.value}' expects {len(expected_params)} "
                    f"argument(s), got {len(node.children)}."
                )
            for i, arg in enumerate(node.children):
                arg_type = self._expr_type(arg)
                if i < len(expected_params):
                    ptype = expected_params[i][0]
                    if not self._compatible(ptype, arg_type):
                        self.errors.append(
                            f"Line {node.line}: Argument {i + 1} of '{node.value}' expects "
                            f"'{ptype}', got '{arg_type}'."
                        )
            return info["return_type"]

        if node.kind == "UnOp":
            operand_type = self._expr_type(node.children[0])
            if node.value == "!":
                if operand_type not in ("bool", "error"):
                    self.errors.append(f"Line {node.line}: '!' requires bool, got '{operand_type}'.")
                return "bool"
            if operand_type not in NUMERIC_TYPES and operand_type != "error":
                self.errors.append(f"Line {node.line}: Unary '-' requires a numeric type, got '{operand_type}'.")
            return operand_type

        if node.kind == "BinOp":
            left = self._expr_type(node.children[0])
            right = self._expr_type(node.children[1])
            operator = node.value

            if operator in ("&&", "||"):
                if left not in ("bool", "error") or right not in ("bool", "error"):
                    self.errors.append(
                        f"Line {node.line}: '{operator}' requires bool operands, got "
                        f"'{left}' and '{right}'."
                    )
                return "bool"

            if operator in ("==", "!="):
                if "error" not in (left, right) and left != right and not (
                    left in NUMERIC_TYPES and right in NUMERIC_TYPES
                ):
                    self.errors.append(
                        f"Line {node.line}: Cannot compare '{left}' with '{right}'."
                    )
                return "bool"

            if operator in ("<", "<=", ">", ">="):
                if left not in NUMERIC_TYPES and left != "error":
                    self.errors.append(f"Line {node.line}: '{operator}' requires numeric operands, got '{left}'.")
                if right not in NUMERIC_TYPES and right != "error":
                    self.errors.append(f"Line {node.line}: '{operator}' requires numeric operands, got '{right}'.")
                return "bool"

            if operator == "+" and left == "string" and right == "string":
                return "string"

            if left not in NUMERIC_TYPES and left != "error":
                self.errors.append(f"Line {node.line}: '{operator}' requires numeric operands, got '{left}'.")
                return "error"
            if right not in NUMERIC_TYPES and right != "error":
                self.errors.append(f"Line {node.line}: '{operator}' requires numeric operands, got '{right}'.")
                return "error"
            return "float" if "float" in (left, right) else "int"

        return "error"


# ===========================================================================
# Intermediate Representation: Quadruples
# ===========================================================================

class Lit:
    """Wraps a literal value (string/char/bool) so it can never be
    confused with a variable or temp name of the same text during
    data-flow analysis. Numbers (int/float) don't need this since
    their Python type already distinguishes them from names."""

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'"{self.value}"' if isinstance(self.value, str) else str(self.value)

    def __eq__(self, other):
        return isinstance(other, Lit) and self.value == other.value

    def __hash__(self):
        return hash(("Lit", self.value))


class Quad:
    """One (op, arg1, arg2, result) instruction. Meaning of the fields
    depends on `op` — see format_quad for the full set."""

    __slots__ = ("op", "arg1", "arg2", "result", "line")

    def __init__(self, op, arg1=None, arg2=None, result=None, line=None):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result
        self.line = line

    def __repr__(self):
        return f"({self.op}, {self.arg1}, {self.arg2}, {self.result})"


def format_quad(q):
    if q.op == "label":
        return f"{q.result}:"
    if q.op == "goto":
        return f"    goto {q.result}"
    if q.op == "iffalse":
        return f"    iffalse {q.arg1} goto {q.result}"
    if q.op == "func_begin":
        return f"func {q.result}:"
    if q.op == "func_end":
        return f"end func {q.result}"
    if q.op == "param":
        return f"    param {q.arg1}"
    if q.op == "call":
        if q.result:
            return f"    {q.result} = call {q.arg1}, {q.arg2}"
        return f"    call {q.arg1}, {q.arg2}"
    if q.op == "return":
        return f"    return {q.arg1}" if q.arg1 is not None else "    return"
    if q.op == "=":
        return f"    {q.result} = {q.arg1}"
    if q.op == "=[]":
        return f"    {q.result} = {q.arg1}[{q.arg2}]"
    if q.op == "[]=":
        return f"    {q.arg1}[{q.arg2}] = {q.result}"
    if q.op == "uminus":
        return f"    {q.result} = -{q.arg1}"
    if q.op == "!":
        return f"    {q.result} = !{q.arg1}"
    return f"    {q.result} = {q.arg1} {q.op} {q.arg2}"


class IRGenerator:
    """Generates quadruples for each function via a straightforward
    AST walk. Uses fresh temporaries (t1, t2, ...) and labels
    (L1, L2, ...) for control flow."""

    def __init__(self):
        self.quads = []
        self.temp_count = 0
        self.label_count = 0

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, op, arg1=None, arg2=None, result=None, line=None):
        self.quads.append(Quad(op, arg1, arg2, result, line))

    def generate(self, program):
        for decl in program.children:
            if decl.kind == "FuncDecl":
                self._gen_function(decl)
        return self.quads

    def _gen_function(self, node):
        info = node.value
        self.emit("func_begin", result=info["name"], line=node.line)
        self._gen_stmt(node.children[0])
        self.emit("func_end", result=info["name"], line=node.line)

    def _gen_stmt(self, node):
        if node.kind == "Block":
            for s in node.children:
                self._gen_stmt(s)

        elif node.kind == "VarDecl":
            if node.children:
                val = self._gen_expr(node.children[0])
                self.emit("=", val, result=node.value[1], line=node.line)

        elif node.kind == "Assign":
            name, has_index = node.value
            if has_index:
                idx = self._gen_expr(node.children[0])
                rhs = self._gen_expr(node.children[-1])
                self.emit("[]=", name, idx, rhs, line=node.line)
            else:
                rhs = self._gen_expr(node.children[-1])
                self.emit("=", rhs, result=name, line=node.line)

        elif node.kind == "If":
            cond = self._gen_expr(node.children[0])
            has_else = len(node.children) > 2
            l_else_or_end = self.new_label()
            self.emit("iffalse", cond, result=l_else_or_end, line=node.line)
            self._gen_stmt(node.children[1])
            if has_else:
                l_end = self.new_label()
                self.emit("goto", result=l_end)
                self.emit("label", result=l_else_or_end)
                self._gen_stmt(node.children[2])
                self.emit("label", result=l_end)
            else:
                self.emit("label", result=l_else_or_end)

        elif node.kind == "While":
            l_start = self.new_label()
            l_end = self.new_label()
            self.emit("label", result=l_start)
            cond = self._gen_expr(node.children[0])
            self.emit("iffalse", cond, result=l_end, line=node.line)
            self._gen_stmt(node.children[1])
            self.emit("goto", result=l_start)
            self.emit("label", result=l_end)

        elif node.kind == "Return":
            if node.children:
                val = self._gen_expr(node.children[0])
                self.emit("return", val, line=node.line)
            else:
                self.emit("return", line=node.line)

        elif node.kind == "ExprStmt":
            self._gen_expr(node.children[0])

    def _gen_expr(self, node):
        if node.kind in ("Num", "Float"):
            return node.value
        if node.kind == "Bool":
            return Lit("true" if node.value else "false")
        if node.kind in ("Str", "Char"):
            return Lit(node.value)

        if node.kind == "Var":
            return node.value

        if node.kind == "ArrayAccess":
            idx = self._gen_expr(node.children[0])
            t = self.new_temp()
            self.emit("=[]", node.value, idx, t, line=node.line)
            return t

        if node.kind == "Call":
            arg_vals = [self._gen_expr(a) for a in node.children]
            for v in arg_vals:
                self.emit("param", v, line=node.line)
            t = self.new_temp()
            self.emit("call", node.value, len(arg_vals), t, line=node.line)
            return t

        if node.kind == "UnOp":
            val = self._gen_expr(node.children[0])
            t = self.new_temp()
            self.emit("uminus" if node.value == "-" else "!", val, result=t, line=node.line)
            return t

        if node.kind == "BinOp":
            left = self._gen_expr(node.children[0])
            right = self._gen_expr(node.children[1])
            t = self.new_temp()
            self.emit(node.value, left, right, t, line=node.line)
            return t

        return "0"


def generate_ir(program):
    return IRGenerator().generate(program)


# ===========================================================================
# Control-Flow Graph + Data-Flow Optimization
# ===========================================================================

ARITH_OPS = {"+", "-", "*", "/", "%"}


def is_var(token):
    """A quad operand is a variable/temp reference iff it's a plain
    Python str — literals are int/float/Lit after IR generation."""
    return isinstance(token, str)


def quad_uses_defs(q):
    """Returns (uses, defs): the variable/temp names read and written
    by this quad, respectively."""
    uses, defs = [], []

    def use(x):
        if is_var(x):
            uses.append(x)

    if q.op in ("label", "func_begin", "func_end", "goto"):
        pass
    elif q.op == "iffalse":
        use(q.arg1)
    elif q.op == "param":
        use(q.arg1)
    elif q.op == "return":
        use(q.arg1)
    elif q.op == "call":
        if q.result:
            defs.append(q.result)
    elif q.op == "=":
        use(q.arg1)
        defs.append(q.result)
    elif q.op == "=[]":
        use(q.arg1)
        use(q.arg2)
        defs.append(q.result)
    elif q.op == "[]=":
        use(q.arg1)
        use(q.arg2)
        use(q.result)
    elif q.op in ("uminus", "!"):
        use(q.arg1)
        defs.append(q.result)
    else:
        use(q.arg1)
        use(q.arg2)
        defs.append(q.result)

    return uses, defs


class BasicBlock:
    def __init__(self, id_):
        self.id = id_
        self.quads = []  # list of (original_index, Quad)
        self.succ = []
        self.pred = []
        self.use = set()
        self.def_ = set()
        self.live_in = set()
        self.live_out = set()

    def label(self):
        if self.quads and self.quads[0][1].op == "label":
            return self.quads[0][1].result
        return f"B{self.id}"


def build_basic_blocks(quads):
    """Splits a straight-line list of quads (one function's body) into
    basic blocks and wires up successor/predecessor edges."""
    if not quads:
        return []

    leaders = {0}
    for i, q in enumerate(quads):
        if q.op == "label":
            leaders.add(i)
        if q.op in ("goto", "iffalse", "return") and i + 1 < len(quads):
            leaders.add(i + 1)

    leader_list = sorted(leaders)
    blocks = []
    for idx, start in enumerate(leader_list):
        end = leader_list[idx + 1] if idx + 1 < len(leader_list) else len(quads)
        b = BasicBlock(idx)
        b.quads = [(i, quads[i]) for i in range(start, end)]
        blocks.append(b)

    label_to_block = {}
    for b in blocks:
        if b.quads and b.quads[0][1].op == "label":
            label_to_block[b.quads[0][1].result] = b

    for idx, b in enumerate(blocks):
        if not b.quads:
            continue
        _, last_q = b.quads[-1]
        if last_q.op == "goto":
            target = label_to_block.get(last_q.result)
            if target:
                b.succ.append(target)
        elif last_q.op == "iffalse":
            target = label_to_block.get(last_q.result)
            if target:
                b.succ.append(target)
            if idx + 1 < len(blocks):
                b.succ.append(blocks[idx + 1])
        elif last_q.op == "return":
            pass
        else:
            if idx + 1 < len(blocks):
                b.succ.append(blocks[idx + 1])

    for b in blocks:
        for s in b.succ:
            s.pred.append(b)

    return blocks


def compute_use_def(block):
    defined_so_far = set()
    use, def_ = set(), set()
    for _, q in block.quads:
        u, d = quad_uses_defs(q)
        for x in u:
            if x not in defined_so_far:
                use.add(x)
        for x in d:
            defined_so_far.add(x)
            def_.add(x)
    block.use, block.def_ = use, def_


def compute_liveness(blocks, max_iterations=200):
    """Classic iterative backward liveness analysis, correct in the
    presence of loops (back-edges) via fixed-point iteration:
        OUT[B] = union of IN[S] for successors S
        IN[B]  = USE[B] U (OUT[B] - DEF[B])
    """
    changed = True
    iterations = 0
    while changed and iterations < max_iterations:
        changed = False
        iterations += 1
        for b in reversed(blocks):
            new_out = set()
            for s in b.succ:
                new_out |= s.live_in
            new_in = b.use | (new_out - b.def_)
            if new_out != b.live_out or new_in != b.live_in:
                b.live_out = new_out
                b.live_in = new_in
                changed = True


def eliminate_dead_code(blocks):
    """Removes quads whose defined variable is never live afterwards,
    using each block's data-flow-computed live_out as the boundary
    condition. Calls are kept even if their result is unused (they may
    have side effects); everything else is a genuine candidate."""
    removed = set()
    for b in blocks:
        live = set(b.live_out)
        for i, q in reversed(b.quads):
            uses, defs = quad_uses_defs(q)
            if defs:
                d = defs[0]
                if d not in live and q.op != "call":
                    removed.add(i)
                    continue
                live.discard(d)
            for u in uses:
                live.add(u)
    return removed


def constant_fold_ir(quads):
    """Folds quads whose two operands are both compile-time literals,
    e.g. 't1 = 2 + 3' becomes 't1 = 5'."""
    folded = []
    changed = False
    for q in quads:
        if (q.op in ARITH_OPS and isinstance(q.arg1, (int, float))
                and isinstance(q.arg2, (int, float))):
            try:
                if q.op == "+":
                    val = q.arg1 + q.arg2
                elif q.op == "-":
                    val = q.arg1 - q.arg2
                elif q.op == "*":
                    val = q.arg1 * q.arg2
                elif q.op == "/":
                    val = q.arg1 / q.arg2 if q.arg2 != 0 else q.arg1
                else:
                    val = q.arg1 % q.arg2 if q.arg2 != 0 else 0
                folded.append(Quad("=", val, result=q.result, line=q.line))
                changed = True
                continue
            except ZeroDivisionError:
                pass
        folded.append(q)
    return folded, changed


def optimize_ir(quads):
    """Runs constant folding to a fixed point, then builds a CFG per
    function and removes quads that data-flow analysis proves dead.
    Returns (optimized_quads, stats) where stats describes what
    changed, for a readable optimization report."""
    working = list(quads)
    folded_total = 0
    for _ in range(10):
        working, changed = constant_fold_ir(working)
        if not changed:
            break
        folded_total += 1

    ranges = []
    start = None
    for i, q in enumerate(working):
        if q.op == "func_begin":
            start = i + 1
        elif q.op == "func_end" and start is not None:
            ranges.append((start, i))
            start = None

    removed = set()
    block_reports = []
    for (s, e) in ranges:
        body = working[s:e]
        blocks = build_basic_blocks(body)
        for b in blocks:
            compute_use_def(b)
        compute_liveness(blocks)
        dead_local = eliminate_dead_code(blocks)
        for local_i in dead_local:
            removed.add(s + local_i)
        block_reports.append(blocks)

    optimized = [q for i, q in enumerate(working) if i not in removed]
    stats = {
        "folded_passes": folded_total,
        "removed_count": len(removed),
        "block_reports": block_reports,
    }
    return optimized, stats


# ===========================================================================
# Parse-tree construction (for the graphical LMD/RMD & Ambiguity viewer)
# ===========================================================================

class TreeNode:
    __slots__ = ("name", "children")

    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []


class _SearchBudgetExceeded(Exception):
    pass


def build_parse_tree(grammar, symbol, target, budget=None):
    """Backtracking search for a concrete parse tree of `symbol` that
    derives exactly the terminal sequence `target` (a list of tokens).
    `budget` is a single-item list used as a mutable call counter so
    the search can bail out on pathological grammars/strings. Tracks
    in-progress (symbol, target) pairs to avoid infinite recursion on
    left-recursive grammars trying to match against an empty slice."""
    if budget is None:
        budget = [20000]
    in_progress = set()

    def go(sym, toks):
        budget[0] -= 1
        if budget[0] <= 0:
            raise _SearchBudgetExceeded()

        if sym not in grammar:
            if len(toks) == 1 and toks[0] == sym:
                return TreeNode(sym, [])
            return None

        key = (sym, tuple(toks))
        if key in in_progress:
            return None
        in_progress.add(key)
        try:
            for prod in grammar[sym]:
                node = _match_production(go, sym, prod, toks)
                if node is not None:
                    return node
            return None
        finally:
            in_progress.discard(key)

    try:
        return go(symbol, target)
    except _SearchBudgetExceeded:
        return None


def _match_production(go, symbol, prod, target):
    seq = [] if prod == ["ε"] else prod
    if not seq:
        return TreeNode(symbol, [TreeNode("ε", [])]) if not target else None

    def helper(i, remaining):
        if i == len(seq) - 1:
            child = go(seq[i], remaining)
            return [child] if child is not None else None
        for split in range(len(remaining) + 1):
            child = go(seq[i], remaining[:split])
            if child is None:
                continue
            tail = helper(i + 1, remaining[split:])
            if tail is not None:
                return [child] + tail
        return None

    children = helper(0, target)
    if children is None:
        return None
    return TreeNode(symbol, children)


def all_parse_trees(grammar, symbol, target, limit=2, budget=None):
    """Finds up to `limit` *structurally distinct* parse trees for the
    same target string — used to visually demonstrate ambiguity."""
    if budget is None:
        budget = [50000]
    seen_shapes = set()
    found = []

    def shape(node):
        if not node.children:
            return node.name
        return node.name + "(" + ",".join(shape(c) for c in node.children) + ")"

    def go(sym, toks, in_progress):
        budget[0] -= 1
        if budget[0] <= 0:
            raise _SearchBudgetExceeded()

        if sym not in grammar:
            if len(toks) == 1 and toks[0] == sym:
                return [TreeNode(sym, [])]
            return []

        key = (sym, tuple(toks))
        if key in in_progress:
            return []
        next_in_progress = in_progress | {key}

        results = []
        for prod in grammar[sym]:
            results.extend(match_production(sym, prod, toks, next_in_progress))
        return results

    def match_production(sym, prod, target_, in_progress):
        seq = [] if prod == ["ε"] else prod
        if not seq:
            return [TreeNode(sym, [TreeNode("ε", [])])] if not target_ else []

        def helper(i, remaining):
            if i == len(seq) - 1:
                return [[c] for c in go(seq[i], remaining, in_progress)]
            combos = []
            for split in range(len(remaining) + 1):
                left_opts = go(seq[i], remaining[:split], in_progress)
                if not left_opts:
                    continue
                for tail in helper(i + 1, remaining[split:]):
                    for lo in left_opts:
                        combos.append([lo] + tail)
            return combos

        return [TreeNode(sym, combo) for combo in helper(0, target_)]

    try:
        all_trees = go(symbol, target, frozenset())
    except _SearchBudgetExceeded:
        all_trees = []

    for tree in all_trees:
        s = shape(tree)
        if s not in seen_shapes:
            seen_shapes.add(s)
            found.append(tree)
        if len(found) >= limit:
            break

    return found


def layout_tree(root, x_gap=60, y_gap=90):
    """Assigns (x, y) pixel positions to every node of a TreeNode/Node
    tree via a simple two-pass layout: leaves get sequential x slots,
    internal nodes are centered above their children. Returns
    (positions, edges, width, height) where positions maps id(node)
    to (x, y) and edges is a list of (id(parent), id(child)).
    """
    positions = {}
    edges = []
    next_x = [0]

    def get_children(node):
        return node.children

    def get_label(node):
        return node.name if hasattr(node, "name") else node.label()

    def assign(node, depth):
        children = get_children(node)
        if not children:
            x = next_x[0]
            next_x[0] += 1
            positions[id(node)] = [x * x_gap, depth * y_gap, get_label(node)]
            return x * x_gap
        xs = []
        for c in children:
            cx = assign(c, depth + 1)
            xs.append(cx)
            edges.append((id(node), id(c)))
        x = sum(xs) / len(xs)
        positions[id(node)] = [x, depth * y_gap, get_label(node)]
        return x

    assign(root, 0)

    max_x = max((p[0] for p in positions.values()), default=0)
    max_y = max((p[1] for p in positions.values()), default=0)
    return positions, edges, max_x + x_gap, max_y + y_gap


# ----------------------------- Main Application -----------------------------

class CompilerLabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1300x860")
        self.minsize(1050, 650)

        self.configure(bg="#0f172a")
        self._last_trees = None
        self._current_file_path = None

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure("TFrame", background="#0f172a")
        self.style.configure("Card.TFrame", background="#111827")
        self.style.configure("TLabel", background="#0f172a", foreground="#e5e7eb",
                             font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background="#0f172a", foreground="#f8fafc",
                             font=("Segoe UI", 23, "bold"))
        self.style.configure("Sub.TLabel", background="#0f172a", foreground="#94a3b8",
                             font=("Segoe UI", 10))
        self.style.configure("CardTitle.TLabel", background="#111827", foreground="#f8fafc",
                             font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8))
        self.style.configure("Accent.TButton", background="#2563eb", foreground="white")
        self.style.map("Accent.TButton", background=[("active", "#1d4ed8")])

        self.build_ui()
        self.load_example()

    def build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=24, pady=(20, 10))

        ttk.Label(header, text="Compiler Construction Lab", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Interactive Compiler Phase & Optimization Analyzer",
            style="Sub.TLabel"
        ).pack(anchor="w", pady=(3, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        sidebar_outer = ttk.Frame(body, style="Card.TFrame", width=270)
        sidebar_outer.pack(side="left", fill="y", padx=(0, 12))
        sidebar_outer.pack_propagate(False)

        # Sidebar now holds a lot of operations (basic + advanced pipeline),
        # so it scrolls instead of clipping content on smaller screens.
        sidebar_canvas = tk.Canvas(sidebar_outer, bg="#111827", highlightthickness=0, bd=0)
        sidebar_scroll = ttk.Scrollbar(sidebar_outer, orient="vertical", command=sidebar_canvas.yview)
        sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        sidebar_canvas.pack(side="left", fill="both", expand=True)
        sidebar_scroll.pack(side="right", fill="y")

        sidebar = ttk.Frame(sidebar_canvas, style="Card.TFrame")
        sidebar_window = sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw")

        def _on_sidebar_configure(event):
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
            sidebar_canvas.itemconfigure(sidebar_window, width=event.width)

        sidebar.bind("<Configure>", lambda e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")))
        sidebar_canvas.bind("<Configure>", _on_sidebar_configure)

        def _on_sidebar_mousewheel(event):
            delta = -1 if event.num == 5 or event.delta < 0 else 1
            sidebar_canvas.yview_scroll(-delta, "units")

        sidebar_canvas.bind_all("<MouseWheel>", _on_sidebar_mousewheel, add="+")
        sidebar_canvas.bind_all("<Button-4>", _on_sidebar_mousewheel, add="+")
        sidebar_canvas.bind_all("<Button-5>", _on_sidebar_mousewheel, add="+")

        ttk.Label(sidebar, text="BASIC / EDUCATIONAL", style="CardTitle.TLabel").pack(
            anchor="w", padx=18, pady=(18, 8)
        )

        self.operation = tk.StringVar(value="Lexical Analysis")
        basic_operations = [
            "Lexical Analysis",
            "Syntax Analysis",
            "Semantic Analysis",
            "Intermediate Code",
            "Code Optimization",
            "CFG / FIRST / FOLLOW",
            "LL(1) Parsing Table",
            "LMD / RMD",
            "Ambiguity",
            "Left Recursion Removal",
            "Left Factoring",
            "Full Compiler Pipeline"
        ]

        advanced_operations = [
            "AST / Parse Tree",
            "Semantic Analysis (Scoped)",
            "LL(1) Driven Parse",
            "IR - Quadruples",
            "Optimized IR (Data-Flow)",
            "Full Advanced Pipeline",
        ]

        def make_button(parent, op_name):
            btn = tk.Button(
                parent,
                text=op_name,
                anchor="w",
                relief="flat",
                bd=0,
                bg="#111827",
                fg="#cbd5e1",
                activebackground="#1e3a8a",
                activeforeground="white",
                font=("Segoe UI", 9, "bold"),
                padx=18,
                pady=7,
                wraplength=210,
                justify="left",
                command=lambda x=op_name: self.select_operation(x)
            )
            btn.pack(fill="x", padx=8, pady=1)
            return btn

        self.buttons = []
        for op_name in basic_operations:
            self.buttons.append((op_name, make_button(sidebar, op_name)))

        ttk.Separator(sidebar).pack(fill="x", padx=15, pady=10)
        ttk.Label(sidebar, text="ADVANCED PIPELINE", style="CardTitle.TLabel").pack(
            anchor="w", padx=18, pady=(2, 8)
        )
        for op_name in advanced_operations:
            self.buttons.append((op_name, make_button(sidebar, op_name)))

        ttk.Separator(sidebar).pack(fill="x", padx=15, pady=12)

        ttk.Button(sidebar, text="Run Selected", style="Accent.TButton",
                   command=self.run_selected).pack(fill="x", padx=18, pady=5)
        ttk.Button(sidebar, text="View Parse Tree", command=self.open_parse_tree_viewer).pack(
            fill="x", padx=18, pady=5
        )
        ttk.Button(sidebar, text="Load Example", command=self.load_example).pack(
            fill="x", padx=18, pady=5
        )
        ttk.Button(sidebar, text="Clear", command=self.clear_all).pack(
            fill="x", padx=18, pady=5
        )

        ttk.Separator(sidebar).pack(fill="x", padx=15, pady=12)
        ttk.Label(sidebar, text="FILE", style="CardTitle.TLabel").pack(
            anchor="w", padx=18, pady=(2, 8)
        )
        ttk.Button(sidebar, text="Open Source File...", command=self.open_source_file).pack(
            fill="x", padx=18, pady=5
        )
        ttk.Button(sidebar, text="Save Source As...", command=self.save_source_file).pack(
            fill="x", padx=18, pady=5
        )
        ttk.Button(sidebar, text="Export Report...", command=self.export_report).pack(
            fill="x", padx=18, pady=(5, 18)
        )

        main = ttk.Frame(body)
        main.pack(side="left", fill="both", expand=True)

        # Vertical paned window so Input/Output can be resized by dragging
        # the divider — the same way panels resize in VS Code. Output also
        # gets a larger default share, and a proper scrollbar, so results
        # are no longer cramped into a tiny box.
        paned = ttk.PanedWindow(main, orient="vertical")
        paned.pack(fill="both", expand=True)

        input_card = ttk.Frame(paned, style="Card.TFrame")
        output_card = ttk.Frame(paned, style="Card.TFrame")
        paned.add(input_card, weight=2)
        paned.add(output_card, weight=3)

        top = ttk.Frame(input_card, style="Card.TFrame")
        top.pack(fill="x", padx=15, pady=(12, 5))
        ttk.Label(top, text="Input / Source Code", style="CardTitle.TLabel").pack(side="left")

        self.status = tk.StringVar(value="Ready")
        ttk.Label(top, textvariable=self.status, background="#111827",
                  foreground="#60a5fa", font=("Segoe UI", 9, "bold")).pack(side="right")

        editor_frame = ttk.Frame(input_card, style="Card.TFrame")
        editor_frame.pack(fill="both", expand=True, padx=15, pady=5)
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(1, weight=1)

        self.input_box = tk.Text(
            editor_frame, wrap="none", undo=True,
            bg="#020617", fg="#dbeafe", insertbackground="white",
            selectbackground="#1d4ed8", font=("Consolas", 11), padx=12, pady=10,
            relief="flat"
        )
        self.input_box.grid(row=0, column=1, sticky="nsew")

        input_yscroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.input_box.yview)
        input_yscroll.grid(row=0, column=2, sticky="ns")
        input_xscroll = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.input_box.xview)
        input_xscroll.grid(row=1, column=1, sticky="ew")

        def _on_input_yscroll(*args):
            input_yscroll.set(*args)
            if hasattr(self, "line_numbers"):
                self.line_numbers.yview_moveto(args[0])

        self.input_box.configure(yscrollcommand=_on_input_yscroll, xscrollcommand=input_xscroll.set)

        # Line-number gutter (left column) kept in sync with scrolling/edits,
        # plus keyword/number/string/comment syntax highlighting.
        self._setup_line_numbers(editor_frame)
        self._setup_syntax_highlighting()

        out_top = ttk.Frame(output_card, style="Card.TFrame")
        out_top.pack(fill="x", padx=15, pady=(12, 5))
        ttk.Label(out_top, text="Compiler Output", style="CardTitle.TLabel").pack(side="left")

        output_frame = ttk.Frame(output_card, style="Card.TFrame")
        output_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)

        self.output_box = tk.Text(
            output_frame, wrap="none", bg="#020617", fg="#a7f3d0",
            insertbackground="white", font=("Consolas", 10), padx=12, pady=10,
            relief="flat"
        )
        self.output_box.grid(row=0, column=0, sticky="nsew")

        output_yscroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_box.yview)
        output_yscroll.grid(row=0, column=1, sticky="ns")
        output_xscroll = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output_box.xview)
        output_xscroll.grid(row=1, column=0, sticky="ew")
        self.output_box.configure(yscrollcommand=output_yscroll.set, xscrollcommand=output_xscroll.set)

        self.select_operation(self.operation.get())

        # Give Output more room than Input right from the start (drag the
        # divider any time to change this — just like a VS Code split).
        self.after(50, lambda: self._set_initial_sash(paned))

    def _set_initial_sash(self, paned):
        try:
            total = paned.winfo_height()
            if total > 1:
                paned.sashpos(0, int(total * 0.36))
        except tk.TclError:
            pass

    def select_operation(self, name):
        self.operation.set(name)
        for op_name, btn in self.buttons:
            if op_name == name:
                btn.configure(bg="#1d4ed8", fg="white")
            else:
                btn.configure(bg="#111827", fg="#cbd5e1")
        self.status.set(f"Selected: {name}")

    def load_example(self):
        example = """int a = 10 + 5;
int b = a;
int c = b * 2;
int unused = 99;
int result = c + 0;
result = result + 0;
"""
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", example)
        self.status.set("Example loaded")
        self.output_box.delete("1.0", "end")
        self._last_trees = None
        self._current_file_path = None
        if hasattr(self, "line_numbers"):
            self._highlight_syntax()
            self.input_box.event_generate("<KeyRelease>")

    def clear_all(self):
        self.input_box.delete("1.0", "end")
        self.output_box.delete("1.0", "end")
        self.status.set("Cleared")
        self._last_trees = None
        self._current_file_path = None
        if hasattr(self, "line_numbers"):
            self.input_box.event_generate("<KeyRelease>")

    def get_input(self):
        return self.input_box.get("1.0", "end-1c")

    def write_output(self, text):
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", text)
        self.status.set("Execution completed")

    # ------------------------- Parse-tree viewer -------------------------

    def open_parse_tree_viewer(self):
        trees = getattr(self, "_last_trees", None)
        if not trees:
            messagebox.showinfo(
                "No Tree Available",
                "Run 'AST / Parse Tree', 'LMD / RMD', or 'Ambiguity' first "
                "(with a target string for Ambiguity), then click "
                "'View Parse Tree'."
            )
            return

        win = tk.Toplevel(self)
        win.title("Parse Tree Viewer")
        win.geometry("950x650")
        win.configure(bg="#0f172a")

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        for title, root_node in trees:
            tab = ttk.Frame(notebook, style="Card.TFrame")
            notebook.add(tab, text=title)

            canvas_frame = ttk.Frame(tab, style="Card.TFrame")
            canvas_frame.pack(fill="both", expand=True)
            canvas_frame.rowconfigure(0, weight=1)
            canvas_frame.columnconfigure(0, weight=1)

            canvas = tk.Canvas(canvas_frame, bg="#020617", highlightthickness=0)
            yscroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            xscroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
            canvas.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            yscroll.grid(row=0, column=1, sticky="ns")
            xscroll.grid(row=1, column=0, sticky="ew")

            self._draw_tree_on_canvas(canvas, root_node)

    def _draw_tree_on_canvas(self, canvas, root_node):
        positions, edges, width, height = layout_tree(root_node, x_gap=90, y_gap=90)
        pad = 60

        for pid, cid in edges:
            px, py, _ = positions[pid]
            cx, cy, _ = positions[cid]
            canvas.create_line(
                px + pad, py + pad + 14, cx + pad, cy + pad - 14,
                fill="#334155", width=2
            )

        for _, (x, y, label) in positions.items():
            x += pad
            y += pad
            box_w = max(40, 9 * len(label) + 20)
            canvas.create_rectangle(
                x - box_w / 2, y - 14, x + box_w / 2, y + 14,
                fill="#1e293b", outline="#3b82f6", width=1.5
            )
            canvas.create_text(
                x, y, text=label, fill="#e2e8f0", font=("Consolas", 10, "bold")
            )

        canvas.configure(scrollregion=(0, 0, width + pad * 2, height + pad * 2))

    # ------------------------- File actions -------------------------

    def open_source_file(self):
        path = filedialog.askopenfilename(
            title="Open Source File",
            filetypes=[("Source / Text files", "*.txt *.src *.c *.cpp *.mini *.*"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            messagebox.showerror("Open Failed", str(e))
            return

        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", content)
        self._current_file_path = path
        self.status.set(f"Opened: {path.split('/')[-1]}")
        self._highlight_syntax()

    def save_source_file(self):
        path = filedialog.asksaveasfilename(
            title="Save Source As",
            defaultextension=".txt",
            initialfile=(self._current_file_path.split("/")[-1] if self._current_file_path else "source.txt"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.get_input())
        except OSError as e:
            messagebox.showerror("Save Failed", str(e))
            return

        self._current_file_path = path
        self.status.set(f"Saved: {path.split('/')[-1]}")

    def export_report(self):
        output_text = self.output_box.get("1.0", "end-1c")
        if not output_text.strip():
            messagebox.showinfo("Nothing to Export", "Run an operation first so there's a report to export.")
            return

        path = filedialog.asksaveasfilename(
            title="Export Report",
            defaultextension=".txt",
            initialfile="compiler_lab_report.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        header = (
            f"COMPILER CONSTRUCTION LAB — REPORT\n"
            f"Operation: {self.operation.get()}\n"
            f"{'=' * 75}\n\n"
            f"SOURCE / GRAMMAR INPUT\n{'-' * 75}\n{self.get_input()}\n\n"
            f"OUTPUT\n{'-' * 75}\n"
        )
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + output_text + "\n")
        except OSError as e:
            messagebox.showerror("Export Failed", str(e))
            return

        self.status.set(f"Report exported: {path.split('/')[-1]}")
        messagebox.showinfo("Export Complete", f"Report saved to:\n{path}")

    # ------------------------- Syntax highlighting -------------------------

    def _setup_syntax_highlighting(self):
        self.input_box.tag_configure("kw", foreground="#c084fc")
        self.input_box.tag_configure("type_kw", foreground="#60a5fa")
        self.input_box.tag_configure("num", foreground="#fbbf24")
        self.input_box.tag_configure("str_lit", foreground="#34d399")
        self.input_box.tag_configure("comment", foreground="#64748b")
        self.input_box.tag_configure("op", foreground="#f472b6")

        self.input_box.bind("<KeyRelease>", lambda e: self._highlight_syntax())
        self._highlight_syntax()

    def _highlight_syntax(self):
        text = self.input_box.get("1.0", "end-1c")
        for tag in ("kw", "type_kw", "num", "str_lit", "comment", "op"):
            self.input_box.tag_remove(tag, "1.0", "end")

        control_kw = {"if", "else", "while", "for", "return"}
        type_kw = {"int", "float", "char", "string", "bool", "void", "true", "false"}

        def add_tag(tag, start, end):
            self.input_box.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")

        for m in re.finditer(r"//[^\n]*", text):
            add_tag("comment", m.start(), m.end())
        for m in re.finditer(r'"[^"\n]*"|\'[^\'\n]*\'', text):
            add_tag("str_lit", m.start(), m.end())
        for m in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
            add_tag("num", m.start(), m.end())
        for m in re.finditer(r"\b[A-Za-z_]\w*\b", text):
            word = m.group(0)
            if word in control_kw:
                add_tag("kw", m.start(), m.end())
            elif word in type_kw:
                add_tag("type_kw", m.start(), m.end())
        for m in re.finditer(r"==|!=|<=|>=|&&|\|\||[+\-*/%=<>!]", text):
            add_tag("op", m.start(), m.end())

    # ------------------------- Line numbers -------------------------

    def _setup_line_numbers(self, editor_frame):
        self.line_numbers = tk.Text(
            editor_frame, width=4, padx=6, pady=10, relief="flat",
            bg="#0b1220", fg="#475569", font=("Consolas", 11),
            state="disabled", takefocus=0, wrap="none"
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        def redraw_line_numbers(*_args):
            line_count = int(self.input_box.index("end-1c").split(".")[0])
            content = "\n".join(str(i) for i in range(1, line_count + 1))
            self.line_numbers.configure(state="normal")
            self.line_numbers.delete("1.0", "end")
            self.line_numbers.insert("1.0", content)
            self.line_numbers.configure(state="disabled")
            self.line_numbers.yview_moveto(self.input_box.yview()[0])

        def on_input_scroll(*args):
            self.line_numbers.yview_moveto(args[0])

        self.input_box.bind("<KeyRelease>", lambda e: (redraw_line_numbers(), self._highlight_syntax()), add="+")
        self.input_box.bind("<<Modified>>", lambda e: redraw_line_numbers(), add="+")
        self.input_box.bind("<MouseWheel>", lambda e: self.after(1, redraw_line_numbers), add="+")
        self.input_box.bind("<Configure>", lambda e: redraw_line_numbers(), add="+")
        redraw_line_numbers()
        return redraw_line_numbers

    def run_selected(self):
        source = self.get_input()
        selected = self.operation.get()

        if selected in {
            "CFG / FIRST / FOLLOW", "LL(1) Parsing Table",
            "LMD / RMD", "Ambiguity", "Left Recursion Removal", "Left Factoring",
            "LL(1) Driven Parse"
        }:
            grammar_text = source.strip()
            if not grammar_text:
                grammar_text = "E -> E + T | T\nT -> id"
        else:
            if not source.strip():
                messagebox.showwarning("No Input", "Please enter source code first.")
                return

        if selected == "Lexical Analysis":
            tokens, errors = lexical_analysis(source)
            lines = ["TOKEN TABLE", "=" * 72,
                     f"{'No.':<6}{'Line':<7}{'Type':<18}Lexeme",
                     "-" * 72]
            for no, line, typ, lexeme in tokens:
                lines.append(f"{no:<6}{line:<7}{typ:<18}{lexeme}")
            if errors:
                lines += ["", "LEXICAL ERRORS", "-" * 40] + errors
            else:
                lines += ["", "Result: Lexical analysis completed successfully."]
            self.write_output("\n".join(lines))

        elif selected == "Syntax Analysis":
            ok, report = syntax_analysis(source)
            self.write_output(
                "SYNTAX ANALYSIS REPORT\n" + "=" * 55 + "\n" +
                "\n".join(report) +
                f"\n\nStatus: {'PASS' if ok else 'FAIL'}"
            )

        elif selected == "Semantic Analysis":
            symbols, errors = semantic_analysis(source)
            lines = ["SEMANTIC ANALYSIS / SYMBOL TABLE", "=" * 65,
                     f"{'Identifier':<18}{'Type':<12}{'Scope':<12}Line",
                     "-" * 65]
            for name, typ, scope, line in symbols:
                lines.append(f"{name:<18}{typ:<12}{scope:<12}{line}")
            lines += ["", "SEMANTIC CHECK"]
            if errors:
                lines += ["FAIL"] + errors
            else:
                lines.append("PASS — No basic semantic errors found.")
            self.write_output("\n".join(lines))

        elif selected == "Intermediate Code":
            tac = generate_three_address(source)
            self.write_output(
                "THREE ADDRESS CODE\n" + "=" * 55 + "\n" +
                ("\n".join(tac) if tac else "No arithmetic assignments detected.")
            )

        elif selected == "Code Optimization":
            optimized = source
            sections = []

            transformations = [
                ("1. CONSTANT FOLDING", constant_folding),
                ("2. COPY PROPAGATION", copy_propagation),
                ("3. DEAD CODE ELIMINATION", dead_code_elimination),
                ("4. COMMON SUBEXPRESSION ELIMINATION", common_subexpression_elimination),
                ("5. AVOID UNNECESSARY CALCULATIONS", avoid_unnecessary_calculation),
            ]

            for title, func in transformations:
                before = optimized
                optimized = func(optimized)
                sections.append(
                    f"{title}\n{'-' * 55}\n"
                    f"Before:\n{before}\n\nAfter:\n{optimized}\n"
                )

            self.write_output("\n".join(sections))

        elif selected in ("CFG / FIRST / FOLLOW", "LL(1) Parsing Table"):
            grammar = parse_grammar(grammar_text)
            if not grammar:
                self.write_output("Invalid grammar.\nUse format: E -> E + T | T")
                return

            first = first_sets(grammar)
            follow = follow_sets(grammar, first)

            lines = ["GRAMMAR", "=" * 55]
            for A, prods in grammar.items():
                lines.append(f"{A} -> " + " | ".join(" ".join(p) for p in prods))

            lines += ["", "FIRST SETS", "-" * 55]
            for A, values in first.items():
                lines.append(f"FIRST({A}) = {{ {', '.join(sorted(values))} }}")

            lines += ["", "FOLLOW SETS", "-" * 55]
            for A, values in follow.items():
                lines.append(f"FOLLOW({A}) = {{ {', '.join(sorted(values))} }}")

            if selected == "LL(1) Parsing Table":
                table, conflicts = parsing_table(grammar, first, follow)
                lines += ["", "LL(1) PARSING TABLE", "-" * 55]
                for (A, terminal), production in sorted(table.items()):
                    lines.append(f"M[{A}, {terminal}] = {production}")
                lines += ["", "LL(1) CHECK", "-" * 55]
                if conflicts:
                    lines.append("FAIL — Grammar has parsing-table conflicts.")
                    lines.extend(conflicts)
                else:
                    lines.append("PASS — No parsing-table conflicts found.")

            self.write_output("\n".join(lines))

        elif selected == "LMD / RMD":
            target, cleaned_grammar_text = extract_target_string(grammar_text)
            grammar = parse_grammar(cleaned_grammar_text)
            self._last_trees = None

            if not grammar:
                self.write_output(left_derivation_example() + "\n" + right_derivation_example())
            else:
                # Preserve the classic id + id demo when the box was left
                # on the default fallback grammar (nothing typed by the user).
                if target is None and cleaned_grammar_text.strip() == "E -> E + T | T\nT -> id":
                    target = ["id", "+", "id"]

                lines = ["GRAMMAR", "=" * 55]
                for A, prods in grammar.items():
                    lines.append(f"{A} -> " + " | ".join(" ".join(p) for p in prods))
                lines.append("")

                if target:
                    lines.append(f"Input: {' '.join(target)}")
                else:
                    lines.append(
                        "Input: (none given — add a line like 'Input: id + id' "
                        "to target a specific string; showing each "
                        "nonterminal's first alternative instead)"
                    )
                lines.append("")

                lmd_steps, lmd_ok = derive_sentence(grammar, rightmost=False, target=target)
                lines.append(format_derivation(grammar, lmd_steps, "Left Most Derivation:"))
                if target is not None and not lmd_ok:
                    lines.append("(Could not reach that exact string within the step limit.)")
                lines.append("")

                rmd_steps, rmd_ok = derive_sentence(grammar, rightmost=True, target=target)
                lines.append(format_derivation(grammar, rmd_steps, "Right Most Derivation:"))
                if target is not None and not rmd_ok:
                    lines.append("(Could not reach that exact string within the step limit.)")

                # Build a concrete parse tree for the graphical viewer,
                # using the explicit target or the auto-derived string.
                tree_target = target if (target is not None and lmd_ok) else (
                    lmd_steps[-1] if lmd_steps and set(lmd_steps[-1]) <= set(
                        t for prods in grammar.values() for p in prods for t in p if t not in grammar
                    ) else None
                )
                if tree_target:
                    tree = build_parse_tree(grammar, next(iter(grammar)), tree_target)
                    if tree:
                        self._last_trees = [("Parse Tree", tree)]
                        lines.append("")
                        lines.append("(Click 'View Parse Tree' in the sidebar to see this visually.)")

                self.write_output("\n".join(lines))

        elif selected == "Ambiguity":
            target, cleaned_grammar_text = extract_target_string(grammar_text)
            grammar = parse_grammar(cleaned_grammar_text)
            self._last_trees = None

            using_default = cleaned_grammar_text.strip() == "E -> E + T | T\nT -> id"
            if not grammar or using_default:
                # Fall back to the classic textbook ambiguity example, but
                # still build real trees for the graphical viewer.
                grammar = parse_grammar("E -> E + E | E * E | id")
                target = ["id", "+", "id", "*", "id"]
                self.write_output(ambiguity_demo())
            else:
                if target is None:
                    self.write_output(
                        "AMBIGUITY CHECK\n" + "=" * 55 + "\n\n"
                        "Grammar:\n" +
                        "\n".join(f"{A} -> " + " | ".join(" ".join(p) for p in prods)
                                  for A, prods in grammar.items()) +
                        "\n\nAdd a line like 'String: id + id * id' to test a "
                        "specific input string for ambiguity (two distinct parse "
                        "trees for the same string means the grammar is ambiguous)."
                    )
                    return

                lines = [
                    "AMBIGUITY CHECK", "=" * 55, "",
                    "Grammar:",
                ] + [f"{A} -> " + " | ".join(" ".join(p) for p in prods)
                     for A, prods in grammar.items()] + [
                    "", f"String: {' '.join(target)}", ""
                ]

                trees = all_parse_trees(grammar, next(iter(grammar)), target, limit=2)
                if len(trees) >= 2:
                    lines.append(
                        "Result: AMBIGUOUS — found more than one distinct parse "
                        "tree for this exact string. Click 'View Parse Tree' to "
                        "compare them visually."
                    )
                    self._last_trees = [("Tree 1", trees[0]), ("Tree 2", trees[1])]
                elif len(trees) == 1:
                    lines.append(
                        "Result: only one derivation was found for this string "
                        "within the search limits — no ambiguity demonstrated "
                        "for this particular input (the grammar could still be "
                        "ambiguous for a different string)."
                    )
                    self._last_trees = [("Parse Tree", trees[0])]
                else:
                    lines.append(
                        "Result: no derivation found for this string with this "
                        "grammar — check the grammar and the target string."
                    )
                self.write_output("\n".join(lines))
                return

            trees = all_parse_trees(grammar, next(iter(grammar)), target, limit=2)
            if len(trees) >= 2:
                self._last_trees = [("Tree 1", trees[0]), ("Tree 2", trees[1])]

        elif selected == "Left Recursion Removal":
            self.write_output(
                "LEFT RECURSION REMOVAL\n" + "=" * 55 + "\n\n" +
                "Input Grammar:\n" + grammar_text +
                "\n\nTransformed Grammar:\n" + remove_left_recursion(grammar_text)
            )

        elif selected == "Left Factoring":
            self.write_output(
                "LEFT FACTORING\n" + "=" * 55 + "\n\n" +
                "Input Grammar:\n" + grammar_text +
                "\n\nFactored Grammar:\n" + left_factoring(grammar_text)
            )

        elif selected == "LL(1) Driven Parse":
            target, cleaned_grammar_text = extract_target_string(grammar_text)
            if target is None and cleaned_grammar_text.strip() == "E -> E + T | T\nT -> id":
                target = ["id", "+", "id"]

            grammar = parse_grammar(cleaned_grammar_text)
            if not grammar:
                self.write_output("Invalid grammar.\nUse format: E -> E + T | T")
                return

            lines = ["LL(1) TABLE-DRIVEN PARSE", "=" * 55, ""]

            # A table-driven LL(1) parser cannot handle left recursion (it
            # would push the same nonterminal back onto the stack forever),
            # so left recursion is removed first — same as a real compiler
            # front-end would require before generating an LL(1) parser.
            had_left_recursion = grammar_text.strip() != remove_left_recursion(cleaned_grammar_text).strip()
            working_text = remove_left_recursion(cleaned_grammar_text)
            working_grammar = parse_grammar(working_text)

            if had_left_recursion:
                lines.append("Note: input grammar was left-recursive, so left")
                lines.append("recursion was removed first (a real LL(1) parser")
                lines.append("cannot process left recursion):")
                lines.append("")
                lines.append(working_text)
                lines.append("")

            first = first_sets(working_grammar)
            follow = follow_sets(working_grammar, first)
            table, conflicts = parsing_table(working_grammar, first, follow)

            if conflicts:
                lines.append("LL(1) CHECK: FAIL — grammar has parsing-table conflicts:")
                lines.extend(conflicts)
                self.write_output("\n".join(lines))
                return

            if not target:
                lines.append(
                    "No input string given — add a line like 'Input: id + id' "
                    "to drive the parser."
                )
                self.write_output("\n".join(lines))
                return

            lines.append(f"Input: {' '.join(target)}")
            lines.append("")
            lines.append(f"{'Stack':<28}{'Input':<20}Action")
            lines.append("-" * 70)

            steps, accepted = ll1_parse_trace(working_grammar, table, target)
            for stack_str, input_str, action in steps:
                lines.append(f"{stack_str:<28}{input_str:<20}{action}")

            lines.append("")
            lines.append("PARSE RESULT: " + ("ACCEPTED" if accepted else "REJECTED"))
            self.write_output("\n".join(lines))

        elif selected == "AST / Parse Tree":
            program, lex_errors, parse_errors = parse_source(source)
            lines = ["ABSTRACT SYNTAX TREE", "=" * 55]
            if lex_errors:
                lines += ["", "LEXICAL ERRORS", "-" * 40] + lex_errors
            if parse_errors:
                lines += ["", "PARSE ERRORS", "-" * 40] + parse_errors
            lines += ["", ast_to_text(program)]
            self._last_trees = [("AST", program)]
            lines.append("")
            lines.append("(Click 'View Parse Tree' in the sidebar to see this visually.)")
            self.write_output("\n".join(lines))

        elif selected == "Semantic Analysis (Scoped)":
            program, lex_errors, parse_errors = parse_source(source)
            lines = ["SCOPED SEMANTIC ANALYSIS", "=" * 65]
            if lex_errors or parse_errors:
                lines += ["", "Cannot run semantic analysis — fix these first:"]
                lines += [f"  {e}" for e in (lex_errors + parse_errors)]
                self.write_output("\n".join(lines))
                return

            sem = SemanticAnalyzer()
            errors, symtab = sem.analyze(program)

            lines += ["", f"{'Scope':<7}{'Identifier':<16}{'Type':<10}Line", "-" * 65]
            for depth, name, sym, line in symtab:
                lines.append(f"{depth:<7}{name:<16}{str(sym.type) + ('[]' if sym.is_array else ''):<10}{line}")

            lines += ["", "FUNCTIONS", "-" * 65]
            for name, info in sem.functions.items():
                params = ", ".join(f"{t}{'[]' if a else ''} {n}" for t, n, a in info["params"])
                lines.append(f"{info['return_type']} {name}({params})")

            lines += ["", "SEMANTIC CHECK", "-" * 65]
            if errors:
                lines.append("FAIL")
                lines.extend(errors)
            else:
                lines.append("PASS — no type, scope, array, or return-type errors found.")

            self.write_output("\n".join(lines))

        elif selected == "IR - Quadruples":
            program, lex_errors, parse_errors = parse_source(source)
            if lex_errors or parse_errors:
                self.write_output(
                    "Cannot generate IR — fix lexical/parse errors first:\n" +
                    "\n".join(lex_errors + parse_errors)
                )
                return

            quads = generate_ir(program)
            lines = ["THREE-ADDRESS QUADRUPLES", "=" * 65,
                     f"{'#':<5}{'op':<10}{'arg1':<12}{'arg2':<12}result", "-" * 65]
            for i, q in enumerate(quads, 1):
                lines.append(f"{i:<5}{str(q.op):<10}{str(q.arg1):<12}{str(q.arg2):<12}{q.result}")
            lines += ["", "READABLE FORM", "-" * 65]
            lines += [format_quad(q) for q in quads]
            self.write_output("\n".join(lines))

        elif selected == "Optimized IR (Data-Flow)":
            program, lex_errors, parse_errors = parse_source(source)
            if lex_errors or parse_errors:
                self.write_output(
                    "Cannot optimize IR — fix lexical/parse errors first:\n" +
                    "\n".join(lex_errors + parse_errors)
                )
                return

            quads = generate_ir(program)
            optimized, stats = optimize_ir(quads)

            lines = ["DATA-FLOW OPTIMIZED IR", "=" * 65, "",
                     "BEFORE", "-" * 65]
            lines += [format_quad(q) for q in quads]
            lines += ["", "AFTER", "-" * 65]
            lines += [format_quad(q) for q in optimized]
            lines += [
                "", "SUMMARY", "-" * 65,
                f"Constant-folding passes applied: {stats['folded_passes']}",
                f"Instructions removed by liveness-based dead-code elimination: "
                f"{stats['removed_count']}",
                f"Total instructions: {len(quads)} -> {len(optimized)}",
            ]
            self.write_output("\n".join(lines))

        elif selected == "Full Advanced Pipeline":
            program, lex_errors, parse_errors = parse_source(source)
            report = ["FULL ADVANCED COMPILER PIPELINE", "=" * 75,
                      "1. LEXICAL + SYNTAX ANALYSIS (recursive-descent parser)", "-" * 75]

            if lex_errors:
                report += ["Lexical errors:"] + lex_errors
            if parse_errors:
                report += ["Parse errors:"] + parse_errors
            if not lex_errors and not parse_errors:
                report.append("PASS — program parsed into an AST with no errors.")

            if lex_errors or parse_errors:
                report += ["", "Stopping here — fix the above errors to continue the pipeline."]
                self.write_output("\n".join(report))
                return

            self._last_trees = [("AST", program)]
            report += ["", "2. ABSTRACT SYNTAX TREE", "-" * 75, ast_to_text(program)]

            sem = SemanticAnalyzer()
            sem_errors, symtab = sem.analyze(program)
            report += ["", "3. SCOPED SEMANTIC ANALYSIS", "-" * 75,
                       f"Symbols: {len(symtab)}   Functions: {len(sem.functions)}   Errors: {len(sem_errors)}"]
            if sem_errors:
                report += ["FAIL"] + sem_errors
            else:
                report.append("PASS — no type, scope, array, or return-type errors found.")

            quads = generate_ir(program)
            report += ["", "4. INTERMEDIATE CODE (QUADRUPLES)", "-" * 75]
            report += [format_quad(q) for q in quads]

            optimized, stats = optimize_ir(quads)
            report += ["", "5. CONTROL-FLOW / DATA-FLOW OPTIMIZATION", "-" * 75,
                       f"Folding passes: {stats['folded_passes']}   "
                       f"Dead instructions removed: {stats['removed_count']}   "
                       f"({len(quads)} -> {len(optimized)} instructions)", ""]
            report += [format_quad(q) for q in optimized]

            report += [
                "", "FINAL STATUS", "-" * 75,
                "PASS" if not sem_errors else "CHECK ERRORS",
                "", "(Click 'View Parse Tree' in the sidebar to see the AST visually.)"
            ]
            self.write_output("\n".join(report))

        elif selected == "Full Compiler Pipeline":
            tokens, lex_errors = lexical_analysis(source)
            syn_ok, syn_report = syntax_analysis(source)
            symbols, sem_errors = semantic_analysis(source)
            tac = generate_three_address(source)

            optimized = constant_folding(source)
            optimized = copy_propagation(optimized)
            optimized = dead_code_elimination(optimized)
            optimized = common_subexpression_elimination(optimized)
            optimized = avoid_unnecessary_calculation(optimized)

            report = [
                "FULL COMPILER PIPELINE",
                "=" * 75,
                "1. LEXICAL ANALYSIS",
                "-" * 75,
                f"Tokens generated: {len(tokens)}",
                f"Errors: {len(lex_errors)}",
                "",
                "2. SYNTAX ANALYSIS",
                "-" * 75,
                "\n".join(syn_report),
                "",
                "3. SEMANTIC ANALYSIS",
                "-" * 75,
                f"Symbols found: {len(symbols)}",
                f"Errors: {len(sem_errors)}",
                "",
                "4. INTERMEDIATE CODE",
                "-" * 75,
                "\n".join(tac) if tac else "No TAC generated.",
                "",
                "5. CODE OPTIMIZATION",
                "-" * 75,
                optimized,
                "",
                "6. CODE GENERATION",
                "-" * 75,
                "Target-style instructions generated from optimized assignments:",
            ]

            for line in optimized.splitlines():
                m = re.match(
                    r"\s*(?:(?:int|float|char|string|bool)\s+)?(\w+)\s*=\s*(.+?);?\s*$",
                    line
                )
                if m:
                    lhs, rhs = m.groups()
                    report.append(f"LOAD R1, {rhs}")
                    report.append(f"STORE {lhs}, R1")

            report += [
                "",
                "FINAL STATUS",
                "-" * 75,
                "PASS" if not lex_errors and syn_ok and not sem_errors else "CHECK ERRORS"
            ]

            self.write_output("\n".join(report))


if __name__ == "__main__":
    app = CompilerLabApp()
    app.mainloop()