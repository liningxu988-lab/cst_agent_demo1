' CST Auto Design - All-in-One Macro
' Iteration: 2
'
Sub Main()
    Dim proj As Object
    Dim solver As Object
    Dim results As Object
    Dim s11_result As Object
    Dim exportSuccess As Boolean
    
    exportSuccess = False
    
    On Error Resume Next
    
    ' Step 1: Get project
    Set proj = GetProject()
    If proj Is Nothing Then
        MsgBox "Error: Cannot get project!"
        Exit Sub
    End If
    
    ' Step 2: Update parameters
    Debug.Print "Updating parameters..."
    StoreDoubleParameter "patch_length", 12.0
    StoreDoubleParameter "patch_width", 10.0
    
    ' Step 3: Rebuild model
    Debug.Print "Rebuilding model..."
    proj.Rebuild
    
    ' Step 4: Run simulation
    Debug.Print "Starting simulation..."
    Set solver = proj.GetSolver()
    If Not solver Is Nothing Then
        solver.Start
        
        ' Wait for simulation to complete
        Debug.Print "Waiting for simulation..."
        Do While solver.IsSimulating
            Debug.Print "Simulating..."
            Sleep 2000  ' Wait 2 seconds
        Loop
        
        Debug.Print "Simulation completed!"
        
        ' Step 5: Export S11
        Debug.Print "Exporting S11..."
        Set results = proj.GetResultsInTree()
        
        If Not results Is Nothing Then
            Dim i As Integer
            For i = 0 To results.Count - 1
                Dim item As Object
                Set item = results.Item(i)
                
                If Not item Is Nothing Then
                    Dim itemName As String
                    itemName = item.GetName()
                    
                    ' Look for S11 result
                    If InStr(itemName, "S1,1") > 0 Or InStr(itemName, "S11") > 0 Then
                        Debug.Print "Found S11: " & itemName
                        
                        ' Export to ASCII
                        On Error Resume Next
                        item.ExportCurve "default", "outputs\\cst_auto\\s11_iteration_1.txt", True
                        
                        If Err.Number = 0 Then
                            exportSuccess = True
                            Debug.Print "Export successful!"
                        Else
                            Debug.Print "Export error: " & Err.Description
                        End If
                        On Error GoTo 0
                        
                        Exit For
                    End If
                End If
            Next
        End If
    End If
    
    ' Show result
    If exportSuccess Then
        MsgBox "Iteration 2 completed!" & vbCrLf & _
               "Parameters updated, simulation run, S11 exported to:" & vbCrLf & _
               "outputs\cst_auto\s11_iteration_1.txt", vbInformation
    Else
        MsgBox "Iteration 2 completed, but S11 export failed." & vbCrLf & _
               "Please manually export S11 to: outputs\cst_auto\s11_iteration_1.txt", vbExclamation
    End If
End Sub

' Helper function
Sub Sleep(milliseconds As Long)
    Dim endTime As Double
    endTime = Timer + milliseconds / 1000
    Do While Timer < endTime
        DoEvents
    Loop
End Sub
