import { useState, useRef, type DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, X, CheckCircle, Loader2, FileUp, FileCheck } from 'lucide-react'
import { documentsApi } from '../services/api'

export function UploadPage() {
  const navigate = useNavigate()
  const [files, setFiles] = useState<{ file: File; sourceType: 'draft' | 'paper'; status: 'pending' | 'uploading' | 'done' | 'error'; error?: string }[]>([])
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const addFiles = (newFiles: FileList | File[]) => {
    const entries = Array.from(newFiles).map((f) => ({
      file: f,
      sourceType: 'draft' as const,
      status: 'pending' as const,
    }))
    setFiles((prev) => [...prev, ...entries])
  }

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  const setSourceType = (idx: number, t: 'draft' | 'paper') => {
    setFiles((prev) => prev.map((f, i) => (i === idx ? { ...f, sourceType: t } : f)))
  }

  const uploadAll = async () => {
    for (let i = 0; i < files.length; i++) {
      if (files[i].status !== 'pending') continue
      setFiles((prev) => prev.map((f, j) => (j === i ? { ...f, status: 'uploading' } : f)))
      try {
        await documentsApi.upload(files[i].file, files[i].sourceType)
        setFiles((prev) => prev.map((f, j) => (j === i ? { ...f, status: 'done' } : f)))
      } catch (err: any) {
        setFiles((prev) =>
          prev.map((f, j) => (j === i ? { ...f, status: 'error', error: err?.response?.data?.detail || err.message } : f))
        )
      }
    }
  }

  const pendingCount = files.filter((f) => f.status === 'pending' || f.status === 'uploading').length
  const doneCount = files.filter((f) => f.status === 'done').length

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Upload Documents</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Upload research papers and drafts for analysis
        </p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className="border-2 border-dashed p-12 text-center cursor-pointer transition-colors mb-6"
        style={{
          borderColor: dragOver ? 'var(--color-primary)' : 'var(--color-border)',
          backgroundColor: dragOver ? 'var(--color-surface)' : 'transparent',
        }}
      >
        <Upload size={32} className="mx-auto mb-3" style={{ color: 'var(--color-text-secondary)' }} />
        <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
          Drop files here or click to browse
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          PDF, DOCX, HTML, TXT, MD (max 20MB each)
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.html,.txt,.md"
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <div className="border" style={{ borderColor: 'var(--color-border)' }}>
          <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: 'var(--color-border)' }}>
            <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
              {files.length} file{files.length > 1 ? 's' : ''}
            </span>
            <div className="flex gap-2">
              <button
                onClick={uploadAll}
                disabled={pendingCount === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40"
                style={{
                  backgroundColor: 'var(--color-primary)',
                  color: '#fff',
                }}
                onMouseEnter={e => !pendingCount && (e.currentTarget.style.backgroundColor = 'var(--color-primary-hover)')}
                onMouseLeave={e => e.currentTarget.style.backgroundColor = 'var(--color-primary)'}
              >
                {pendingCount > 0 ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Upload {pendingCount}
                  </>
                ) : (
                  <>
                    <CheckCircle size={14} />
                    All uploaded
                  </>
                )}
              </button>
            </div>
          </div>
          <div className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3">
                {f.sourceType === 'draft' ? (
                  <FileUp size={18} style={{ color: 'var(--color-warning)' }} />
                ) : (
                  <FileCheck size={18} style={{ color: 'var(--color-success)' }} />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text)' }}>
                    {f.file.name}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    {(f.file.size / 1024 / 1024).toFixed(1)} MB
                  </p>
                </div>
                <select
                  value={f.sourceType}
                  onChange={(e) => setSourceType(i, e.target.value as 'draft' | 'paper')}
                  disabled={f.status === 'uploading' || f.status === 'done'}
                  className="text-xs font-medium px-2 py-1 border bg-transparent"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                >
                  <option value="draft">Draft</option>
                  <option value="paper">Paper</option>
                </select>
                {f.status === 'done' && <CheckCircle size={16} style={{ color: 'var(--color-success)' }} />}
                {f.status === 'error' && <span className="text-xs" style={{ color: 'var(--color-danger)' }}>Failed</span>}
                {f.status === 'uploading' && <Loader2 size={16} className="animate-spin" style={{ color: 'var(--color-primary)' }} />}
                {f.status === 'pending' && (
                  <button onClick={() => removeFile(i)} className="p-1 transition-colors hover:bg-black/5 dark:hover:bg-white/10">
                    <X size={14} style={{ color: 'var(--color-text-secondary)' }} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {doneCount > 0 && doneCount === files.length && (
        <div className="mt-4 p-4 border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <p className="text-sm font-medium" style={{ color: 'var(--color-success)' }}>
            All files uploaded successfully
          </p>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => setFiles([])}
              className="text-xs font-medium px-3 py-1.5 border transition-colors"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
            >
              Upload more
            </button>
            <button
              onClick={() => navigate('/analysis')}
              className="text-xs font-medium px-3 py-1.5 transition-colors"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              Go to Analysis
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
