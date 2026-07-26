import { useState, useRef, type DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, X, CheckCircle, Loader2, FileUp, FileCheck, FileText, ArrowRight } from 'lucide-react'
import { documentsApi } from '../services/api'
import { PageHeader } from '../components/ui/PageHeader'

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
    <div className="max-w-3xl animate-fade-in">
      <PageHeader
        title="Upload Documents"
        description="Upload research papers and drafts for AI-powered analysis"
      />

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`drop-zone p-14 text-center mb-6 ${dragOver ? 'drop-zone-active' : ''}`}
      >
        <div
          className="w-16 h-16 flex items-center justify-center mx-auto mb-4 border"
          style={{ background: 'var(--color-primary-light)', borderColor: 'var(--color-border)' }}
        >
          <Upload size={28} style={{ color: 'var(--color-primary)' }} />
        </div>
        <p className="text-base font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
          Drop files here or click to browse
        </p>
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
          PDF, DOCX, HTML, TXT, MD — max 20MB each
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
        <div className="card overflow-hidden mb-6">
          <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--color-border)' }}>
            <div className="flex items-center gap-2">
              <FileText size={16} style={{ color: 'var(--color-text-secondary)' }} />
              <span className="text-sm font-bold" style={{ color: 'var(--color-text)' }}>
                {files.length} file{files.length > 1 ? 's' : ''} selected
              </span>
            </div>
            <button
              onClick={uploadAll}
              disabled={pendingCount === 0}
              className="btn btn-primary btn-sm"
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
          <div className="divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-3 px-5 py-3.5">
                <div
                  className="w-9 h-9 flex items-center justify-center shrink-0 border"
                  style={{
                    background: f.sourceType === 'draft' ? 'var(--color-warning-light)' : 'var(--color-success-light)',
                    borderColor: 'var(--color-border)',
                  }}
                >
                  {f.sourceType === 'draft' ? (
                    <FileUp size={16} style={{ color: 'var(--color-warning)' }} />
                  ) : (
                    <FileCheck size={16} style={{ color: 'var(--color-success)' }} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate" style={{ color: 'var(--color-text)' }}>
                    {f.file.name}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                    {(f.file.size / 1024 / 1024).toFixed(1)} MB
                    {f.status === 'error' && f.error && (
                      <span style={{ color: 'var(--color-danger)' }}> · {f.error}</span>
                    )}
                  </p>
                </div>
                <select
                  value={f.sourceType}
                  onChange={(e) => setSourceType(i, e.target.value as 'draft' | 'paper')}
                  disabled={f.status === 'uploading' || f.status === 'done'}
                  className="text-xs font-semibold px-2.5 py-1.5 border bg-transparent cursor-pointer"
                  style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                >
                  <option value="draft">Draft</option>
                  <option value="paper">Paper</option>
                </select>
                {f.status === 'done' && <CheckCircle size={18} style={{ color: 'var(--color-success)' }} />}
                {f.status === 'uploading' && <Loader2 size={18} className="animate-spin" style={{ color: 'var(--color-primary)' }} />}
                {f.status === 'pending' && (
                  <button
                    onClick={() => removeFile(i)}
                    className="p-1.5 border transition-colors hover:bg-[var(--color-surface-hover)]"
                    style={{ borderColor: 'var(--color-border)' }}
                  >
                    <X size={16} style={{ color: 'var(--color-text-muted)' }} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {doneCount > 0 && doneCount === files.length && (
        <div
          className="card p-5 flex items-center justify-between gap-4"
          style={{ borderColor: 'var(--color-success)', background: 'var(--color-success-light)' }}
        >
          <div className="flex items-center gap-3">
            <CheckCircle size={22} style={{ color: 'var(--color-success)' }} />
            <div>
              <p className="text-sm font-bold" style={{ color: 'var(--color-success)' }}>
                All files uploaded successfully
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                Your documents are being processed and will be ready for analysis shortly.
              </p>
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <button onClick={() => setFiles([])} className="btn btn-secondary btn-sm">
              Upload more
            </button>
            <button onClick={() => navigate('/analysis')} className="btn btn-primary btn-sm">
              Go to Analysis
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
