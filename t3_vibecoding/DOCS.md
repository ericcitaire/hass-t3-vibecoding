# T3 Code + OpenCode

Environnement de **vibe coding headless** packagé comme add-on local Home
Assistant OS. Il exécute un serveur **T3 Code** (`t3 serve`, mode web) avec
**OpenCode** comme harness, sous un utilisateur **non-root** `dev` (uid/gid 1000).

## Composants embarqués

- `git`, `gh` (GitHub CLI)
- `node` 22 + `npm`
- `ripgrep`, `fd`, `jq`, `less`, `vim`, `nano`
- `build-essential`, `python3`, `openssh-client`
- `opencode-ai` 1.19.3 et `t3` 0.1.0 (versions stables épinglées, installées
  globalement via npm)
- `code-server` 4.141.0 (VS Code dans le navigateur, optionnel)

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
| `code_server` | `false` | Active l'éditeur web **code-server** (VS Code) sur le port `8081`. |
| `code_server_password` | *(vide)* | Mot de passe de code-server. **Requis** si `code_server` est activé. |

## Éditeur web code-server (optionnel)

En plus de T3 Code, l'add-on peut lancer **code-server**, un VS Code complet
accessible dans le navigateur (éditeur, terminal, LSP, extensions Open VSX).

1. Renseigner `code_server_password` (option masquée).
2. Cocher `code_server`.
3. Démarrer / redémarrer l'add-on.
4. Ouvrir `http://<IP-box>:8081/` et se connecter avec ce mot de passe.

Points importants :

- Le port est **fixe** (`8081`) et distinct de T3 Code (`4096`). code-server
  n'est pas exposé via l'ingress Home Assistant (sous-chemin non supporté) :
  il s'ouvre dans un onglet séparé.
- Si `code_server` est activé sans mot de passe, code-server n'est **pas**
  démarré et un avertissement apparaît dans le journal.
- Le mot de passe est réécrit dans `~/.config/code-server/config.yaml` à chaque
  démarrage : le modifier depuis l'UI code-server n'est pas persistant, utiliser
  l'option de l'add-on.
- code-server tourne sous l'utilisateur `dev`, avec le même `HOME` et le même
  workspace que T3 Code (`/share/vibecoding` par défaut).
- Le mot de passe et le port donnent un **accès shell complet** : ne pas exposer
  `8081` sur Internet. Rester sur le LAN ou passer par un VPN (Tailscale, etc.).
- Les réglages et extensions sont persistés dans
  `/data/home/.local/share/code-server` ; la configuration dans
  `/data/home/.config/code-server`.
- Les extensions proviennent d'**Open VSX** (le marketplace Microsoft n'est pas
  accessible depuis code-server).

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
| `/data/home` | `HOME` de `dev`, config OpenCode/gh/code-server, secrets | oui (`/data`) |
| `/data/home/.local/share/code-server` | Réglages et extensions code-server | oui (`/data`) |
| `/data/t3code` | `T3CODE_HOME` : userdata, caches, worktrees, logs | oui (`/data`) |
| `/share/vibecoding` | Code source des projets | oui (dossier `share`) |

## Installation

1. **Paramètres → Add-ons → Boutique → ⋮ → Dépôts**, ajouter l'URL du dépôt.
2. L'add-on apparaît sous le nom du dépôt.
3. **Installer**, renseigner les options, **Démarrer**.
4. Onglet **Journal** : récupérer les informations d'appairage affichées par
   `t3 serve`, puis ouvrir `http://<IP-box>:4096/` et appairer.
5. *(Optionnel)* Activer `code_server`, définir `code_server_password`, puis
   ouvrir `http://<IP-box>:8081/`.
6. Configurer finement dans l'UI T3 Code si besoin (persisté dans `/data`).

## Dépannage

- **L'add-on ne démarre pas / `init: false`** : la base Home Assistant embarque
  s6-overlay v3 ; ne pas passer `init: true`.
- **`gh auth login` échoue** : token invalide/expiré ou scope insuffisant
  (`repo`). Vérifier le journal.
- **JSON ignoré** : le message « JSON invalide » apparaît dans le journal ;
  corriger le collage.
- **Port inaccessible** : vérifier `t3_host`/`t3_port` ; le watchdog Supervisor
  teste `tcp://host:4096`.
- **code-server ne démarre pas** : vérifier que `code_server_password` est
  renseigné et que le port `8081` est libre sur l'hôte. Les erreurs et les
  redémarrages apparaissent dans le journal de l'add-on.
- **Mot de passe code-server refusé** : le mot de passe est réécrit depuis
  l'option `code_server_password` à chaque démarrage ; le modifier dans
  l'éditeur ne suffit pas.
- **`OpenCode CLI version probe timed out after 4 seconds`** : le binaire
  OpenCode peut mettre plus de 4 secondes à démarrer sur certaines machines,
  alors que T3 Code impose ce délai à `opencode --version`. L'add-on installe un
  wrapper qui répond immédiatement à `--version` ; les autres commandes sont
  transmises au binaire réel. Si le message persiste, vérifier qu'aucun
  `binaryPath` personnalisé ne pointe directement vers `opencode.real`.
- **Keyring headless** : `@napi-rs/keyring` peut ne pas trouver de Secret Service ;
  vérifier le fallback fichier dans les logs.
- **Sécurité réseau** : `0.0.0.0:4096` expose le port au LAN ; s'appuyer sur
  l'auth T3 et éviter une exposition Internet directe (préférer Tailscale).

## Mises à jour

Les versions d'`opencode-ai`, de `t3` et de `code-server` sont épinglées dans le
`Dockerfile` via les arguments de build `OPENCODE_VERSION`, `T3_VERSION` et
`CODE_SERVER_VERSION` (actuellement `1.19.3`, `0.1.0` et `4.141.0`). Pour
rafraîchir les applicatifs :

1. rechercher la dernière version stable sur npm (`npm view opencode-ai version`,
   `npm view t3 version`) et sur les releases GitHub de code-server ;
2. mettre à jour les valeurs par défaut des `ARG` dans le `Dockerfile` ;
3. incrémenter `version` dans `config.yaml` et ajouter une entrée au
   `CHANGELOG.md` ;
4. reconstruire l'add-on.

Changer la valeur d'un `ARG` invalide le cache Docker des couches concernées : la
nouvelle version est donc réellement réinstallée (contrairement à un rebuild à
`Dockerfile` inchangé). Éviter `t3 update` dans le conteneur : la mise à jour
serait perdue à la reconstruction et moins reproductible.
