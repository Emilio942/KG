import asyncio
import logging
import json
from kg.modules.lar.lar_agent import LARAgent

# Setup logging to see the mathematical steps
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_pipeline():
    print("\n" + "="*60)
    print("🧪 TEST: NEUE MATHEMATISCHE ENTDECKUNGS-PIPELINE")
    print("="*60)
    
    # Initialize the core orchestrator
    lar = LARAgent()
    await lar.initialize()
    
    # Define a signal for a new discovery
    # We want something sweet and fruity, but excluding certain molecules
    signal = {
        "taskID": "DISCOVERY-TASK-001",
        "signal": "CREATE_NEW",
        "constraints": {
            "targetProfile": ["SÜSS", "FRUCHTIG"],
            "exclude": ["Capsaicin"]
        }
    }
    
    print(f"\nSende Signal: {json.dumps(signal, indent=2)}")
    
    # Process the signal
    result = await lar.process_signal(signal)
    
    print("\n" + "-"*60)
    print("✅ ERGEBNIS DER MATHEMATISCHEN GENERIERUNG")
    print("-"*60)
    print(f"Hypothese ID: {result.hypotheseID}")
    print(f"Novelty Score: {result.beweis.noveltyScore:.4f}")
    print(f"Herleitung: {result.beweis.herleitung}")
    
    print("\nKomponenten:")
    for comp in result.hypothese.komponenten:
        print(f"  - {comp.name}: {comp.konzentration*100:.2f}%")
    
    # Validate concentration sum (OT-VAE property)
    total_conc = sum(c.konzentration for c in result.hypothese.komponenten)
    print(f"\nGesamtkonzentration: {total_conc*100:.2f}% (Mathematisch korrekt: {abs(total_conc-1.0) < 1e-5})")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
