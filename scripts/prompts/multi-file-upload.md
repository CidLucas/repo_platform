# Multi-file upload support for StepData onboarding

## Summary

Change the onboarding CSV file upload from single-file to multi-file. The user wants to select multiple spreadsheet files at once.

## Changes needed in `/home/ec2-user/repo_platform/apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx`

### 1. StepData component (lines 1116-1480)

**State changes (lines 1131-1138):**
Replace single-file states:
```ts
const [csvUploaded, setCsvUploaded] = useState(false)
const [csvHeaders, setCsvHeaders] = useState<string[]>([])
const [csvFileName, setCsvFileName] = useState<string>('')
const [csvClassification, setCsvClassification] = useState<CsvClassification | null>(null)
const [showClassificationModal, setShowClassificationModal] = useState(false)
const [showSchemaTypeRadios, setShowSchemaTypeRadios] = useState(true)
const csvRef = useRef<HTMLInputElement>(null)
const csvFileRef = useRef<File | null>(null)
```

With:
```ts
interface CsvFileEntry {
  file: File
  headers: string[]
  sheetName: string
}
const [csvFiles, setCsvFiles] = useState<CsvFileEntry[]>([])
const [csvUploaded, setCsvUploaded] = useState(false)
const [csvClassification, setCsvClassification] = useState<CsvClassification | null>(null)
const [showClassificationModal, setShowClassificationModal] = useState(false)
const [showSchemaTypeRadios, setShowSchemaTypeRadios] = useState(true)
const csvRef = useRef<HTMLInputElement>(null)
```

**handleCsvChange (lines 1250-1259):** Change to accept multiple files, parse all, show modal:
```ts
async function handleCsvChange(e: React.ChangeEvent<HTMLInputElement>) {
  const files = e.target.files
  if (!files || files.length === 0) return
  const entries: CsvFileEntry[] = []
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    try {
      const { headers, sheetName } = await parseSpreadsheetHeaders(file)
      entries.push({ file, headers, sheetName })
    } catch (err) {
      console.warn(`[onboarding] failed to parse ${file.name}:`, err)
    }
  }
  if (entries.length === 0) return
  setCsvFiles(entries)
  setShowClassificationModal(true)
}
```

**UI — "Planilha" tile (lines 1325-1328):** Show count when multiple files:
```tsx
{csvUploaded
  ? `✓ ${csvFiles.length} arquivo${csvFiles.length > 1 ? 's' : ''}${csvFiles.length > 0 ? ` · ${csvFiles[0].headers.length} colunas` : ''}`
  : 'CSV · XLSX · XLS'}
```

**Classification modal — "Confirmar" button (lines 1415-1423):** Call onCsvFileReady for each file:
```tsx
<button className="btn btn-primary" onClick={() => {
  const schemaType = csvClassification?.schemaType || 'invoices'
  setCsvUploaded(true)
  setCsvClassification({ confirmed: true, schemaType, canceled: false })
  setShowClassificationModal(false)
  setShowSchemaTypeRadios(false)
  for (const entry of csvFiles) {
    onCsvFileReady(entry.file, entry.sheetName, schemaType)
  }
}}>Confirmar</button>
```

**Cancel button (lines 1427-1435):** Reset array:
```tsx
<button className="btn btn-ghost" onClick={() => {
  setCsvFiles([])
  setCsvUploaded(false)
  setCsvClassification(null)
  setShowClassificationModal(false)
  onCsvFileReady(null)
}}>Cancelar</button>
```

**Classification modal sub-select (lines 1440-1449):** Confirm with sub-select, call for each file:
```tsx
<select value={csvClassification.schemaType} onChange={e => {
  setCsvClassification(prev => prev ? { ...prev, schemaType: e.target.value } : { confirmed: false, schemaType: e.target.value, canceled: false })
  if (e.target.value !== '') {
    setCsvUploaded(true)
    setCsvClassification({ confirmed: true, schemaType: e.target.value, canceled: false })
    setShowClassificationModal(false)
    for (const entry of csvFiles) {
      onCsvFileReady(entry.file, entry.sheetName, e.target.value)
    }
  }
}}>
```

**Hidden file input (line 1461-1467):** Add `multiple` attribute:
```tsx
<input
  ref={csvRef}
  type="file"
  accept=".csv,.xlsx,.xls"
  multiple
  style={{ display: 'none' }}
  onChange={handleCsvChange}
/>
```

**handleNext (lines 1262-1273):** Match columns using first file's headers:
```tsx
async function handleNext() {
  const systems = [
    ...Object.keys(connected).filter(k => connected[k]),
    ...Object.keys(interested).filter(k => interested[k]),
  ]
  await saveDraft({ systems, csvUploaded })
  // Match CSV columns if uploaded; BQ columns are discovered in StepLaunch
  const schemaType = csvClassification?.schemaType || 'invoices'
  const firstEntry = csvFiles[0]
  const mappingResult = firstEntry ? await callMatchColumns(firstEntry.headers, schemaType) : null
  onMappingReady(mappingResult)
  onNext(mappingResult)
}
```

### 2. Parent component state (lines 2045-2047)

Change from single file to array:
```tsx
const [csvFiles, setCsvFiles] = useState<File[]>([])
const [csvSheetNames, setCsvSheetNames] = useState<string[]>([])
const [csvSchemaType, setCsvSchemaType] = useState<string>('invoices')
```

### 3. onCsvFileReady callback (lines 2192-2196)

Change to push to array:
```tsx
onCsvFileReady={(file, sheetName, schemaType) => {
  if (file) {
    setCsvFiles(prev => [...prev.filter(f => f.name !== file.name), file])
    if (sheetName) setCsvSheetNames(prev => [...prev.filter((_, i) => i < prev.length), sheetName])
  }
  if (schemaType) setCsvSchemaType(schemaType)
}}
```

Actually, simpler: just collect files in an array:
```tsx
onCsvFileReady={(file, sheetName, schemaType) => {
  if (!file) { setCsvFiles([]); return }
  setCsvFiles(prev => [...prev, file])
  if (schemaType) setCsvSchemaType(schemaType)
}}
```

### 4. StepLaunch component (lines 1764 and 1883-1889)

Change prop from single `csvFile` to `csvFiles: File[]` and loop:
```tsx
if (csvFiles.length > 0 && result.client_id) {
  for (const file of csvFiles) {
    const form = new FormData()
    form.append('client_id', result.client_id)
    form.append('file', file)
    form.append('schema_type', csvSchemaType || 'invoices')
    await fetch(uploadUrl, { method: 'POST', body: form })
  }
}
```

Prop interface at line 1764:
```tsx
csvFiles?: File[]    // was: csvFile?: File | null
```

Component call at line 2228:
```tsx
csvFiles={csvFiles}  // was: csvFile={csvFile}
```

## Please implement all changes above
