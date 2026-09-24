#!/bin/sh
# Linux / macOS : installe rustup s'il manque, puis joue les tests.
# La version du compilateur n'est pas choisie ici : rust-toolchain.toml l'impose, et rustup la télécharge au besoin.
set -eu

if ! command -v rustup >/dev/null 2>&1 && [ -f "$HOME/.cargo/env" ]; then
    . "$HOME/.cargo/env"
fi

if ! command -v rustup >/dev/null 2>&1; then
    echo "rustup absent : installation depuis https://sh.rustup.rs"
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
    . "$HOME/.cargo/env"
fi

cd "$(dirname "$0")"
rustup show active-toolchain
cargo test
