# 🛡️ wplace.live — Moniteur anti-grief

Bot de surveillance automatique pour [wplace.live](https://wplace.live).
Il surveille une zone de pixel art et t'envoie une alerte Discord dès que
quelqu'un la modifie de manière significative (griefing).

**Hébergement** : GitHub Actions (gratuit, tourne même PC éteint).

---

## 📁 Structure du projet

| Fichier | Rôle |
|---|---|
| `monitor.py` | Script Python principal : télécharge la tuile, découpe la zone, compare avec la référence précédente, et envoie une alerte Discord si le changement dépasse le seuil. |
| `requirements.txt` | Liste des dépendances Python (`requests`, `Pillow`, `numpy`). |
| `.github/workflows/monitor.yml` | Workflow GitHub Actions : exécute `monitor.py` toutes les 5 minutes via cron, et committe automatiquement l'image de référence mise à jour. |
| `reference.png` | Image de référence (générée automatiquement au premier run, committée par le bot). |
| `.gitignore` | Exclut les fichiers temporaires Python du dépôt. |

---

## 🚀 Guide d'installation pas à pas

### Étape 1 — Créer un webhook Discord

1. Ouvre Discord, va dans le **serveur** et le **salon** où tu veux recevoir les alertes.
2. Clique sur la **roue dentée** (paramètres du salon) → **Intégrations** → **Webhooks**.
3. Clique **Nouveau webhook**, donne-lui un nom (ex: "wplace monitor").
4. Clique **Copier l'URL du webhook** — garde-la, on en aura besoin à l'étape 4.

### Étape 2 — Créer le dépôt GitHub

1. Va sur [github.com/new](https://github.com/new).
2. Nom du dépôt : `wplace-monitor` (ou ce que tu veux).
3. Visibilité : **Private** (recommandé, pour ne pas exposer ton image de référence).
4. **Ne coche PAS** "Add a README" (on a déjà le nôtre).
5. Clique **Create repository**.

### Étape 3 — Pousser les fichiers

Ouvre un terminal dans le dossier du projet (`wplace-monitor/`) et exécute :

```bash
git init
git add .
git commit -m "🚀 Premier commit — moniteur wplace.live"
git branch -M main
git remote add origin https://github.com/TON_PSEUDO/wplace-monitor.git
git push -u origin main
```

> Remplace `TON_PSEUDO` par ton nom d'utilisateur GitHub.

### Étape 4 — Configurer le secret Discord

1. Sur GitHub, va dans ton dépôt → **Settings** → **Secrets and variables** → **Actions**.
2. Clique **New repository secret**.
3. Nom : `DISCORD_WEBHOOK_URL`
4. Valeur : colle l'URL du webhook copiée à l'étape 1.
5. Clique **Add secret**.

### Étape 5 — (Optionnel) Configurer les variables

Si tu veux modifier la zone surveillée ou le seuil **sans toucher au code** :

1. Toujours dans **Settings** → **Secrets and variables** → **Actions** → onglet **Variables**.
2. Clique **New repository variable** pour chacune que tu veux modifier :

| Variable | Valeur par défaut | Description |
|---|---|---|
| `TILE_X` | `1054` | Coordonnée X de la tuile |
| `TILE_Y` | `736` | Coordonnée Y de la tuile |
| `ZONE_X_MIN` | `18` | Bord gauche de la zone (pixels) |
| `ZONE_X_MAX` | `143` | Bord droit de la zone (pixels) |
| `ZONE_Y_MIN` | `0` | Bord haut de la zone (pixels) |
| `ZONE_Y_MAX` | `999` | Bord bas de la zone (pixels) |
| `CHANGE_THRESHOLD` | `3.0` | Seuil de détection (%) |
| `COLOR_TOLERANCE` | `10` | Tolérance de couleur (0-255) |

> ⚠️ **Tu n'es pas obligé de créer ces variables.** Si elles n'existent pas (ou sont vides), le code utilise les valeurs par défaut indiquées ci-dessus.

### Étape 6 — Activer le workflow et premier test

1. Va dans l'onglet **Actions** de ton dépôt.
2. GitHub peut te demander d'activer les workflows — clique **"I understand my workflows, go ahead and enable them"**.
3. Dans la barre de gauche, clique sur **"wplace.live — Moniteur anti-grief"**.
4. Clique le bouton **"Run workflow"** → **"Run workflow"** (branche `main`).
5. Attends ~30 secondes, puis regarde les logs du run.
6. Au **premier run** : pas d'alerte (il n'y a pas encore de référence). L'image `reference.png` sera committée automatiquement.
7. Au **deuxième run** (5 min plus tard ou re-run manuel) : comparaison effective. Si quelqu'un a modifié la zone, tu reçois l'alerte Discord ! 🎉

---

## ⚙️ Comment ça marche

```
┌─────────────┐     ┌────────────────┐     ┌─────────────────┐
│ wplace.live │────▶│  Découpe zone  │────▶│ Compare avec    │
│ tuile PNG   │     │  surveillée    │     │ reference.png   │
└─────────────┘     └────────────────┘     └────────┬────────┘
                                                    │
                                          ┌─────────▼─────────┐
                                          │ Changement > seuil │
                                          └─────────┬─────────┘
                                           Non │         │ Oui
                                               ▼         ▼
                                          ┌────────┐ ┌────────────┐
                                          │  RAS   │ │ 🚨 Discord │
                                          └────────┘ │  + images  │
                                                     └────────────┘
                                               │         │
                                               ▼         ▼
                                        ┌─────────────────────┐
                                        │ 💾 Sauvegarder      │
                                        │ nouvelle référence   │
                                        └─────────────────────┘
```

---

## ⚠️ Limites à connaître

### Délai du cron GitHub Actions
- Le cron GitHub Actions est **indicatif** : `*/5 * * * *` signifie "environ toutes les 5 minutes", mais en pratique GitHub peut ajouter **1 à 15 minutes de délai** en période de forte charge. Ce n'est pas du temps réel.
- Pour les dépôts inactifs, GitHub peut **désactiver le cron** après 60 jours sans activité. Il suffit de faire un commit ou de relancer un run manuel pour le réactiver.

### Quota GitHub Actions (plan gratuit)
- **2 000 minutes par mois** sur les dépôts privés (illimité sur les dépôts publics).
- Chaque run dure environ **30-60 secondes**. Avec un run toutes les 5 min, ça fait ~8 640 min/mois → **dépasse le quota en privé** !
- **Solution** : rendre le dépôt **public** (gratuit et illimité), ou augmenter l'intervalle à `*/10` ou `*/15` minutes dans le workflow.

### Ajuster le seuil
- **Trop d'alertes ?** → Augmente `CHANGE_THRESHOLD` (ex: `5.0` ou `10.0`) et/ou augmente `COLOR_TOLERANCE` (ex: `20` ou `30`).
- **Pas assez d'alertes ?** → Diminue `CHANGE_THRESHOLD` (ex: `1.0`) et/ou diminue `COLOR_TOLERANCE` (ex: `5`).
- Le `COLOR_TOLERANCE` filtre les micro-variations dues à la compression JPEG/PNG ou aux artefacts réseau. Valeur de `10` = bon compromis.

### Conflits de commit
- Si deux runs GitHub Actions se chevauchent et essaient de committer `reference.png` en même temps, le push peut échouer. C'est rare (chaque run dure < 1 min) et non critique — le run suivant repartira de la dernière référence committée.

---

## 📜 Licence

Projet personnel — utilise-le comme tu veux.
