# 🧬 KG-System (Knowledge Graph Taste Hypothesis System)

Ein robustes, modulares KI-System zur Generierung, Validierung und Bewertung von Geschmackshypothesen.

## 📋 Übersicht

Das KG-System implementiert eine vollständige Pipeline zur automatischen Erstellung und Bewertung von Geschmackshypothesen basierend auf einem Knowledge Graph. Das System besteht aus vier Hauptmodulen:

- **HG** (Hypothesen-Generierung): Generiert neue Geschmackshypothesen
- **ISV** (In-Silico-Validierung): Validiert Hypothesen durch Simulation
- **KD** (Kritische Bewertung): Bewertet die Qualität der Hypothesen
- **LAR** (Lernen und Argumentieren): Koordiniert das System und lernt aus Feedback

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    KG-System                                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │   HG    │───▶│   ISV   │───▶│   KD    │───▶│   LAR   │  │
│  │ (Gen.)  │    │ (Valid.)│    │ (Eval.) │    │ (Learn) │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┤
│  │                Web API (FastAPI)                        │
│  │                Monitoring Dashboard                     │
│  │                Database (SQLAlchemy)                    │
│  │                Configuration & Logging                  │
│  └─────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Schnellstart

### Installation

```bash
# Virtuelle Umgebung erstellen
python -m venv .venv
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### System starten

```bash
# API-Server starten
python -m uvicorn kg_api:app --reload

# System läuft auf: http://localhost:8000
# Dashboard: http://localhost:8000/dashboard
# API-Docs: http://localhost:8000/docs
```

### Demo ausführen

```bash
# Vollständige Demo
python demo.py

# Einfache Tests
python test_simple.py
python test_complete.py
```

## 📊 Aktuelle Features

✅ **Vollständige Pipeline**: HG → ISV → KD → LAR  
✅ **REST API**: FastAPI mit OpenAPI/Swagger  
✅ **Monitoring Dashboard**: Real-time Überwachung  
✅ **Datenbankintegration**: SQLAlchemy ORM  
✅ **Asynchrone Verarbeitung**: Concurrent processing  
✅ **Strukturiertes Logging**: JSON-Format  
✅ **Input-Validierung**: Pydantic-basiert  
✅ **Umfassende Tests**: Alle Module getestet  

## 🌐 API-Endpoints

- `GET /status` - Systemstatus
- `POST /hypothese/erstellen` - Neue Hypothese erstellen
- `GET /hypothese/status/{id}` - Status einer Hypothese
- `GET /hypothese/ergebnis/{id}` - Ergebnis einer Hypothese
- `GET /metriken` - Systemmetriken
- `GET /dashboard` - Monitoring-Dashboard

## 📈 Performance

- **Verarbeitungszeit**: ~2-3 Sekunden pro Hypothese
- **Erfolgsrate**: ~89% Approval-Rate
- **Durchsatz**: Mehrere Hypothesen parallel
- **Speicher**: ~100MB RAM im Betrieb

## 📁 Projektstruktur

```
KG/
├── main.py                 # Haupteinstiegspunkt
├── kg_api.py              # FastAPI Web-Server
├── demo.py                # Demonstration
├── config.json            # Konfiguration
├── requirements.txt       # Abhängigkeiten
├── README.md             # Diese Datei
├── FINAL_STATUS_REPORT.md # Vollständiger Statusbericht
├── kg/                   # Hauptmodule
│   ├── schemas.py        # Datenmodelle (Pydantic)
│   ├── database.py       # Datenbankmodelle (SQLAlchemy)
│   ├── monitoring.py     # Monitoring-System
│   ├── modules/          # Core-Module
│   │   ├── hg/          # Hypothesen-Generierung
│   │   ├── isv/         # In-Silico-Validierung
│   │   ├── kd/          # Kritische Bewertung
│   │   └── lar/         # Lernen und Argumentieren
│   └── utils/           # Hilfswerkzeuge
│       ├── config.py    # Konfigurationsmanagement
│       └── logging_config.py # Logging-Setup
├── test_simple.py        # Einfache Tests
├── test_complete.py      # Vollständige Tests
└── .venv/               # Virtuelle Umgebung
```

## 🔧 Verwendung

### API-Beispiel

```python
import requests

# Neue Hypothese erstellen
response = requests.post("http://localhost:8000/hypothese/erstellen", json={
    "targetProfile": ["ERDIG", "SÜSS", "FRUCHTIG"],
    "exclude": ["Capsaicin"],
    "signal": "CREATE_NEW",
    "priority": "HIGH"
})

task_id = response.json()["taskID"]

# Status prüfen
status = requests.get(f"http://localhost:8000/hypothese/status/{task_id}")
print(status.json())
```

### Direkte Verwendung

```python
import asyncio
from kg.modules.lar.lar_agent import LARAgent

async def main():
    lar = LARAgent()
    await lar.initialize()
    
    result = await lar.process_signal({
        "taskID": "DEMO-001",
        "signal": "CREATE_NEW",
        "constraints": {"targetProfile": ["ERDIG", "SÜSS"]}
    })
    
    print(result)

asyncio.run(main())
```

## 🧪 Testing

```bash
# Alle Tests
python -m pytest

# Einzelne Tests
python test_simple.py
python test_complete.py

# Demo ausführen
python demo.py
```

## 📚 Weitere Ressourcen

- **API-Dokumentation**: http://localhost:8000/docs
- **Monitoring-Dashboard**: http://localhost:8000/dashboard
- **Vollständiger Statusbericht**: `FINAL_STATUS_REPORT.md`
- **Atomare Aufgaben**: `aufgabenliste.md`

---

**Status**: ✅ Vollständig implementiert und getestet  
**Version**: 1.0.0  
**API**: http://localhost:8000  
**Dashboard**: http://localhost:8000/dashboard
