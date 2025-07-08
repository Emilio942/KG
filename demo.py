#!/usr/bin/env python3
"""
KG-System Demonstration Script
==============================

This script demonstrates the complete capabilities of the KG-System:
1. System startup and initialization
2. API server running
3. Hypothesis generation via API
4. Real-time monitoring
5. Results visualization

Usage:
    python demo.py
"""

import asyncio
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"🧬 {title}")
    print("="*60)

def print_success(message: str):
    """Print a success message"""
    print(f"✅ {message}")

def print_info(message: str):
    """Print an info message"""
    print(f"ℹ️  {message}")

def print_error(message: str):
    """Print an error message"""
    print(f"❌ {message}")

def format_json(data: Dict[str, Any]) -> str:
    """Format JSON data for display"""
    return json.dumps(data, indent=2, ensure_ascii=False)

def test_api_connection(base_url: str = "http://localhost:8000") -> bool:
    """Test if the API is running"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def demonstrate_system():
    """Demonstrate the complete KG-System"""
    
    print_header("KG-SYSTEM DEMONSTRATION")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "http://localhost:8000"
    
    # 1. Check system status
    print_info("1. Checking system status...")
    if not test_api_connection(base_url):
        print_error("API server is not running!")
        print("Please start the server with: python -m uvicorn kg_api:app --reload")
        return False
    
    print_success("API server is running")
    
    # 2. Get system status
    print_info("2. Getting system status...")
    response = requests.get(f"{base_url}/status")
    if response.status_code == 200:
        status = response.json()
        print_success(f"System running with {len(status['activeModules'])} modules")
        print(f"   Active modules: {', '.join(status['activeModules'])}")
        print(f"   Total processed: {status['totalProcessed']}")
        print(f"   Success rate: {status['successRate']:.1f}%")
    else:
        print_error(f"Status check failed: {response.status_code}")
        return False
    
    # 3. Create a new hypothesis
    print_info("3. Creating new hypothesis...")
    hypothesis_request = {
        "targetProfile": ["ERDIG", "SÜSS", "FRUCHTIG"],
        "exclude": ["Capsaicin"],
        "signal": "CREATE_NEW",
        "priority": "HIGH"
    }
    
    response = requests.post(f"{base_url}/hypothese/erstellen", json=hypothesis_request)
    if response.status_code == 200:
        result = response.json()
        task_id = result["taskID"]
        print_success(f"Hypothesis creation started: {task_id}")
        print(f"   Polling URL: {result['polling_url']}")
    else:
        print_error(f"Hypothesis creation failed: {response.status_code}")
        return False
    
    # 4. Monitor hypothesis processing
    print_info("4. Monitoring hypothesis processing...")
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{base_url}/hypothese/status/{task_id}")
        if response.status_code == 200:
            status = response.json()
            print(f"   Status: {status['status']}")
            
            if status['status'] == 'SUCCESS':
                print_success("Hypothesis processing completed!")
                break
            elif status['status'] == 'FAILED':
                print_error(f"Hypothesis processing failed: {status.get('error', 'Unknown error')}")
                return False
            else:
                print("   Processing...")
                time.sleep(2)
        else:
            print_error(f"Status check failed: {response.status_code}")
            return False
        
        attempt += 1
    
    if attempt >= max_attempts:
        print_error("Hypothesis processing timed out")
        return False
    
    # 5. Get full results
    print_info("5. Getting full results...")
    response = requests.get(f"{base_url}/hypothese/ergebnis/{task_id}")
    if response.status_code == 200:
        result = response.json()
        print_success("Full results retrieved!")
        
        # Display hypothesis details
        hypothesis = result["hypothese"]
        print(f"\\n📋 HYPOTHESIS: {hypothesis['hypotheseID']}")
        print(f"   Components: {len(hypothesis['komponenten'])}")
        for comp in hypothesis['komponenten']:
            print(f"   - {comp['name']}: {comp['konzentration']}")
        print(f"   Novelty Score: {hypothesis['noveltyScore']}")
        
        # Display simulation results
        simulation = result["simulation"]
        print(f"\\n🧪 SIMULATION: {simulation['method']}")
        print(f"   Confidence: {simulation['confidence']}")
        print(f"   Duration: {simulation['duration']}s")
        print("   Taste Profile:")
        for taste, data in simulation['grundgeschmack'].items():
            print(f"   - {taste.title()}: {data['score']:.2f}")
        
        # Display evaluation
        evaluation = result["bewertung"]
        print(f"\\n⚖️  EVALUATION: {evaluation['verdict']}")
        print(f"   Overall Score: {evaluation['gesamtScore']}")
        print(f"   Taste Harmony: {evaluation['geschmacksharmonie']}")
        print(f"   Aroma Harmony: {evaluation['aromaharmonie']}")
        print(f"   Confirmed Novelty: {evaluation['bestaetigteNeuheit']}")
        
        if evaluation['verdict'] == 'APPROVED':
            print("\\n✅ HYPOTHESIS SUCCESSFULLY APPROVED!")
        else:
            print("\\n❌ HYPOTHESIS REJECTED")
    else:
        print_error(f"Results retrieval failed: {response.status_code}")
        return False
    
    # 6. Get system metrics
    print_info("6. Getting system metrics...")
    response = requests.get(f"{base_url}/metriken")
    if response.status_code == 200:
        metrics = response.json()
        print_success("System metrics retrieved!")
        
        # Group metrics by module
        module_metrics = {}
        for metric in metrics:
            module = metric['module']
            if module not in module_metrics:
                module_metrics[module] = {}
            module_metrics[module][metric['metrikName']] = metric['wert']
        
        print("\\n📊 MODULE PERFORMANCE:")
        for module, metrics in module_metrics.items():
            print(f"   {module}: {metrics.get('erfolgsrate', 0)}% success, {metrics.get('durchschnittliche_verarbeitungszeit', 0)}s avg")
    else:
        print_error(f"Metrics retrieval failed: {response.status_code}")
    
    # 7. Show dashboard info
    print_info("7. Monitoring dashboard...")
    print_success("Dashboard is available at: http://localhost:8000/dashboard")
    print_success("API documentation at: http://localhost:8000/docs")
    
    print_header("DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("🎉 The KG-System is fully operational!")
    print("\\nKey URLs:")
    print(f"   • API: {base_url}")
    print(f"   • Dashboard: {base_url}/dashboard")
    print(f"   • Documentation: {base_url}/docs")
    print("\\nThe system is ready for production use!")
    
    return True

def main():
    """Main function"""
    try:
        success = demonstrate_system()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n\\nDemo interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\\n\\nDemo failed with error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
