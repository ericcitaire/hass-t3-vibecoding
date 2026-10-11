# Changelog

## 0.1.0

- Initialisation de l'add-on local « T3 Code + OpenCode ».
- Image Debian (glibc) avec tooling dev : git, gh, node 22, npm, ripgrep, fd,
  jq, build-essential, python3, openssh-client.
- Installation globale de `opencode-ai` et `t3`.
- Utilisateur non-root `dev` (uid/gid 1000).
- `run.sh` : préparation des répertoires persistants, config git, puis
  `exec t3 serve` (mode web) sous `dev`.
- Persistance dans `/data/home` et `/data/t3code`, workspace sur `/share/vibecoding`.
- Traductions `en`/`fr`.
