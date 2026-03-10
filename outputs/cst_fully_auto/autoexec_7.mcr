' CST FULLY AUTOMATIC EXECUTION - Iteration 7
' This macro runs automatically when CST starts
' NO USER INTERACTION REQUIRED

Sub Main()
    On Error Resume Next
    
    Dim proj As Object, solver As Object, results As Object
    Dim fso As Object, flagFile As Object
    Dim exportSuccess As Boolean
    Dim startTime As Double
    
    exportSuccess = False
    startTime = Timer
    
    Debug.Print "[AUTO] === Starting Automatic Execution 7 ==="
    
    ' Get project
    Set proj = GetProject()
    If proj Is Nothing Then
        Debug.Print "[AUTO] ERROR: Cannot get project"
        WriteStatus "FAILED", "Cannot get project"
        Exit Sub
    End If
    
    ' Step 1: Parameters
    Debug.Print "[AUTO] Step 1: Setting parameters..."
    StoreDoubleParameter "patch_length", CDbl(12.0)
    StoreDoubleParameter "patch_width", CDbl(10.0)
    If Err.Number <> 0 Then
        WriteStatus "FAILED", "Parameter error: " & Err.Description
        Exit Sub
    End If
    
    ' Step 2: Rebuild
    Debug.Print "[AUTO] Step 2: Rebuilding..."
    Err.Clear
    proj.Rebuild
    DoEvents  ' Allow UI update
    If Err.Number <> 0 Then
        WriteStatus "FAILED", "Rebuild error: " & Err.Description
        Exit Sub
    End If
    Debug.Print "[AUTO] Rebuild OK"
    
    ' Step 3: Run simulation
    Debug.Print "[AUTO] Step 3: Running simulation..."
    Set solver = proj.GetSolver()
    If solver Is Nothing Then
        WriteStatus "FAILED", "Cannot get solver"
        Exit Sub
    End If
    
    Err.Clear
    solver.Start
    If Err.Number <> 0 Then
        WriteStatus "FAILED", "Solver start error: " & Err.Description
        Exit Sub
    End If
    
    ' Wait with progress
    Debug.Print "[AUTO] Waiting for simulation..."
    Dim waitCount As Integer
    waitCount = 0
    Do While solver.IsSimulating
        Sleep 2000
        waitCount = waitCount + 2
        Debug.Print "[AUTO] Running... " & waitCount & "s"
        ' Timeout after 30 minutes
        If waitCount > 1800 Then
            WriteStatus "FAILED", "Simulation timeout (>30min)"
            Exit Sub
        End If
    Loop
    Debug.Print "[AUTO] Simulation completed!"
    
    ' Step 4: Export S11
    Debug.Print "[AUTO] Step 4: Exporting S11..."
    Set results = proj.GetResultsInTree()
    If results Is Nothing Then
        WriteStatus "FAILED", "No results"
        Exit Sub
    End If
    
    Debug.Print "[AUTO] Found " & results.Count & " results"
    
    Dim i As Integer
    Dim item As Object
    Dim itemName As String
    
    For i = 0 To results.Count - 1
        Set item = results.Item(i)
        If Not item Is Nothing Then
            itemName = item.GetName()
            If InStr(itemName, "S1,1") > 0 Or InStr(itemName, "S11") > 0 Or _
               InStr(itemName, "S-Parameter") > 0 Or InStr(itemName, "S Parameter") > 0 Then
                
                Debug.Print "[AUTO] Exporting: " & itemName
                Err.Clear
                item.ExportCurve "default", "E:\\code\\cst_agent_demo\\outputs\\cst_fully_auto\\s11_iter_7.txt", True
                
                If Err.Number = 0 Then
                    exportSuccess = True
                    Debug.Print "[AUTO] Export OK"
                Else
                    Debug.Print "[AUTO] Export failed: " & Err.Description
                End If
                Exit For
            End If
        End If
    Next
    
    If Not exportSuccess Then
        WriteStatus "FAILED", "S11 not found or export failed"
        Exit Sub
    End If
    
    ' Step 5: Write completion flag
    Debug.Print "[AUTO] Step 5: Writing status..."
    WriteStatus "SUCCESS", "Iteration 7 completed"
    
    Debug.Print "[AUTO] === Execution Complete ==="
    
    ' Optional: Close CST for next iteration
    ' Uncomment the next line if you want CST to close after each iteration
    ' Quit
    
End Sub

Sub WriteStatus(status As String, msg As String)
    On Error Resume Next
    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.CreateTextFile("E:\\code\\cst_agent_demo\\outputs\\cst_fully_auto\\s11_iter_7.txt.done", True)
    ts.WriteLine status & ": " & msg
    ts.WriteLine "Time: " & Now
    ts.Close
End Sub

Sub Sleep(ms As Long)
    Dim endTime As Double
    endTime = Timer + ms / 1000
    Do While Timer < endTime
        DoEvents
    Loop
End Sub

Sub Quit()
    On Error Resume Next
    Application.Quit
End Sub
