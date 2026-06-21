Set WshShell = CreateObject("WScript.Shell")
' Run streamlit silently (0 hides the cmd window)
WshShell.Run "cmd /c streamlit run app.py", 0, False
' Wait 3 seconds for the server to start up
WScript.Sleep 3000
' Open the application in the default web browser
WshShell.Run "http://localhost:8501", 1, False
