import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Import all view modules to check scoping and syntax
import views.aspirant
import views.guide
import views.sme
import views.admin
import app

print("✅ All view modules and app.py imported cleanly without any SyntaxError or UnboundLocalError!")
