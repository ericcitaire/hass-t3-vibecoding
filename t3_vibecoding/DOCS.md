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
| `github_token` | *(vide)* | Token GitHub pour `gh auth login` (+ export `GH_TOKEN`). |
| `env_vars` | `[]` | Variables d'environnement passées à T3 Code. |
| `opencode_config_json` | *(vide)* | JSON → `~/.config/opencode/opencode.json`. |
| `opencode_auth_json` | *(vide)* | JSON → `~/.local/share/opencode/auth.json`. |
| `t3_settings_json` | *(vide)* | JSON fusionné dans `<T3CODE_HOME>/userdata/settings.json`. |

## Configuration des providers / clés d'API

T3 Code délègue l'auth à ses *drivers* (OpenCode, Codex, Claude, Cursor, Grok).
On configure donc les identifiants **en amont**, depuis l'add-on.

### 1. Variables d'environnement (le plus simple)

Champ `env_vars` : liste de paires `name` / `value`. Exemples de clés reconnues
par OpenCode :

```yaml
env_vars:
  - name: ANTHROPIC_API_KEY
    value: "sk-ant-..."
  - name: OPENAI_API_KEY
    value: "sk-..."
  - name: OPENROUTER_API_KEY
    value: "sk-or-..."
```

Les valeurs sont de type `password` (masquées dans l'UI).

### 2. Config OpenCode (JSON)

Coller dans `opencode_config_json` le contenu de `~/.config/opencode/opencode.json`
(providers, modèles, options) :

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "provider": {
    "anthropic": { "options": { "apiKey": "sk-ant-..." } }
  }
}
```

### 3. Auth OpenCode (JSON)

Pour des identifiants au format `opencode auth` (api/oauth), coller dans
`opencode_auth_json` le contenu de `~/.local/share/opencode/auth.json`.

> Les JSON sont validés par `jq` au démarrage, puis écrits avant le lancement de
> T3 Code. Un JSON invalide est ignoré avec un avertissement dans le journal.

### 4. Réglages T3 Code (`settings.json`)

Par défaut **aucun driver n'est activé** dans T3 Code, et le modèle de génération
par défaut pointe sur `codex` (indisponible ici). Pour que l'add-on soit utilisable
dès le départ, renseigner `t3_settings_json`. Ce JSON est **fusionné
récursivement** dans `<T3CODE_HOME>/userdata/settings.json` : tes clés gagnent,
les autres (réglages faits dans l'UI) sont préservées.

Exemple : activer le driver OpenCode et prendre DeepSeek par défaut.

```json
{
  "providers": {
    "opencode": { "enabled": true }
  },
  "textGenerationModelSelection": {
    "instanceId": "opencode",
    "model": "deepseek/deepseek-chat"
  }
}
```

Drivers disponibles sous `providers` : `opencode`, `codex`, `claudeAgent`,
`cursor`, `grok`, `antigravity` — chacun avec un champ `enabled` (défaut `false`).

> Le fichier vit dans `/data/t3code/userdata/settings.json` et survit aux mises à
> jour de l'add-on.

### 5. GitHub CLI (`gh`)

Renseigner `github_token` (classic PAT, scope `repo`) : l'add-on exécute
`gh auth login --with-token` + `gh auth setup-git`, et exporte `GH_TOKEN`. La
config persiste dans `/data/home/.config/gh`.

## Persistance

| Chemin conteneur | Contenu | Persistant |
|---|---|---|
| `/data/home` | `HOME` de `dev`, config OpenCode/gh, secrets | oui (`/data`) |
| `/data/t3code` | `T3CODE_HOME` : userdata, caches, worktrees, logs | oui (`/data`) |
| `/share/vibecoding` | Code source des projets | oui (dossier `share`) |

## Installation

1. **Paramètres → Add-ons → Boutique → ⋮ → Dépôts**, ajouter l'URL du dépôt.
2. L'add-on apparaît sous le nom du dépôt.
3. **Installer**, renseigner les options, **Démarrer**.
4. Onglet **Journal** : récupérer les informations d'appairage affichées par
   `t3 serve`, puis ouvrir `http://<IP-box>:4096/` et appairer.
5. Configurer finement dans l'UI T3 Code si besoin (persisté dans `/data`).

## Dépannage

- **L'add-on ne démarre pas / `init: false`** : la base Home Assistant embarque
  s6-overlay v3 ; ne pas passer `init: true`.
- **`gh auth login` échoue** : token invalide/expiré ou scope insuffisant
  (`repo`). Vérifier le journal.
- **JSON ignoré** : le message « JSON invalide » apparaît dans le journal ;
  corriger le collage.
- **Port inaccessible** : vérifier `t3_host`/`t3_port` ; le watchdog Supervisor
  teste `tcp://host:4096`.
- **Keyring headless** : `@napi-rs/keyring` peut ne pas trouver de Secret Service ;
  vérifier le fallback fichier dans les logs.
- **Sécurité réseau** : `0.0.0.0:4096` expose le port au LAN ; s'appuyer sur
  l'auth T3 et éviter une exposition Internet directe (préférer Tailscale).

## Mises à jour

Pour rafraîchir `t3`/`opencode`, incrémenter `version` dans `config.yaml` et
reconstruire l'add-on (reproductible), plutôt que `t3 update` dans le conteneur.
