@echo off
cd /d "C:\Users\jchoi\OneDrive\Desktop\Python Training\stock-backend"
"C:\Users\jchoi\AppData\Local\Programs\Python\Python313\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
