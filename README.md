## Erpnext Oci

Open Catalog Interface for ERPNext

#### OCI VALIDATE / Preisabfrage

Im OCI-Partner die Option **Validate** aktivieren. URL, GET/POST,
Benutzername, Passwort und Zusatzparameter werden wie beim Katalogaufruf verwendet.
Der Lieferantenkatalog muss `FUNCTION=VALIDATE` unter dieser URL unterstuetzen.
Das Feld **Validate Quantity Field** bestimmt den Parameternamen fuer die Menge.
Der Standardwert ist `QUANTITY`; beim Siemens-OCI-5-Partner muss es gemaess
Siemens-Formular `Quantity` lauten.

Auf der Seite **OCI Partners** oder im gespeicherten Partnerformular
**Preisabfrage** oeffnen. Lieferant, Lieferanten-Artikelnummer (`PRODUCTID`)
und Menge eingeben und **Preis abfragen** starten. Optional einen vorhandenen
ERPNext-Artikel auswaehlen: Seine Lieferanten-Artikelnummer wird fuer den
gewaehlten Lieferanten vorbelegt. Falls der Katalog eine andere Produkt-ID
erwartet, diese im Feld Lieferanten-Artikelnummer eintragen.

Die Anfrage sendet die OCI-Verbindungsparameter aus den Partnereinstellungen,
`FUNCTION=VALIDATE`, `PRODUCTID` und `QUANTITY`. Wie beim normalen OCI-Aufruf
werden auch `HOOK_URL` (Rücksprung auf die aktuelle ERPNext-Site) und `~caller`
(OCI-Partnername) mitgesendet.
Unterstuetzt werden OCI-Eingabefelder in einer HTML-Antwort sowie
URL-kodierte OCI-Felder. Angezeigt werden Preis, Waehrung, Preiseinheit
und Mengeneinheit; zusaetzliche Preisfelder werden aus dem Partner-Mapping
(`Item-Price`, erste Position) gelesen. Ein Preis gilt fuer die zurueckgegebene
Preiseinheit, nicht zwingend fuer ein einzelnes Stueck.

Die Abfrage speichert keine Artikel, Artikelpreise oder Warenkoerbe und fuehrt
keine Lieferantenskripte aus. Kataloge, die JavaScript oder einen interaktiven
Login voraussetzen, benoetigen eine lieferantenspezifische Erweiterung.
Zugriff haben Purchase User, Purchase Manager und System Manager mit
Leseberechtigung auf den jeweiligen Lieferanten. Zugangsdaten bleiben serverseitig.

#### Monatliche Einkaufspreispruefung

Im OCI-Partner **Validate** aktivieren und **Monthly Purchase Price Update**
einschalten. Die Preisliste wird aus genau einer `Item-Price`-Zuordnung des
Partners genommen; die Anfrage verwendet **Price Check Quantity**. Die Artikel
werden aus `Item Supplier` fuer den Partner-Lieferanten gelesen. Der Monatslauf
startet am ersten Tag des Monats. **Check Purchase Prices** startet denselben
Lauf manuell im Hintergrund.

Preisabweichungen erzeugen ab dem Laufdatum eine neue lieferantenspezifische
`Item Price`-Gueltigkeit; der vorherige Siemens-Preis wird am Vortag beendet.
Generische Preise bleiben unangetastet. Nicht abrufbare Preise und Fehler bei
der Aktualisierung werden im Desk-**Error Log** mit Artikel und Fehlermeldung
protokolliert. Der Scheduler muss aktiviert sein.

#### License

MIT