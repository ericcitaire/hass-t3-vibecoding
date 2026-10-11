# Plan — Add-on Home Assistant « T3 Code + OpenCode » (vibe coding headless)

## 1. Objectif

Fournir, sur une box **HAOS**, un environnement de vibe coding packagé en **add-on
local** (conteneur géré par Supervisor) qui :

- embarque le tooling nécessaire : `git`, `node`, `npm`, `ripgrep`, plus outils
  usuels (`jq`, `fd`, `build-essential`, `python3`, `gh`, …) ;
- installe **OpenCode** et **T3 Code** ;
- **démarre T3 Code automatiquement au boot** (`t3 serve`) ;
- exécute le workload sous un **utilisateur dédié non-root** (`dev`), avec
  isolation (pas de privilèges, AppArmor, surface réseau minimale).

## 2. Constat / contraintes (vérifiés)

### HAOS
- Appliance verrouillée (Buildroot) : rootfs **read-only**, **pas de gestionnaire
  de paquets** sur l'hôte, mise à jour de l'OS qui écrase les modifs.
- **Docker appartient à Supervisor** : impossible de lancer ses propres
  conteneurs. Le **seul** mécanisme supporté = **add-on**.
- Les add-ons sont des conteneurs Docker décrits par `config.yaml` + `Dockerfile`
  + script d'entrée (`run.sh`), base `ghcr.io/home-assistant/base*` (s6-overlay +
  bashio).

### T3 Code (vérifié via le CLI `t3` 0.0.45, binaire self-contained + client web)
- CLI `t3` (npm `t3`, dépôt `pingdotgg/t3code`), sous-commandes :
  - `t3 serve` → **serveur headless** (HTTP/WebSocket) + **client web**, imprime
    les infos d'appairage (pas de navigateur). C'est notre mode cible.
  - `--mode web` → mode web (le mode `desktop` garde les défauts loopback).
  - `--host`, `--port`, `--base-dir` (= `T3CODE_HOME`), `--no-browser`,
    `--auto-bootstrap-project-from-cwd`, `--tailscale-serve`.
  - `t3 auth pairing|session` → plan de contrôle d'auth pour déploiement headless.
  - `t3 service install` → service système (systemd/launchd). **À NE PAS utiliser
    ici** : pas de systemd dans le conteneur ; c'est **Supervisor** qui gère le
    cycle de vie.
- État persistant dans le **base-dir** (`userdata/`, `caches/`, `worktrees/`,
  `scratch/`, logs, keybindings…). Chez Eric, défaut = `~/.t3`.
- Dépendances natives notables : `node-pty` (terminaux), `@napi-rs/keyring`
  (coffre de secrets).

### OpenCode
- Binaire self-contained (`curl -fsSL https://opencode.ai/install | bash` →
  `~/.opencode/bin/opencode`) ou npm `opencode-ai`. T3 Code l'utilise comme
  **harness/provider** (donc doit être présent dans le `PATH`).

## 3. Décisions d'architecture

