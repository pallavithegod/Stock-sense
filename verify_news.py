
import sys
import os
sys.path.append(os.getcwd())

try:
    from app import app, quantum_ai, QuantumNewsAI
    
    print("[OK] App imported successfully")
    
    # Check Endpoints
    # app.url_map returns rules object
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    
    if '/api/news/market' in rules:
        print("[OK] /api/news/market endpoint exists")
    else:
        print("[FAIL] /api/news/market endpoint MISSING")
        
    found_symbol = False
    for r in rules:
        if '/api/news/symbol/' in r:
             found_symbol = True
             print(f"[OK] Found symbol endpoint: {r}")
             break
    
    if not found_symbol:
         # Maybe exactly /api/news/symbol/<symbol>
         if '/api/news/symbol/<symbol>' in rules:
             print("[OK] /api/news/symbol endpoint exists")
         else:
             print("[FAIL] /api/news/symbol endpoint MISSING")
        
    # Check Foresight Injection
    if hasattr(app, 'foresight_system'):
        print("[OK] Foresight System attached to app")
        if hasattr(app.foresight_system, 'news_ai'):
             news_ai = app.foresight_system.news_ai
             if isinstance(news_ai, QuantumNewsAI):
                 print("[OK] QuantumNewsAI injected into Foresight System correctly")
             else:
                 print(f"[FAIL] app.foresight_system.news_ai is {type(news_ai)}")
        else:
            print("[FAIL] app.foresight_system has NO news_ai attribute")
    else:
        print("[FAIL] Foresight System NOT attached to app")
        
    # Check QuantumAI injection
    if hasattr(quantum_ai, 'quantum_news'):
        q_news = quantum_ai.quantum_news
        if isinstance(q_news, QuantumNewsAI):
            print("[OK] QuantumNewsAI injected into QuantumAI correctly")
        else:
             print(f"[FAIL] quantum_ai.quantum_news is {type(q_news)}")
    else:
        print("[FAIL] quantum_ai has NO quantum_news attribute")
        
    # Verify Intelligence Core update (check for new method logic presence if easily possible, or skip)
    print("Verification complete.")

except Exception as e:
    print(f"[FAIL] Verification Failed with error: {e}")
    import traceback
    traceback.print_exc()
