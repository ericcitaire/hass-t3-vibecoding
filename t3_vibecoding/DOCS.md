# T3 Code + OpenCode

Environnement de **vibe coding headless** packagé comme add-on local Home
Assistant OS. Il exécute un serveur **T3 Code** (`t3 serve`, mode web) avec
**OpenCode** comme harness, sous un utilisateur **non-root** `dev` (uid/gid 1000).

## Composants embarqués

- `git`, `gh` (GitHub CLI)
- `node` 22 + `npm`
- `ripgrep`, `fd`, `jq`, `less`, `vim`, `nano`
- `build-essential`, `python3`, `openssh-client`
- `opencode-ai` et `t3` (installés globalement via npm)

## Options

| Option | Défaut | Description |
|---|---|---|
| `t3_port` | `4096` | Port TCP de l'interface web T3 Code. |
| `t3_host` | `0.0.0.0` | Adresse d'écoute (0.0.0.0 = exposé sur le LAN). |
| `workspace` | `/share/vibecoding` | Répertoire de travail / projet par défaut. |
| `git_name` | *(vide)* | `user.name` global git pour `dev`. |
| `git_email` | *(vide)* | `user.email` global git pour `dev`. |
| `t3_version` | `latest` | Informative : reconstruire l'add-on pour rafraîchir. |

## Persistance

| Chemin conteneur | Contenu | Persistant |
|---|---|---|
| `/data/home` | `HOME` de `dev`, config OpenCode, secrets | oui (`/data`) |
| `/data/t3code` | `T3CODE_HOME` : userdata, caches, worktrees, logs | oui (`/data`) |
| `/share/vibecoding` | Code source des projets | oui (dossier `share`) |

## Installation

1. **Paramètres → Add-ons → Boutique → ⋮ → Vérifier les mises à jour**, recharger.
2. L'add-on apparaît dans **Add-ons locaux** (dossier `/addons/t3_vibecoding`).
3. **Installer**, renseigner les options, **Démarrer**.
4. Onglet **Journal** : récupérer les informations d'appairage affichées par
   `t3 serve`, puis ouvrir `http://<IP-box>:4096/` et appairer.
5. Configurer les providers IA (OpenCode Zen / clés API) via l'UI T3 et
   `opencode auth` — persistés dans `/data`.

## Déploiement des fichiers

```bash
# depuis la session SSH & Web Terminal (ou un partage)
cp -r homeassistant-vibecoding-addon/* /addons/t3_vibecoding/
```

## Dépannage

- **L'add-on ne démarre pas / `init: false`** : la base Home Assistant embarque
  s6-overlay v3 ; ne pas passer `init: true`.
- **Port inaccessible** : vérifier `t3_host`/`t3_port` et que le port `4096/tcp`
  n'est pas déjà pris ; le watchdog Supervisor teste `tcp://host:4096`.
- **Build lent / stockage limité (box ARM)** : builder l'image ailleurs et
  référencer `image:` dans `config.yaml`.
- **Keyring headless** : `@napi-rs/keyring` peut ne pas trouver de Secret Service ;
  vérifier le fallback fichier dans les logs.
- **Sécurité réseau** : `0.0.0.0:4096` expose le port au LAN ; s'appuyer sur
  l'auth T3 et éviter une exposition Internet directe (préférer Tailscale).

## Mises à jour

Pour rafraîchir `t3`/`opencode`, incrémenter `version` dans `config.yaml` et
reconstruire l'add-on (reproductible), plutôt que `t3 update` dans le conteneur.
