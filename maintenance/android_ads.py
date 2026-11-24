"""Convert the public (ads AND NOT exceptions) predicate into Xray domain matchers."""
import re
from collections import defaultdict
from itertools import chain

from greenery import parse



def parents(host):
    labels = host.split(".")
    return [".".join(labels[i:]) for i in range(len(labels))]


def literal(name):
    if not re.fullmatch(r"[a-z0-9_.-]+", name):
        raise ValueError(f"Unsupported exception name {name!r}")
    return name.replace(".", r"\.")


def forward_expression(fsm):
    """Eliminate states from the reversed DFA, joining small branches first."""
    start, end = object(), object()
    edges = {}

    def add(a, b, expr):
        old = edges.get((a, b))
        if old is None:
            edges[a, b] = expr
        elif old != expr:
            edges[a, b] = "(?:" + old + "|" + expr + ")"

    states = {state for state in fsm.states if fsm.islive(state)}
    for state in sorted(states):
        if state in fsm.finals:
            add(start, state, "")
        symbols = {}
        for symbol, target in fsm.map[state].items():
            if target in states:
                symbols[target] = symbols[target] | symbol if target in symbols else symbol
        for target, symbol in sorted(symbols.items()):
            add(target, state, str(symbol))
    add(fsm.initial, end, "")
    while states:
        def cost(state):
            inc = [len(v) + 1 for (a, b), v in edges.items() if b == state and a != state]
            out = [len(v) + 1 for (a, b), v in edges.items() if a == state and b != state]
            return (sum(inc) * len(out) + sum(out) * len(inc)
                    + len(inc) * len(out) * len(edges.get((state, state), "")), state)
        state = min(states, key=cost)
        states.remove(state)
        incoming = [(a, v) for (a, b), v in edges.items() if b == state and a != state]
        outgoing = [(b, v) for (a, b), v in edges.items() if a == state and b != state]
        loop = edges.pop((state, state), "")
        repeated = "(?:" + loop + ")*" if loop else ""
        for a, left in incoming:
            for b, right in outgoing:
                add(a, b, left + repeated + right)
        for a, _ in incoming:
            del edges[a, state]
        for b, _ in outgoing:
            del edges[state, b]
    return edges[start, end]


def effective_ads(ads, exceptions):
    if set(ads) - {"domain_set", "domain_suffix_set"} or set(exceptions) - {
        "domain_set", "domain_suffix_set", "domain_regex_set"
    }:
        raise ValueError("Unsupported advertising matcher")

    block_suffix = set(ads["domain_suffix_set"])
    allowed_full = set(exceptions.get("domain_set", []))
    allowed_suffix = set(exceptions.get("domain_suffix_set", []))
    globs = []
    below = defaultdict(list)
    overlapping = defaultdict(list)
    suffix_prefix = r"(.*\.)?"
    for name, is_suffix in chain(((x, False) for x in sorted(allowed_full)),
                                 ((x, True) for x in sorted(allowed_suffix))):
        for base in parents(name):
            if base in block_suffix:
                below[base].append((name, is_suffix))

    for pattern in exceptions.get("domain_regex_set", []):
        # The source compiler translates ad-filter globs to this anchored syntax.
        # Reject new syntax until its literal suffix can be indexed without loss.
        lead = r"(?:^|\.)"
        body = pattern[len(lead):-1].replace(r"\-", "-")
        if not pattern.startswith(lead) or not pattern.endswith("$") or not re.fullmatch(
            r"(?:[a-z0-9-]|\\\.|\.\*)+", body
        ):
            raise ValueError(f"Unsupported exception expression {pattern}")
        tail = body.rsplit(".*", 1)[-1]
        if not tail.startswith(r"\."):
            raise ValueError(f"Missing fixed suffix in {pattern}")
        anchor = tail[2:].replace(r"\.", ".")
        reverse = parse(suffix_prefix + body).reversed().to_fsm()
        globs.append((anchor, re.compile(pattern), reverse))
        for base in parents(anchor):
            if base in block_suffix:
                overlapping[base].append(reverse)

    by_anchor = {anchor: [] for anchor, _, _ in globs}
    for anchor, _, reverse in globs:
        by_anchor[anchor].append(reverse)

    def allowed(name):
        return (name in allowed_full or not allowed_suffix.isdisjoint(parents(name))
                or any(rx.search(name) for _, rx, _ in globs))

    for name in sorted(ads["domain_set"]):
        if not allowed(name) and block_suffix.isdisjoint(parents(name)):
            yield 3, name

    nonempty = parse(".+").to_fsm()
    for base in sorted(block_suffix):
        ancestry = parents(base)
        if not block_suffix.isdisjoint(ancestry[1:]) or not allowed_suffix.isdisjoint(ancestry):
            continue
        wildcard = list(overlapping[base]) if base in overlapping else []
        for parent in ancestry[1:]:
            wildcard.extend(by_anchor.get(parent, ()))
        if base not in below and not wildcard:
            yield 2, base
            continue

        # For subdomains P.base, consume ".base" from the right. Subtract
        # exceptions on P only, then append the fixed suffix to the RE2 result.
        if not allowed(base):
            yield 3, base
        holes = []
        for name, is_suffix in below.get(base, ()):
            if name != base:
                pre = literal(name[:-(1 + len(base))])
                holes.append(parse((suffix_prefix if is_suffix else "") + pre).reversed().to_fsm())
        holes.extend(fsm.derive(("." + base)[::-1]) for fsm in wildcard)
        holes = [fsm for fsm in holes if not fsm.empty()]
        if not holes:
            yield 1, r"^.+\." + literal(base) + "$"
            continue
        accepted = nonempty.difference(holes[0].union(*holes[1:])).reduce()
        if not accepted.empty():
            expression = forward_expression(accepted)
            yield 1, "^(" + expression + r")\." + literal(base) + "$"
