# Make zsh with powerlevel10k the integrated terminal's shell

Status: accepted

The add-on installed `zsh` next to `bash` but left the integrated terminal on
`bash`, so users had to know that `zsh` existed and start it by hand. 0.14.0
installs [powerlevel10k](https://github.com/romkatv/powerlevel10k) and makes
`zsh` the shell T3 opens, so the terminal is pleasant by default while staying
a plain, framework-free shell.

Three constraints shaped the implementation:

- T3 chooses the PTY shell from `$SHELL`, falling back to `bash`; it does not
  read `/etc/passwd` for that. `startup.sh` therefore exports `SHELL=/bin/zsh`
  (and `usermod` keeps `/etc/passwd` consistent for `docker exec` and for the
  `PATH` hydration candidates).
- At startup T3 hydrates `PATH` by running `zsh -ilc` **without a TTY**. That is
  an *interactive* shell, so powerlevel10k would offer its configuration wizard
  inside a pipe on every server start. The block appended to
  `/etc/zsh/zshrc` only loads the theme when `[[ -t 0 && -t 1 ]]`, which is true
  in the PTY and false in the hydration subprocess.
- The persistent `HOME` (`/data/home`) makes any file there user data. The
  theme lives in `/usr/share/powerlevel10k`, unpacked from the pinned upstream
  tarball (no `.git`), and the add-on never writes or seeds `~/.p10k.zsh`: the
  wizard creates it on first use and the user owns it afterwards.

## Considered Options

- Keep `bash` by default and let users type `zsh`: rejected because the prompt
  styling is then invisible to anyone who does not already know it is there.
- `chsh -s /bin/zsh dev` alone: rejected because T3 ignores the login shell
  when it spawns the PTY.
- Ship Oh My Zsh on top of powerlevel10k: rejected because powerlevel10k runs
  standalone, and the extra framework adds startup output and behaviour the
  add-on would have to document without using.
- Seed `~/.zshrc` and `~/.p10k.zsh` on first boot: rejected because the home is
  persistent user data; a shipped theme would then either overwrite user edits
  or never receive fixes.
- Pin a commit hash instead of the `v1.20.0` tag: rejected for legibility; the
  tag's commit is recorded next to the build arg if the tag ever moves.
- Install a Nerd Font in the image: rejected because glyphs are rendered by the
  client browser; a font in the image would only serve the headless preview
  browser. `DOCS.md` points at `fontFamilyTerminal` instead.

## Consequences

- The first zsh session shows powerlevel10k's configuration wizard; users who
  want no prompt customisation must answer it once, or answer `n` each time.
- The prompt's appearance depends on the client: without a Nerd Font, glyphs
  render as boxes until the user installs one or picks the wizard's ASCII mode.
- `PATH` hydration now runs through `zsh` rather than `bash`, so anything that
  only exists in `/etc/profile.d` still applies (Debian's `zprofile` sources
  it), but a broken `/etc/zsh/zshenv` would now affect server startup.
- The Debian `compinit` call is Ubuntu-only, so the appended block initialises
  completion itself; a future Debian change may require revisiting that.
- `/usr/share/powerlevel10k` is owned by root and not writable by `dev`, so the
  optional `gitstatusd` helper is downloaded on first prompt into
  `/data/home/.cache/gitstatus` instead. Until then, git status is computed by
  the slower pure-zsh fallback.
