Set WshShell = CreateObject("WScript.Shell")
' Silently run powershell to terminate only the Python processes running streamlit
WshShell.Run "powershell -WindowStyle Hidden -Command ""Get-Process -Name python, streamlit -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*streamlit*' -or $_.Name -eq 'streamlit' } | Stop-Process -Force""", 0, True
' Display a clean message box
MsgBox "Dota 2 Draft Analyzer server has been stopped successfully.", 64, "Dota 2 Draft Analyzer"
