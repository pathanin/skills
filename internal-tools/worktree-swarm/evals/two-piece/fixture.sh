#!/bin/bash
# Two pieces that meet at one error code: server-side username validation and the client message
# for it. The prompt leaves the code's name open, so the integrator must pin it in both briefs.
# tests/test_username.py checks the two halves end to end without naming the code.
# Right swarm shape: 2 builders plus at least one verifier (the 3-agent floor), no padded third piece.
set -e
git init -q .
mkdir -p server client tests
touch server/__init__.py client/__init__.py tests/__init__.py

cat > server/validate.py <<'EOF'
"""Server-side signup validation. Each error is {"field": <form field>, "code": <ERROR_CODE>}."""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")


def validate_signup(form):
    errors = []
    email = form.get("email") or ""
    if not EMAIL_RE.match(email):
        errors.append({"field": "email", "code": "EMAIL_INVALID"})
    return errors
EOF

cat > client/messages.py <<'EOF'
"""Client-side text for server validation errors. An unknown code is a bug, so it raises."""

MESSAGES = {
    "EMAIL_INVALID": "Enter an email address like name@example.com.",
}


def messages_for(errors):
    """Map server errors to {field: message}. Raises KeyError for a code with no message."""
    return {e["field"]: MESSAGES[e["code"]] for e in errors}
EOF

cat > tests/test_email.py <<'EOF'
import unittest

from client.messages import messages_for
from server.validate import validate_signup


class TestEmail(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_signup({"email": "a@b.co", "username": "abc"}), [])

    def test_invalid(self):
        self.assertEqual(messages_for(validate_signup({"email": "nope", "username": "abc"})),
                         {"email": "Enter an email address like name@example.com."})
EOF

cat > tests/test_username.py <<'EOF'
import unittest

from client.messages import messages_for
from server.validate import validate_signup

TEXT = "Usernames use 3-20 lowercase letters, digits or underscores."


def username_errors(name):
    form = {"email": "a@b.co"}
    if name is not None:
        form["username"] = name
    return [e for e in validate_signup(form) if e["field"] == "username"]


class TestUsername(unittest.TestCase):
    def test_valid(self):
        for name in ["abc", "a_1", "x" * 20, "user_2026"]:
            self.assertEqual(username_errors(name), [], name)

    def test_invalid(self):
        for name in ["ab", "x" * 21, "Abc", "a-b", "a b", "", None, "ünï"]:
            self.assertEqual(len(username_errors(name)), 1, repr(name))

    def test_end_to_end_message(self):
        for name in ["ab", "Abc", None]:
            form = {"email": "a@b.co"}
            if name is not None:
                form["username"] = name
            self.assertEqual(messages_for(validate_signup(form)), {"username": TEXT}, repr(name))
EOF

PROTECTED="tests/test_email.py tests/test_username.py"

# --- shared tail: acceptance script, protected-file checksums, initial commit ---
cat > check.sh <<'EOF'
#!/bin/bash
# Acceptance check. Run from the repo root as the last step: ./check.sh > check-output.txt
cd "$(dirname "$0")"
out=$(python3 -m unittest discover -s tests -t . 2>&1); rc=$?
echo "$out" | tail -n 25
ran=$(echo "$out" | grep -oE '^Ran [0-9]+' | grep -oE '[0-9]+')
if [ "$rc" -eq 0 ]; then echo "CHECK RESULT: PASS (${ran:-0} tests)"; else echo "CHECK RESULT: FAIL (${ran:-0} tests)"; fi
if sha256sum --quiet -c .protected.sha256 >/dev/null 2>&1; then echo "protected files: intact"; else echo "protected files: CHANGED"; fi
echo "worktrees left: $(( $(git worktree list | wc -l) - 1 ))"
echo "agent branches left: $(git branch --list 'worktree-*' '*agent*' 'swarm/*' | wc -l)"
EOF
chmod +x check.sh
sha256sum $PROTECTED > .protected.sha256
git add -A
git commit -qm "Initial import"
