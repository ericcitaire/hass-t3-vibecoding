# Revert the integrated terminal to bash with a plain prompt

Status: accepted; supersedes [ADR 0004](0004-zsh-powerlevel10k-prompt.md)

ADR 0004 made `zsh` with powerlevel10k the terminal's shell. In practice the
theme cost more than it returned: a configuration wizard on first contact,
glyphs that depend on a Nerd Font installed on the client, an ordering bug
between the theme and `compinit` that hid the first prompt, and a managed block
written into the persistent `~/.zshrc` on every start. The terminal is a tool
for running commands, and the add-on owns it, so it should not need a wizard or
client-side fonts. The shell goes back to `bash`, with a short prompt block in
`/etc/bash.bashrc`.

What shapes the implementation:

- T3 still chooses the PTY shell from `$SHELL` and hydrates `PATH` with
  `<shell> -ilc`; `startup.sh` exports `SHELL=/bin/bash`, `useradd` records
  `/bin/bash`, and `bash -ilc` needs no special handling because the capture
  extracts values between markers.
- `/etc/bash.bashrc` is read by the interactive, non-login shell T3 opens, and
  it lives in the image, so add-on updates replace it and nothing is written to
  `/data/home`. A user's own `~/.bashrc` is read afterwards and can override
  the prompt.
- `bash-completion` is installed and loaded from the block: Debian only loads
  it from `/etc/profile`, which a terminal session never reads.
- The git branch comes from `/usr/lib/git-core/git-sh-prompt`, shipped by the
  `git` package that the image already installs, so the prompt adds no
  dependency. It prints nothing outside a repository.
- History moves to `/data/home/.bash_history` with `HISTCONTROL=ignoreboth`
  and `histappend`, which covers what the zsh setup provided.

## Considered Options

- Keep `zsh` installed without powerlevel10k: rejected because a bare `zsh`
  with no rc is worse than the bash prompt, and keeping the package means
  documenting and testing a second shell for no user.
- Keep powerlevel10k as an opt-in theme: rejected because its wizard and font
  requirements are exactly what made the terminal unreliable for users who
  never asked for them.
- Install `bash-completion` only, without a prompt: rejected because bash's
  default prompt has no colour and no branch, which is the "plain but ugly"
  terminal 0.14.0 was trying to avoid.
- Put the prompt in `~/.bashrc` with a managed block: rejected because the
  block machinery is what made the zsh setup fragile, and the persistent home
  is user data.
- Use `dash`: rejected because it has no history, completion or prompt
  customisation worth having in a coding terminal.

## Consequences

- The prompt uses colour escapes only: no glyph, no font, no wizard.
- `zsh` and powerlevel10k are gone from the image, and powerlevel10k is no
  longer a tracked component or a release-surface version.
- Existing `/data/home/.zshrc` and `~/.p10k.zsh` files are left untouched:
  nothing reads them once `zsh` is removed.
- `~/.bashrc` is not created or managed by the add-on; users who write one can
  replace the prompt, and the add-on will not fight them on the next start.
