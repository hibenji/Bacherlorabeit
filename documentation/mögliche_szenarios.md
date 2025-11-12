Bei OpenWhisk werden Warme container standardmäßig nach 10 Minuten Inaktivität heruntergefahren. Dies führt zu sogenannten "Cold Starts", wenn eine Funktion nach einer Inaktivitätsperiode erneut aufgerufen wird. Je nach Nutzungsszenario können die Auswirkungen von Cold Starts variieren.


| Szenario               | Beschreibung                               | Erwartung bei OpenWhisk                        |
| ---------------------- | ------------------------------------------ | ---------------------------------------------- |
| Einzel-Intervalle  | Alle 15 Minuten ein Bild                   | Cold Start bei jedem Aufruf       |
| Kurz-Intervalle    | Alle 2 Minuten                             | Nur Warm Starts, sehr niedrige Latenz          |
| Batch-Job          | 100 Bilder gleichzeitig                   | Auto-Scaling, sehr kurze Gesamtdauer           |
| Dauerlast / Stream | Kontinuierlicher Datenstrom                | Warm, stabil, aber teurer (dauerhafte Nutzung) |
| Unregelmäßige Last | Zufällige Events (z. B. 5–20 Min Abstände) | Mischverhalten – teils Cold, teils Warm Starts |

Beispiel warm/cold starts aus OpenWhisk Logs:
```
minikube@OpenWhisk:~/openwhisk-deploy-kube/helm/openwhisk$ wsk activation list -l 15
Datetime            Activation ID                    Kind     Start Duration   Status  Entity
2025-11-12 16:53:57 6b952d08e3274846952d08e3275846dc blackbox warm  57ms       success benji/postprocess:0.0.2
2025-11-12 16:53:57 2c2a69b53f084ca2aa69b53f082ca27a blackbox warm  208ms      success benji/detect:0.0.2
2025-11-12 16:53:57 945e764e134143309e764e134173303c blackbox warm  111ms      success benji/resize:0.0.2
2025-11-12 16:53:57 8ee442f5428f4bb4a442f5428fdbb4c5 sequence warm  431ms      success benji/yolo-seq:0.0.2

2025-11-12 16:53:43 deed7b64b51b46bbad7b64b51ba6bb83 blackbox cold  769ms      success benji/postprocess:0.0.2
2025-11-12 16:53:39 87de4989d3624d7d9e4989d3623d7db3 blackbox cold  1.036s     success benji/detect:0.0.2
2025-11-12 16:53:35 0334fed6c3354bd2b4fed6c335fbd2cc blackbox cold  744ms      success benji/resize:0.0.2
2025-11-12 16:53:31 3f08152aa854446688152aa854546619 sequence warm  12.169s    success benji/yolo-seq:0.0.2

2025-11-12 16:41:54 4238d55d71144f70b8d55d71140f7061 blackbox cold  729ms      success benji/postprocess:0.0.2
2025-11-12 16:41:50 a19de6fcce3c4e709de6fcce3c7e7018 blackbox cold  1.073s     success benji/detect:0.0.2
2025-11-12 16:41:47 ea6091994da049e5a091994da0a9e56d blackbox cold  708ms      success benji/resize:0.0.2
2025-11-12 16:41:44 5d23c4b374ff4396a3c4b374ffc396b0 sequence warm  11.234s    success benji/yolo-seq:0.0.2
```

Warm braucht die Pipeline ca. 0.4s, Cold Starts ca. 11-12s.