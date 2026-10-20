# Use T3 Code's terminal and Files panel instead of a bundled web IDE

Status: accepted

The add-on bundled code-server (VS Code in the browser) as an optional second
web IDE. It cost ~229 MiB compressed, a second port, a password and an s6
service, while T3 Code 0.1.0 already ships an integrated terminal and an
editable Files panel bound to the same container and workspace. We removed
code-server entirely and made those T3 surfaces the supported way to edit and
run commands, keeping `vim` and `nano` as CLI fallbacks.

## Considered Options

- Keep code-server optional: rejected because "optional" still means shipping
  and maintaining the image layer, service, options, tests and docs, and the
  feature duplicated what T3 already provides.
- Replace it with a lighter web terminal (ttyd) or an SSH daemon: rejected
  because T3's terminal already grants a PTY in the container; a second entry
  point would add another credential and attack surface.
- Rely on the Home Assistant *Terminal & SSH* add-on: kept as the documented
  break-glass path when T3 itself is down, not as the normal editing surface.

## Consequences

- Users lose code-server's LSP, debugging and Open VSX extensions. The
  Files panel covers browsing and editing; the terminal covers everything else.
- File and terminal access depend on the scopes of the paired T3 client. A
  client paired before the required scopes existed must re-pair; the add-on
  does not silently revoke sessions.
- Existing code-server settings and extensions stay on disk but are inert. The
  docs give the two directories to delete to reclaim space.