| Sujet | Décision | Raison |
|---|---|---|
| Emballage | **Add-on local** (dossier `/addons/t3_vibecoding`) | Seule voie supportée sur HAOS |
| Base image | **`ghcr.io/home-assistant/base-debian:trixie`** (glibc) | Le binaire `t3` est compilé (Bun) et vise glibc ; Alpine/musl = risque. Base-débian dispo officiellement |
| `init` | `false` | La base HA embarque s6-overlay v3 (sinon l'add-on ne démarre pas) |
| Démarrage | `boot: auto`, `startup: application`, `CMD` = `run.sh` qui fait `exec t3 serve` | Redémarrage/watchdog gérés par Supervisor → répond à « démarre au boot » |
| Utilisateur | **non-root** `dev` (uid/gid 1000), drop via `s6-setuidgid` | Exigence d'isolation |
| Persistance | `T3CODE_HOME=/data/t3code`, `HOME=/data/home`, workspace sur `/share` | `/data` survit aux MAJ ; `/share` pour le code |
| Réseau | Bind `0.0.0.0:4096`, exposé via `ports` + `webui` (pas d'ingress) | Ingress sous-chemin + WebSocket = fragile ; T3 Code a sa propre auth d'appairage |
| Secrets | Auth via l'UI T3 + `opencode auth`, persistés dans `/data` ; pas de clé en clair dans les options | Options d'add-on = visibles en UI/logs |
| Privilèges | Aucun `privileged`, `full_access: false`, `hassio_api/homeassistant_api/auth_api: false` | Isolation maximale |

> Note honnête sur « pas de root » : le **conteneur** est lancé par Supervisor
> (le runtime de l'add-on tourne en root par conception). Ce qu'on garantit, c'est
> que **le workload** (`t3`, OpenCode, terminaux, outils) tourne en **`dev`
> non-root**, avec AppArmor actif, caps minimales et surface réseau/volumes
> réduite. Le « rootless » complet n'est pas possible pour un add-on HA.

## 4. Arborescence à créer

Dans ce dossier (copie versionnée), puis déployée dans `/addons/t3_vibecoding/` :

```
homeassistant-vibecoding-addon/
├── PLAN.md            # ce document
├── config.yaml        # métadonnées + options/schema de l'add-on
├── Dockerfile         # image : outils + opencode + t3 + user dev
├── run.sh             # entrée : prépare /data, drop non-root, exec t3 serve
├── DOCS.md            # doc utilisateur (options, appairage, dépannage)
├── README.md          # description courte
├── CHANGELOG.md
├── icon.png           # 128x128 (optionnel)
├── logo.png           # 250x100 (optionnel)
└── translations/
    ├── en.yaml
    └── fr.yaml
```

## 5. Spécification des fichiers

### 5.1 `config.yaml` (brouillon)

```yaml
name: "T3 Code + OpenCode"
version: "0.1.0"
slug: "t3_vibecoding"
description: >-
  Environnement de vibe coding headless : serveur T3 Code + OpenCode, avec git,
  node, ripgrep et outils usuels, exécutés sous un utilisateur non-root.
url: "https://github.com/pingdotgg/t3code"
arch:
  - amd64
  - aarch64
init: false
startup: application
boot: auto
panel_icon: mdi:code-braces
panel_title: "T3 Code"
map:
  - type: share
    read_only: false
  - type: app_config
    read_only: false
ports:
  "4096/tcp": 4096
ports_description:
  "4096/tcp": "Interface web T3 Code"
webui: "http://[HOST]:[PORT:4096]/"
watchdog: "tcp://[HOST]:[PORT:4096]"
options:
  t3_port: 4096
  t3_host: "0.0.0.0"
  workspace: "/share/vibecoding"
  git_name: ""
  git_email: ""
  t3_version: "latest"
schema:
  t3_port: port
  t3_host: str
  workspace: str
  git_name: "str?"
  git_email: "str?"
  t3_version: str
```

### 5.2 `Dockerfile` (brouillon)

```dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg git jq ripgrep fd-find less vim nano \
      build-essential python3 unzip xz-utils procps openssh-client \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && ln -sf "$(command -v fdfind)" /usr/local/bin/fd \
 && rm -rf /var/lib/apt/lists/*

# Tooling IA (global, lisible par tous)
RUN npm install -g --omit=dev opencode-ai t3

# Utilisateur non-root
RUN useradd -u 1000 -g 1000 -m -s /bin/bash dev

COPY run.sh /
RUN chmod a+x /run.sh

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
```

Points d'attention :
- `BUILD_VERSION` / `BUILD_ARCH` sont fournis automatiquement par Supervisor.
- Sur Debian, `fd-find` s'installe sous le nom `fdfind` → symlink `fd` créé.
- `gh` (GitHub CLI) non présent dans les dépôts de base : à ajouter via le dépôt
  apt de GitHub ou un tarball (optionnel, cf. §9).

### 5.3 `run.sh` (brouillon)

```bash
#!/usr/bin/with-contenv bashio
set -e

DEV_UID=1000
DEV_GID=1000
HOME_DIR="/data/home"
T3_HOME="/data/t3code"

T3_PORT="$(bashio::config 't3_port')"
T3_HOST="$(bashio::config 't3_host')"
WORKSPACE="$(bashio::config 'workspace')"
GIT_NAME="$(bashio::config 'git_name')"
GIT_EMAIL="$(bashio::config 'git_email')"

bashio::log.info "Préparation des répertoires persistants"
mkdir -p "${HOME_DIR}" "${T3_HOME}" "${WORKSPACE}"
chown -R "${DEV_UID}:${DEV_GID}" "${HOME_DIR}" "${T3_HOME}"
chown "${DEV_UID}:${DEV_GID}" "${WORKSPACE}"

if bashio::var.has_value "${GIT_NAME}"; then
  env HOME="${HOME_DIR}" s6-setuidgid dev git config --global user.name "${GIT_NAME}"
fi
if bashio::var.has_value "${GIT_EMAIL}"; then
  env HOME="${HOME_DIR}" s6-setuidgid dev git config --global user.email "${GIT_EMAIL}"
fi

bashio::log.info "Démarrage de T3 Code sur ${T3_HOST}:${T3_PORT} (user dev, workspace=${WORKSPACE})"

exec env \
  HOME="${HOME_DIR}" \
  T3CODE_HOME="${T3_HOME}" \
  XDG_CONFIG_HOME="${HOME_DIR}/.config" \
  XDG_DATA_HOME="${HOME_DIR}/.local/share" \
  XDG_CACHE_HOME="${HOME_DIR}/.cache" \
  TERM="xterm-256color" \
  PATH="/usr/local/bin:/usr/bin:/bin:${HOME_DIR}/.opencode/bin" \
  s6-setuidgid dev \
  t3 serve \
    --mode web \
    --host "${T3_HOST}" \
    --port "${T3_PORT}" \
    --base-dir "${T3_HOME}" \
    --no-browser \
    --auto-bootstrap-project-from-cwd \
    "${WORKSPACE}"
```

`exec` final = `t3 serve` devient le process principal → logs et signaux
propres, watchdog Supervisor fonctionnel. L'appairage (URL + token/QR) apparaît
dans les **logs de l'add-on**.

### 5.4 `translations/fr.yaml` + `en.yaml`

Labels/descriptions pour : `t3_port`, `t3_host`, `workspace`, `git_name`,
`git_email`, `t3_version`. Et `network: {"4096/TCP": ...}`.

## 6. Flux d'installation & test (sur la box)

1. Installer/ouvrir l'add-on **Advanced SSH & Web Terminal**, se connecter.
2. Créer `/addons/t3_vibecoding/` et y copier les fichiers (§4).
3. HA → **Paramètres → Add-ons → Store → ⋮ → Vérifier les mises à jour**, puis
   recharger la page. L'add-on apparaît en **« Add-ons locaux »**.
4. **Installer**, renseigner les options (`workspace`, `git_name/email`), démarrer.
5. **Appairage** : ouvrir l'onglet logs, récupérer les infos d'appairage
   (`t3 serve`), ouvrir `http://<IP-box>:4096/` et appairer.
6. Configurer les providers IA (OpenCode Zen / clés API) via l'UI T3 + `opencode
   auth`, persistés dans `/data/home` et `/data/t3code`.

## 7. Vérifications (smoke tests)

- [ ] Image build sans erreur (`t3 --version`, `opencode --version`, `git --version`, `rg --version`).
- [ ] `run.sh` démarre et `t3 serve` écoute sur `0.0.0.0:4096`.
- [ ] `id` du process `t3` = `dev` (uid 1000), **pas root**.
- [ ] Redémarrage de l'add-on → projets/threads **persistés** (`/data/t3code`).
- [ ] Reboot de la box → add-on redémarre tout seul (`boot: auto`).
- [ ] Ouverture terminal dans T3 Code (node-pty) OK.
- [ ] Aucune capability privilégiée ; AppArmor actif.

## 8. Risques & points de vigilance

- **Taille/build** : node + outils + binaire `t3` (~160 Mo) → image ~0,5–1 Go ;
  build lent et stockage limité sur box ARM (Green/Yellow). Envisager de builder
  ailleurs et publier via `image:` si ça coince.
- **glibc vs musl** : on part sur Debian pour éviter le piège musl d'Alpine.
- **Keyring headless** : `@napi-rs/keyring` peut ne pas trouver de Secret Service
  → vérifier le fallback fichier ; sinon prévoir une variable/flag dédiée.
- **Sécurité réseau** : `0.0.0.0:4096` expose le port sur le LAN. S'appuyer sur
  l'auth T3 ; éviter une exposition Internet directe. Alternative : bind sur IP
  Tailscale + `--tailscale-serve`.
- **Mises à jour `t3`** : `t3 update` écrit dans le base-dir ; dans le conteneur,
  privilégier une montée de **version de l'add-on** (rebuild) pour rester
  reproductible. `t3_version: latest` = rebuild pour rafraîchir.
- **Ingress** non utilisé (WebSocket + chemins absolus) : on reste sur port +
  `webui`.

## 9. Décisions à valider avec Eric

1. **Architecture de la box** : `amd64` ou `aarch64` ? (impacte uniquement le tag
   de base si on pin, le multi-arch couvre les deux).
2. **Providers IA** : OpenCode Zen, clés API (OpenAI/Anthropic), ou Claude
   Code/Codex en plus ? Où stocker les secrets ?
3. **Emplacement du workspace** : `/share/vibecoding` convient, ou un sous-dossier
   précis ? Git init/credentials à prévoir ?
4. **Exposition réseau** : LAN seulement, Tailscale, ou reverse proxy HA ?
5. **Tooling additionnel** : `gh`, `docker` CLI, `python` + pip, `uv`, runtime
   `bun`, etc. ?
6. **Politique de version** : épingler `t3`/`opencode` ou suivre `latest` ?
7. **`init: false`** : à confirmer au premier build (contrainte s6 v3).

## 10. TODO (implémentation)

- [ ] Valider les décisions du §9.
- [ ] Créer `config.yaml`, `Dockerfile`, `run.sh`, traductions, `DOCS/README/CHANGELOG`.
- [ ] (Option) icônes `icon.png` / `logo.png`.
- [ ] Build local de test (hors HA de préférence) : `docker build`.
- [ ] Déployer dans `/addons/t3_vibecoding`, installer via l'UI, appairer.
- [ ] Passer les smoke tests §7.
- [ ] Rédiger `DOCS.md` (appairage, providers, dépannage, sauvegardes).
