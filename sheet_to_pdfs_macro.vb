
Private Sub CommandButton1_Click()
  CheckAndCreateFolder TextBox2.Text
  ExportingPDFNotice1 TextBox2.Value
  MsgBox "Réussi!"
  Unload NoticeForm
End Sub


Public Sub pickfolderButton_Click()
    Dim folderPath As String
    With Application.FileDialog(msoFileDialogFolderPicker)
        If .Show = -1 Then
            folderPath = .SelectedItems(1)
            TextBox2.Value = folderPath
        End If
    End With
End Sub

Private Sub SpinButton1_Change()
    TextBox1.Text = SpinButton1.Value
End Sub

Private Sub TextBox1_Change()
    SpinButton1.Value = CInt(TextBox1.Text)
End Sub


Sub ExportingPDFNotice1(path)

    'Defining worksheets
    Dim detailsSheet As Worksheet
    Dim reportSheet As Worksheet

    Dim notice As String
    If OptionButton1.Value = True Then
        notice = "Premier"
    ElseIf OptionButton1.Value = False Then
        notice = "Deuxieme"
    End If
    Set reportSheet = ActiveWorkbook.Sheets(notice)
    Set detailsSheet = ActiveWorkbook.Sheets("Details")

    Dim result As Collection
    Dim minIndex As Long
    Dim maxIndex As Long

    Set result = GetSelectedMinMaxIndexesAndCount(ActiveSheet.Name)

    minIndex = result.Item(1)
    maxIndex = result.Item(2)

    Application.ScreenUpdating = False

    For i = minIndex To maxIndex

        'Assigning values
        SName = detailsSheet.Cells(i, 1)
        If (SName <> "") Then
            CNI = detailsSheet.Cells(i, 2)
            Adresse = detailsSheet.Cells(i, 3)
            Informations = detailsSheet.Cells(i, 4)
            Annexe = detailsSheet.Cells(i, 5)
            AnnexeFR = detailsSheet.Cells(i, 6)

            YearsNoPay = detailsSheet.Cells(i, 7)
            MontantTotale = detailsSheet.Cells(i, 8)

            'Generating the output

            reportSheet.Cells(1, 1).Value = Date
            reportSheet.Cells(5, 1).Value = SName
            reportSheet.Cells(9, 2).Value = CNI
            reportSheet.Cells(6, 1).Value = Adresse
            reportSheet.Cells(23, 4).Value = SName
            reportSheet.Cells(23, 1).Value = Informations
            'reportSheet.Cells(57, 3).Value = Informations
            'reportSheet.Cells(47, 4).Value = Informations
            'reportSheet.Cells(51, 1).Value = Annexe
            'reportSheet.Cells(62, 4).Value = SName

            'reportSheet.Cells(23, 3).Value = YearsNoPay

            'reportSheet.Cells(23, 1).Value = MontantTotale
            'reportSheet.Cells(23, 2).Value = UnitePrice
            

            v1 = GetFileName(SName)
            v2 = GetFileName(Replace(Informations, "/", "_"))
            'Save the PDF file
            reportSheet.ExportAsFixedFormat Type:=xlTypePDF, Filename:= _
                path & "\" & AnnexeFR & "-" & notice & "-(" & Format(i, "000") & ")" & "-" & v2, Quality:=xlQualityStandard, _
                IncludeDocProperties:=True, IgnorePrintAreas:=False, _
                OpenAfterPublish:=False
        End If

    Next i

    Application.ScreenUpdating = True

End Sub


Public Sub CheckAndCreateFolder(folderPath As String)
    exis = FolderExists(folderPath)
    If Not exis Then
        CreateFolder folderPath
    End If
End Sub

Function GetFileName(ByVal Param As String) As String
    Dim pattern As String
    Dim regex As Object
    Dim replacedString As String
    
    pattern = "[<>:""/\\|?*]" ' Define the pattern
    
    ' Create a regular expression object
    Set regex = CreateObject("VBScript.RegExp")
    regex.Global = True
    regex.IgnoreCase = True
    regex.pattern = pattern
    
    ' Replace matches with underscores
    replacedString = regex.Replace(Param, "_")
    
    GetFileName = replacedString ' Return the modified string
End Function



Function FolderExists(folderPath As String) As Boolean
    FolderExists = (Dir(folderPath, vbDirectory) <> "")
End Function

Sub CreateFolder(folderPath As String)
    MkDir folderPath
End Sub


Function GetSelectedMinMaxIndexesAndCount(ByVal sheetName As String) As Collection
    Dim ws As Worksheet
    Dim selectedRange As Range
    Dim minIndex As Long
    Dim maxIndex As Long
    Dim count As Long
    Dim result As New Collection

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    Dim dataRange As Range
    Set dataRange = ws.UsedRange

    Dim numRows As Long
    Dim numCols As Long
    numRows = dataRange.Rows.count
    numCols = dataRange.Columns.count
    If ws Is Nothing Then
        result.Add 2
        result.Add numRows
        result.Add numRows - 1
        Set GetSelectedMinMaxIndexesAndCount = result
        Exit Function
    End If

    Set selectedRange = Application.Selection.Rows

    If selectedRange Is Nothing Then
        result.Add 2
        result.Add numRows
        result.Add numRows - 1
        Set GetSelectedMinMaxIndexesAndCount = result
        Exit Function
    End If

    
    count = selectedRange.Rows.count
    If count = 1 Then
        result.Add 2
        result.Add numRows
        result.Add numRows - 1
        Set GetSelectedMinMaxIndexesAndCount = result
        Exit Function
    End If
    minIndex = selectedRange.Cells(1, 1).Row
    maxIndex = selectedRange.Cells(count, 1).Row

    result.Add minIndex
    result.Add maxIndex
    result.Add count
    Set GetSelectedMinMaxIndexesAndCount = result
End Function


