# TCG Restock/Preorder Watcher (Schweiz)

Überwacht Schweizer Online-Shops auf **Pokémon**- und **Dragon Ball**-TCG-Produkte
und schickt dir eine Discord-Nachricht, sobald etwas restocked wird oder als
Preorder online geht.

## Wie es funktioniert

- `config.json` – Liste der Shops + Suchbegriffe.
- `checker.py` – prüft jeden Shop, vergleicht mit dem letzten bekannten Zustand
  (`state.json`) und meldet nur **Änderungen** (nicht jedes Mal alles).
- `.github/workflows/watch.yml` – lässt das Skript alle 15 Minuten automatisch
  auf GitHub laufen (kostenlos, kein eigener PC nötig).

Zwei Shop-Typen werden unterstützt:

1. **`shopify`** – nutzt die öffentliche `/products.json`-API des Shops.
   Sehr zuverlässig, keine Anpassung an HTML nötig. Viele kleinere
   Schweizer TCG-Shops laufen auf Shopify.
2. **`custom`** – für Shops ohne Shopify. Hier müssen CSS-Selektoren in
   `config.json` eingetragen werden (siehe Beispiel-Eintrag). Das erfordert
   einmalig, dass jemand kurz in die Seitenstruktur des jeweiligen Shops
   reinschaut (Rechtsklick → "Untersuchen" im Browser).

## Setup

### 1. Discord-Webhook erstellen

1. Discord-Server öffnen (oder einen neuen erstellen – geht in 10 Sekunden,
   auch nur für dich alleine).
2. Rechtsklick auf den Kanal, in dem die Meldungen ankommen sollen
   → **Kanal bearbeiten → Integrationen → Webhooks → Neuer Webhook**.
3. Dem Webhook einen Namen geben (z. B. "TCG Watcher"), dann auf
   **Webhook-URL kopieren** klicken.
   Die URL sieht aus wie:
   `https://discord.com/api/webhooks/123456789/AbCdEfGhIjKlMnOp...`
4. Diese URL brauchst du im nächsten Schritt als Secret.

### 2. Repository auf GitHub anlegen

1. Neues (privates) GitHub-Repo erstellen.
2. Diesen Ordner hochladen (z. B. via GitHub Desktop, oder `git push`).
3. Unter **Settings → Secrets and variables → Actions** ein Secret anlegen:
   - `DISCORD_WEBHOOK_URL` mit der URL aus Schritt 1
4. Unter **Actions** den Workflow einmal manuell starten
   ("Run workflow"), um zu testen.

Danach läuft es automatisch alle 15 Minuten.

### 3. Lokal testen (optional)

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python checker.py
```

## Aktuell konfigurierte Shops

- **Cardmaniac.ch** – Shopify, funktioniert direkt
- **Pikaversum.ch** – Shopify, funktioniert direkt
- **The Uncommon Shop (theuncommonshop.ch)** – WooCommerce, über Kategorie-Seiten
- **JapHunter.ch** – Shopify, funktioniert direkt
- **PokeAlp.ch** – Shopify, funktioniert direkt

**Nicht enthalten:** Manor.ch, Coop.ch, Galaxus.ch, Brack.ch und Amazingtoys.ch
blockieren automatisierte Zugriffe explizit über ihre `robots.txt`. Das wird
hier respektiert – diese Shops lassen sich mit diesem Tool nicht überwachen.

## Shops hinzufügen

In `config.json` einfach einen neuen Eintrag in `"shops"` hinzufügen.
Am einfachsten: prüfen, ob der Shop Shopify nutzt. Das lässt sich testen,
indem man `https://SHOPDOMAIN.ch/products.json` im Browser öffnet — kommt
eine JSON-Liste mit Produkten zurück, funktioniert der `shopify`-Typ direkt,
ohne weitere Anpassung.

Falls nicht (z. B. Digitec, Manor, Coop, individuelle Shop-Systeme), braucht
es den `custom`-Typ mit CSS-Selektoren. Schick mir einfach die Shop-URL,
dann schaue ich mir die Struktur an und ergänze den Eintrag.

## Wichtiger Hinweis

- Bitte die Abfrage-Frequenz moderat halten (15 Min ist ein guter Kompromiss),
  um Shops nicht unnötig zu belasten oder eine IP-Sperre zu riskieren.
- Manche Shops verbieten automatisiertes Abfragen in ihren AGB — im Zweifel
  deren Nutzungsbedingungen kurz prüfen.
