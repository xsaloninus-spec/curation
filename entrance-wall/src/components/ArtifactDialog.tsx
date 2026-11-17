import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { Loader2, Move3d, Pause, Play, RotateCcw, X, ZoomIn, ZoomOut } from 'lucide-react'
import { ArtifactViewer } from '@/scene/ArtifactViewer'
import type { ViewerStatus } from '@/scene/ArtifactViewer'
import { zoneText } from '@/lib/validation'
import type { Language, WallConfig, WallObject } from '@/types/wall'

interface Props {
  object: WallObject
  config: WallConfig
  language: Language
  onClose: () => void
}

function zoneById(config: WallConfig, id: string) {
  return config.zones.find(zone => zone.id === id)
}

export function ArtifactDialog({ object, config, language, onClose }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const viewer = useRef<ArtifactViewer | null>(null)
  const [status, setStatus] = useState<ViewerStatus>('loading')
  const [autoRotate, setAutoRotate] = useState(true)
  const bayLabel = String(object.bay).padStart(2, '0')

  useEffect(() => {
    if (!host.current || !object.model) return
    const instance = new ArtifactViewer(host.current, object.model, { onStatus: setStatus, rotationY: object.rotationY ?? 0 })
    viewer.current = instance
    return () => { viewer.current = null; instance.dispose() }
  }, [object.model, object.rotationY])

  const section = zoneById(config, `section.${bayLabel}`)
  const name = zoneById(config, `object.${bayLabel}.name`)
  const caption = zoneById(config, `caption.${bayLabel}`)
  const meta = zoneById(config, `meta.${bayLabel}`)

  const onKeyDown = (event: ReactKeyboardEvent) => {
    const view = viewer.current
    if (!view) return
    if (event.code === 'ArrowLeft') { event.preventDefault(); view.rotateBy(-14, 0) }
    else if (event.code === 'ArrowRight') { event.preventDefault(); view.rotateBy(14, 0) }
    else if (event.code === 'ArrowUp') { event.preventDefault(); view.rotateBy(0, -10) }
    else if (event.code === 'ArrowDown') { event.preventDefault(); view.rotateBy(0, 10) }
    else if (event.code === 'Equal' || event.code === 'NumpadAdd') { event.preventDefault(); view.zoomBy(0.85) }
    else if (event.code === 'Minus' || event.code === 'NumpadSubtract') { event.preventDefault(); view.zoomBy(1.18) }
  }

  const toggleRotate = () => {
    const next = !autoRotate
    setAutoRotate(next)
    viewer.current?.setAutoRotate(next)
  }

  return (
    <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
      <section className="artifact-modal" role="dialog" aria-modal="true" aria-label="Artifact viewer" tabIndex={-1} onKeyDown={onKeyDown} autoFocus>
        <div className="artifact-stage">
          <div ref={host} className="artifact-viewer" />
          {status === 'loading' && <div className="artifact-status"><Loader2 size={22} className="spin" /><span>Loading 3D model…</span></div>}
          {status === 'error' && <div className="artifact-status error"><span>Could not load this model.</span></div>}
          <div className="artifact-toolbar">
            <button className="icon-button" onClick={() => viewer.current?.zoomBy(0.8)} title="Zoom in · +"><ZoomIn size={16} /></button>
            <button className="icon-button" onClick={() => viewer.current?.zoomBy(1.25)} title="Zoom out · −"><ZoomOut size={16} /></button>
            <button className={`icon-button ${autoRotate ? 'active' : ''}`} onClick={toggleRotate} title={autoRotate ? 'Pause auto-rotation' : 'Resume auto-rotation'}>{autoRotate ? <Pause size={16} /> : <Play size={16} />}</button>
            <button className="icon-button" onClick={() => viewer.current?.resetView()} title="Reset view"><RotateCcw size={16} /></button>
            <span className="toolbar-hint"><Move3d size={13} />DRAG · SCROLL · ARROWS</span>
          </div>
        </div>
        <aside className="artifact-info">
          <div className="editor-header">
            <div>
              <span className="eyebrow">{section ? zoneText(section, language) || section.label : `OBJECT BAY ${bayLabel}`} · B{object.bay}</span>
              <h2>{name ? zoneText(name, language) ?? '' : ''}</h2>
            </div>
            <button className="icon-button" onClick={onClose} title="Close · Esc"><X size={18} /></button>
          </div>
          {meta && <p className="artifact-meta">{zoneText(meta, language) ?? ''}</p>}
          <p className="artifact-caption">{caption ? zoneText(caption, language) ?? '' : ''}</p>
          <p className="artifact-note">360° interactive view · drag to rotate, scroll or pinch to zoom, arrow keys to turn.</p>
        </aside>
      </section>
    </div>
  )
}
