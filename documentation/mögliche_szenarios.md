Bei OpenWhisk werden Warme container standardmäßig nach 10 Minuten Inaktivität heruntergefahren. Dies führt zu sogenannten "Cold Starts", wenn eine Funktion nach einer Inaktivitätsperiode erneut aufgerufen wird. Je nach Nutzungsszenario können die Auswirkungen von Cold Starts variieren.


| Szenario               | Beschreibung                               | Erwartung bei OpenWhisk                        |
| ---------------------- | ------------------------------------------ | ---------------------------------------------- |
| Einzel-Intervalle  | Alle 15 Minuten ein Bild                   | Cold Start bei jedem Aufruf       |
| Kurz-Intervalle    | Alle 2 Minuten                             | Nur Warm Starts, sehr niedrige Latenz          |
| Batch-Job          | 100 Bilder gleichzeitig                   | Auto-Scaling, sehr kurze Gesamtdauer           |
| Dauerlast / Stream | Kontinuierlicher Datenstrom                | Warm, stabil, aber teurer (dauerhafte Nutzung) |
| Unregelmäßige Last | Zufällige Events (z. B. 5–20 Min Abstände) | Mischverhalten – teils Cold, teils Warm Starts |

