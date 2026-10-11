# Changelog

## 0.3.0

- Option `t3_settings_json` : JSON fusionné (récursivement) dans
  `<T3CODE_HOME>/userdata/settings.json` pour activer les drivers et définir le
  comportement par défaut (modèle de génération). Permet d'activer le harness
  OpenCode sans passer par l'UI.
- Validation JSON via `jq` ; fusion sans écraser les réglages issus de l'UI.
- Traduction de la nouvelle option (`en`/`fr`).

## 0.2.0

- Option `github_token` : `gh auth login --with-token` + `gh auth setup-git`,
  et export de `GH_TOKEN`.
- Option `env_vars` (liste nom/valeur) : variables d'environnement passées à
  T3 Code (clés d'API des providers).
- Option `opencode_config_json` : écrit `~/.config/opencode/opencode.json`.
- Option `opencode_auth_json` : écrit `~/.local/share/opencode/auth.json`.
- Validation JSON via `jq` (JSON invalide ignoré avec avertissement).
- Nouvelles traductions pour les options ajoutées.

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
