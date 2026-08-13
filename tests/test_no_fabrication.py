"""
Build-failing guard against re-introducing fabricated outputs.

This test exists because every literal it bans was, at some point, served to a user as a
measurement. It greps the source tree rather than exercising behaviour, deliberately: the
failure mode being prevented is a plausible-looking constant appearing in a code path, and
that is a property of the text.

Comments and docstrings are exempt. Several modules document precisely which fabricated
value they replaced, and that documentation is worth keeping.
"""

import io
import os
import re
import tokenize

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCANNED_DIRS = ("src", "scripts")

# Literals that only ever appeared as fabricated business facts in this repository.
BANNED_LITERALS = [
    ("0.3812", "fabricated LightGBM backtest RMSLE"),
    ("0.2150", "fabricated LSTM backtest RMSLE"),
    ("0.42393", "fabricated pooled RMSLE from the unverified evaluation report"),
    ("145.0", "fabricated school-supplies surge percentage"),
    ("2480.0", "fabricated 16-day forecast sum"),
    ("2674850", "fabricated national demand volume"),
    ("16526470", "fabricated national gross revenue"),
    ("4703580", "fabricated national return profit"),
]

# Randomness is legitimate in seeding and regularisation, and nowhere else in a training,
# forecasting, or serving path.
RANDOM_CALL_RE = re.compile(r'\bnp\.random\.|\bnumpy\.random\.')
RANDOM_ALLOWED_RE = re.compile(r'seed|RandomState|default_rng|dropout', re.IGNORECASE)


def _python_files():
    for scanned in SCANNED_DIRS:
        root = os.path.join(REPO_ROOT, scanned)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def _code_lines(path):
    """
    Yields (lineno, source_text) for executable code only.

    Comments and string literals are blanked out of the ORIGINAL source lines rather than
    reassembled from tokens. Reassembly is what an earlier version of this guard did, and
    joining tokens with spaces turned `np.random.uniform` into `np . random . uniform`,
    so the randomness check silently matched nothing — a guard that could not fail.

    Blanking preserves spacing exactly, so patterns spanning attribute access still match.
    String literals are blanked too: none of the banned values are legitimate string
    content, and prose is not where they caused harm.
    """
    with io.open(path, encoding="utf-8") as handle:
        source_lines = handle.readlines()

    with io.open(path, encoding="utf-8") as handle:
        try:
            tokens = list(tokenize.generate_tokens(handle.readline))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            # An unparseable file cannot be cleared by this guard.
            pytest.fail(f"Could not tokenize {os.path.relpath(path, REPO_ROOT)}")

    # Mutable copy, 1-indexed to match token line numbers.
    blanked = [""] + [line.rstrip("\n") for line in source_lines]

    for tok in tokens:
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        (start_row, start_col), (end_row, end_col) = tok.start, tok.end
        if start_row == end_row:
            line = blanked[start_row]
            blanked[start_row] = line[:start_col] + " " * (end_col - start_col) + line[end_col:]
        else:
            blanked[start_row] = blanked[start_row][:start_col]
            for row in range(start_row + 1, end_row):
                blanked[row] = ""
            blanked[end_row] = " " * end_col + blanked[end_row][end_col:]

    for lineno, line in enumerate(blanked):
        if lineno == 0 or not line.strip():
            continue
        yield lineno, line


@pytest.mark.parametrize("literal,description", BANNED_LITERALS)
def test_banned_literal_absent_from_code(literal, description):
    """A fabricated constant must not reappear in executable code."""
    offenders = []
    for path in _python_files():
        for lineno, line in _code_lines(path):
            if literal in line:
                rel = os.path.relpath(path, REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        f"Banned literal {literal!r} ({description}) found in executable code:\n"
        + "\n".join(offenders)
    )


def test_no_random_outside_seeds_and_dropout():
    """Randomness must not appear in a training, forecasting, or serving path."""
    offenders = []
    for path in _python_files():
        for lineno, line in _code_lines(path):
            if RANDOM_CALL_RE.search(line) and not RANDOM_ALLOWED_RE.search(line):
                rel = os.path.relpath(path, REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "np.random used outside seeding/dropout. Model outputs must be computed, "
        "not sampled:\n" + "\n".join(offenders)
    )


def test_evaluation_artifacts_are_not_resurrected_unverified():
    """
    `artifacts/evaluation/` is reserved for Phase 4 output.

    The quarantined originals must stay quarantined, and the quarantine notice must stay
    with them.
    """
    quarantine = os.path.join(REPO_ROOT, "artifacts", "evaluation_UNVERIFIED")
    assert os.path.isdir(quarantine), "The unverified artifacts must remain quarantined."
    assert os.path.exists(os.path.join(quarantine, "README.md")), (
        "The quarantine directory must carry its README explaining why it is untrustworthy."
    )

    report = os.path.join(quarantine, "EVALUATION_REPORT.md")
    if os.path.exists(report):
        text = io.open(report, encoding="utf-8").read()
        # The gate table itself must be gone. The report may still *describe* what was
        # deleted and why -- that is the audit trail, not a resurrected claim.
        assert "Release Gate Decision - DELETED" in text or "DELETED" in text, (
            "The quarantined report must record that its release-gate table was removed."
        )
        assert "| **Pooled Overall RMSLE** |" not in text, (
            "The release-gate metric table must not survive in the quarantined report."
        )
        assert "> **GO / NO-GO DECISION**" not in text, (
            "The GO/NO-GO verdict line must not survive in the quarantined report."
        )
