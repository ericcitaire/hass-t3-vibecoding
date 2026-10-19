# Changelog

## 0.6.0

- Retrait des options trompeuses : `t3_port`, `t3_host` et `t3_version` n'étaient
  pas (ou seulement partiellement) honorées. Le port conteneur T3 Code est fixé à
  `4096`, l'écoute à `0.0.0.0`, et seul le port **hôte** se configure dans les
  réglages réseau de l'add-on.
- Retrait des surfaces mortes : montage `config` (déprécié et inutilisé),
  `panel_icon`/`panel_title` (aucun ingress) et `ports_description` (doublon des
  traductions).
- Ajout de `scripts/verify-options.py` et d'une GitHub Action qui vérifient la
  cohérence options / schéma / traductions / `DOCS.md` / ports / `run.sh`.
- Suppression de `PLAN.md`, plan d'implémentation obsolète et contradictoire.

## 0.5.1

- Correctif du health check OpenCode de T3 Code : `opencode --version` pouvait
  dépasser le délai de 4 secondes (`OpenCode CLI version probe timed out after
  4 seconds`) à cause du temps de démarrage du binaire compilé.
- Un wrapper léger répond immédiatement à `opencode --version` ; toutes les
  autres commandes sont transmises au binaire réel `opencode.real`.

## 0.5.0

- Ajout de **code-server 4.141.0** (VS Code dans le navigateur), installé depuis
  la release GitHub officielle et épinglé via `CODE_SERVER_VERSION`.
- Nouvelles options `code_server` (désactivé par défaut) et
  `code_server_password` pour activer et protéger l'éditeur web depuis l'UI de
  configuration Home Assistant.
- Port `8081` dédié (T3 Code reste sur `4096`) ; code-server tourne sous
  l'utilisateur `dev`, en parallèle de `t3 serve`, et redémarre automatiquement
  en cas d'arrêt.
- Configuration et extensions code-server persistées dans `/data/home`.
- Traductions `en`/`fr` et documentation mises à jour.

## 0.4.0

- Mise à jour des applicatifs embarqués : **OpenCode 1.19.3** et **T3 Code
  0.1.0** (dernières versions stables publiées sur npm).
- Versions épinglées via les arguments de build `OPENCODE_VERSION` et
  `T3_VERSION` : le cache Docker de la couche npm est invalidé quand une version
  change, ce qui garantit que l'image reconstruite contient bien la nouvelle
  version.
- Journalisation des versions `opencode` et `t3` au démarrage de l'add-on.

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
