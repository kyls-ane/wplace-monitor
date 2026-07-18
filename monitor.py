"""
wplace.live — Moniteur de zone pixel art avec alerte Discord.

Ce script :
1. Télécharge la tuile PNG depuis le backend de wplace.live
2. Découpe la zone surveillée (rectangle configurable)
3. Compare pixel par pixel avec l'image de référence précédente
4. Si le % de pixels modifiés dépasse le seuil → alerte Discord (webhook)
5. Sauvegarde la nouvelle image comme référence pour le prochain run
"""

import os
import sys
import io
import requests
from PIL import Image
import numpy as np


# ──────────────────────────────────────────────────────────────
# Configuration (variables d'environnement avec valeurs par défaut)
# GitHub Actions injecte "" (chaîne vide) pour les variables non
# définies, donc on utilise `or` pour retomber sur la valeur par défaut.
# ──────────────────────────────────────────────────────────────

TILE_X = int(os.environ.get("TILE_X") or "1054")
TILE_Y = int(os.environ.get("TILE_Y") or "736")
TILE_URL = f"https://backend.wplace.live/files/s0/tiles/{TILE_X}/{TILE_Y}.png"

# Zone à surveiller dans la tuile (coordonnées pixels)
ZONE_X_MIN = int(os.environ.get("ZONE_X_MIN") or "18")
ZONE_X_MAX = int(os.environ.get("ZONE_X_MAX") or "143")
ZONE_Y_MIN = int(os.environ.get("ZONE_Y_MIN") or "0")
ZONE_Y_MAX = int(os.environ.get("ZONE_Y_MAX") or "999")

# Seuil de détection (% de pixels modifiés pour déclencher l'alerte)
CHANGE_THRESHOLD = float(os.environ.get("CHANGE_THRESHOLD") or "0.5")

# Tolérance de couleur par canal (0-255) pour ignorer le bruit
# Un pixel est considéré "changé" si au moins un canal RGB diffère
# de plus de COLOR_TOLERANCE par rapport à la référence.
COLOR_TOLERANCE = int(os.environ.get("COLOR_TOLERANCE") or "5")

# Webhook Discord (secret, JAMAIS en dur)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# Chemin de l'image de référence (conservée entre les runs via git)
REFERENCE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "reference.png"
)


def download_tile() -> Image.Image:
    """Télécharge la tuile depuis le backend wplace.live."""
    print(f"📥 Téléchargement de la tuile : {TILE_URL}")
    resp = requests.get(TILE_URL, timeout=30)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


def crop_zone(tile: Image.Image) -> Image.Image:
    """Découpe la zone surveillée dans la tuile.

    PIL crop utilise (left, upper, right+1, lower+1) pour inclure
    les pixels aux coordonnées max.
    """
    box = (ZONE_X_MIN, ZONE_Y_MIN, ZONE_X_MAX + 1, ZONE_Y_MAX + 1)
    cropped = tile.crop(box)
    print(
        f"✂️  Zone découpée : x=[{ZONE_X_MIN}..{ZONE_X_MAX}], "
        f"y=[{ZONE_Y_MIN}..{ZONE_Y_MAX}] → {cropped.size[0]}×{cropped.size[1]} px"
    )
    return cropped


def compare_images(current: Image.Image, reference: Image.Image) -> float:
    """Compare deux images et retourne le pourcentage de pixels modifiés.

    Un pixel est considéré "modifié" si la différence absolue sur au
    moins un canal RGB dépasse COLOR_TOLERANCE.
    """
    if current.size != reference.size:
        print("⚠️  Taille différente → considéré comme 100% de changement")
        return 100.0

    arr_cur = np.array(current, dtype=np.int16)
    arr_ref = np.array(reference, dtype=np.int16)

    # Différence absolue par canal, puis max par pixel
    diff = np.abs(arr_cur - arr_ref)  # shape: (H, W, 3)
    max_diff_per_pixel = diff.max(axis=2)  # shape: (H, W)

    # Un pixel est "changé" si sa diff max dépasse la tolérance
    changed_mask = max_diff_per_pixel > COLOR_TOLERANCE
    num_changed = int(changed_mask.sum())
    total = changed_mask.size
    pct = (num_changed / total) * 100.0

    print(
        f"🔍 Comparaison : {num_changed}/{total} pixels modifiés "
        f"({pct:.2f}%) — seuil = {CHANGE_THRESHOLD}%"
    )
    return pct


def send_discord_alert(
    pct: float, before_img: Image.Image, after_img: Image.Image
) -> None:
    """Envoie une alerte Discord via webhook avec les images avant/après."""
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL non défini — alerte ignorée !")
        return

    # Préparer les images en mémoire (PNG)
    buf_before = io.BytesIO()
    before_img.save(buf_before, format="PNG")
    buf_before.seek(0)

    buf_after = io.BytesIO()
    after_img.save(buf_after, format="PNG")
    buf_after.seek(0)

    # Construire le message
    message = (
        f"🚨 **Alerte wplace.live — Griefing détecté !**\n"
        f"**{pct:.2f}%** des pixels de la zone surveillée ont changé "
        f"(seuil : {CHANGE_THRESHOLD}%).\n"
        f"Tuile `({TILE_X}, {TILE_Y})` — Zone "
        f"x=[{ZONE_X_MIN}..{ZONE_X_MAX}], y=[{ZONE_Y_MIN}..{ZONE_Y_MAX}]"
    )

    # Envoi multipart (texte + fichiers)
    resp = requests.post(
        DISCORD_WEBHOOK_URL,
        data={"content": message},
        files=[
            ("file1", ("avant.png", buf_before, "image/png")),
            ("file2", ("apres.png", buf_after, "image/png")),
        ],
        timeout=30,
    )
    resp.raise_for_status()
    print("✅ Alerte Discord envoyée !")


def main() -> None:
    # 1. Télécharger la tuile et découper la zone
    tile = download_tile()
    current_zone = crop_zone(tile)

    # 2. Charger la référence (si elle existe)
    if os.path.isfile(REFERENCE_PATH):
        reference_zone = Image.open(REFERENCE_PATH).convert("RGB")
        print(f"📂 Référence chargée : {REFERENCE_PATH}")
    else:
        # Premier run : pas de référence, on sauvegarde et on sort
        current_zone.save(REFERENCE_PATH)
        print(
            "🆕 Aucune référence trouvée — image initiale sauvegardée. "
            "Le prochain run pourra comparer."
        )
        return

    # 3. Comparer
    pct = compare_images(current_zone, reference_zone)

    # 4. Alerter si nécessaire
    if pct >= CHANGE_THRESHOLD:
        print("🚨 Changement significatif détecté → envoi de l'alerte Discord")
        send_discord_alert(pct, before_img=reference_zone, after_img=current_zone)
    else:
        print("✅ Pas de changement significatif — rien à signaler.")

    # 5. Sauvegarder la nouvelle référence pour le prochain run
    current_zone.save(REFERENCE_PATH)
    print(f"💾 Nouvelle référence sauvegardée : {REFERENCE_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"❌ Erreur fatale : {exc}", file=sys.stderr)
        sys.exit(1)
