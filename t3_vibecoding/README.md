# T3 Code + OpenCode — add-on Home Assistant

Add-on local Home Assistant OS pour le **vibe coding headless** : il embarque
tout le tooling (`git`, `node`, `npm`, `ripgrep`, `fd`, `gh`, build tools,
`python3`), installe **OpenCode** et **T3 Code**, et démarre automatiquement
`t3 serve` sous un utilisateur **non-root** (`dev`).

- Interface web T3 Code exposée sur `http://<hôte>:4096/` (appairage géré par T3).
- État persistant dans `/data` (survit aux mises à jour de l'add-on).
- Workspace par défaut : `/share/vibecoding` (dossier HA `share`).
- Redémarrage automatique au boot de la box (`boot: auto`).

Voir [DOCS.md](DOCS.md) pour l'installation, l'appairage et le dépannage.
