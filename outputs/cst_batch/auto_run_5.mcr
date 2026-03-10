' CST Auto Run - Iteration 5
Sub Main()
    On Error Resume Next
    Dim proj As Object, solver As Object, results As Object
    Dim exportSuccess As Boolean
    exportSuccess = False

    Set proj = GetProject()
    If proj Is Nothing Then
        MsgBox "Error: Cannot access project!", vbCritical
        Exit Sub
    End If

    Debug.Print "[5] Updating parameters..."
    StoreDoubleParameter "patch_length", 12.0
    StoreDoubleParameter "patch_width", 10.0

    Debug.Print "[5] Rebuilding..."
    proj.Rebuild

    Debug.Print "[5] Starting simulation..."
    Set solver = proj.GetSolver()
    If Not solver Is Nothing Then
        solver.Start
        Do While solver.IsSimulating
            Sleep 1000
        Loop
        Debug.Print "[5] Simulation done"

        Debug.Print "[5] Exporting S11..."
        Set results = proj.GetResultsInTree()
        Dim i As Integer
        For i = 0 To results.Count - 1
            Dim item As Object
            Set item = results.Item(i)
            If Not item Is Nothing Then
                Dim itemName As String
                itemName = item.GetName()
                If InStr(itemName, "S1,1") > 0 Or InStr(itemName, "S11") > 0 Then
                    item.ExportCurve "default", "outputs\\cst_batch\\s11_iter_5.txt", True
                    exportSuccess = True
                    Exit For
                End If
            End If
        Next
    End If

    Dim fso As Object, flagFile As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set flagFile = fso.CreateTextFile("outputs\\cst_batch\\s11_iter_5.txt.done", True)
    flagFile.WriteLine "Iteration 5 completed"
    flagFile.Close

    If exportSuccess Then
        MsgBox "Iteration 5 completed!", vbInformation
    Else
        MsgBox "Iteration 5 done, export may have failed", vbExclamation
    End If
End Sub

Sub Sleep(milliseconds As Long)
    Dim endTime As Double
    endTime = Timer + milliseconds / 1000
    Do While Timer < endTime
        DoEvents
    Loop
End Sub
