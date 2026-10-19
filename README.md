# Home Assistant add-ons by Eric

Dépôt d'add-ons locaux pour Home Assistant OS.

## Ajouter ce dépôt à Home Assistant

1. **Paramètres → Add-ons → Boutique**.
2. Menu **⋮ → Dépôts**.
3. Coller l'URL du dépôt :
   - Dépôt public : `https://github.com/ericcitaire/hass-t3-vibecoding`
   - Dépôt privé : `https://<TOKEN>@github.com/ericcitaire/hass-t3-vibecoding`
     (token GitHub *Personal access token* avec le scope `repo`).
4. **Ajouter**, puis recharger la page. Les add-ons apparaissent sous le nom du
   dépôt.

## Add-ons

| Add-on | Description |
|---|---|
| [T3 Code + OpenCode](t3_vibecoding) | Vibe coding headless : serveur T3 Code + OpenCode, tooling dev, user non-root. |

## Vérifications

La cohérence des options entre `config.yaml`, les traductions, `DOCS.md` et
`run.sh`, ainsi que celle des ports conteneur, est vérifiée par la CI :

```bash
python3 -m pip install --user pyyaml
python3 scripts/verify-options.py
bash tests/test-startup.sh
bash tests/test-code-server.sh
bash tests/test-credentials.sh
```
