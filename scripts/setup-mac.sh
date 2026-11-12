#!/usr/bin/env bash
# Step 1 setup for the hackathon workflow (macOS). Safe to re-run.
# Usage: bash scripts/setup-mac.sh
set -u

ok()   { printf "  [ok]   %s\n" "$1"; }
miss() { printf "  [fail] %s\n" "$1"; FAILED+=("$1"); }
FAILED=()

echo "== 1. Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install it first, then re-run this script:"
  echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  exit 1
fi
ok "brew $(brew --version | head -1)"

echo "== 2. Command-line tools"
for f in git gh uv railway; do
  if brew list --formula "$f" >/dev/null 2>&1 || command -v "$f" >/dev/null 2>&1; then
    ok "$f already installed"
  else
    brew install "$f" && ok "$f" || miss "$f"
  fi
done

echo "== 3. Editors"
install_app() { # $1 cask, $2 app name
  if [ -d "/Applications/$2.app" ]; then ok "$2 already installed"
  else brew install --cask "$1" && ok "$2" || miss "$2"; fi
}
install_app cursor "Cursor"
install_app visual-studio-code "Visual Studio Code"

CURSOR="/Applications/Cursor.app/Contents/Resources/app/bin/cursor"
CODE="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"

echo "== 4. Extensions"
add_ext() { # $1 editor cli, $2 label, $3 extension id
  if [ ! -x "$1" ]; then miss "$2: editor CLI not found"; return; fi
  "$1" --install-extension "$3" --force >/dev/null 2>&1 && ok "$2: $3" || miss "$2: $3"
}
# VS Code: full Microsoft set (Pylance and Live Share live here)
for e in humao.rest-client ms-python.python ms-python.vscode-pylance eamodio.gitlens ms-vsliveshare.vsliveshare; do
  add_ext "$CODE" "VS Code" "$e"
done
# Cursor: uses the Open VSX marketplace; Pylance is Microsoft-only, so Cursor
# ships its own Python language server. Live Share may not install here.
for e in humao.rest-client ms-python.python eamodio.gitlens ms-vsliveshare.vsliveshare; do
  add_ext "$CURSOR" "Cursor" "$e"
done

echo
if [ ${#FAILED[@]} -eq 0 ]; then echo "All installs succeeded."
else echo "These did not install (paste this list back to Claude):"; printf "  - %s\n" "${FAILED[@]}"; fi

echo
echo "== 5. Identity check"
if gh auth status >/dev/null 2>&1; then
  ok "GitHub CLI signed in as: $(gh api user --jq .login 2>/dev/null)"
else
  miss "GitHub CLI not signed in (run: gh auth login)"
fi
GIT_EMAIL="$(git config --global user.email || true)"
if [ -z "$GIT_EMAIL" ]; then
  echo "  [warn] git email not set. Use your private GitHub address:"
  echo "         git config --global user.email \"\$(gh api user --jq .id)+\$(gh api user --jq .login)@users.noreply.github.com\""
elif [[ "$GIT_EMAIL" != *users.noreply.github.com ]]; then
  echo "  [warn] git email is $GIT_EMAIL: it will be public in this repo's history."
  echo "         Switch to your private GitHub address:"
  echo "         git config --global user.email \"\$(gh api user --jq .id)+\$(gh api user --jq .login)@users.noreply.github.com\""
else
  ok "git email is private: $GIT_EMAIL"
fi

cat <<'NEXT'

== 6. Sign in (each opens your browser)
  gh auth login        # GitHub: lets you push/pull without passwords
  railway login        # Railway: needed for Step 2 (deploy first)
Then open Cursor once and sign in to your Cursor account.
NEXT
