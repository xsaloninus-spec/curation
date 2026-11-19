import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'
import { RectAreaLightUniformsLib } from 'three/examples/jsm/lights/RectAreaLightUniformsLib.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js'
import type { Language, Quality, SceneSnapshot, ViewMode, WallConfig, WallObject, WallZone } from '@/types/wall'

interface SceneCallbacks {
  onSnapshot: (snapshot: SceneSnapshot) => void
  onSelect: (zoneId: string) => void
  onModeChange: (mode: ViewMode) => void
  onError: (message: string) => void
  onObjectClick: (objectId: string) => void
  onModelStatus: (bay: number, label: string | null) => void
}

interface TourSegment {
  start: number
  end: number
  from: number
  to: number
  dwell: boolean
}

const STATION_X = [0.8, 5.2, 7.2, 9.2, 11.2, 13.2, 15.2, 17.2]
const STATION_LOOK: [number, number, number][] = [
  [2, 1.9, 0], [5.2, 1.4, 0], [7.2, 1.4, 0], [9.2, 1.4, 0],
  [11.2, 1.4, 0], [13.2, 1.4, 0], [15.2, 1.4, 0], [17.6, 1.3, 0],
]

function makeTourSegments(): TourSegment[] {
  const segments: TourSegment[] = []
  const transition = 40 / 7
  let cursor = 0
  for (let i = 0; i < 8; i += 1) {
    const dwell = i === 0 ? 8 : 6
    segments.push({ start: cursor, end: cursor + dwell, from: i, to: i, dwell: true })
    cursor += dwell
    if (i < 7) {
      segments.push({ start: cursor, end: cursor + transition, from: i, to: i + 1, dwell: false })
      cursor += transition
    }
  }
  return segments
}

const TOUR_SEGMENTS = makeTourSegments()
const clamp = THREE.MathUtils.clamp
const ease = (value: number) => value * value * (3 - 2 * value)

/** Shared ink-wash palette: light xuan paper room, black/gray only (case brass excepted). */
const INK = {
  background: '#d8d6d3',
  wall: '#d6d4d1',
  floor: '#b3b1ae',
  ceiling: '#cfcdcb',
  side: '#c9c7c3',
  pilaster: '#bab8b4',
  trim: '#a9a7a4',
  frame: '#84827f',
  lampNeutral: '#fff8ef',
  dust: '#8a8885',
  paper: '#f4f2ef',
  paperEdge: '#b8b6b3',
  paperHairline: '#cfcdca',
  baseline: 'rgba(150,148,145,0.4)',
  inkStrong: '#1a1a1a',
  inkBody: '#3c3c3c',
  inkMuted: '#6b6966',
  inkFaint: 'rgba(26,26,26,0.35)',
  debug: '#6f6d6a',
  select: '#3a3a3a',
} as const
const BASE_EXPOSURE = 1.06

function mulberry32(seed: number) {
  let state = seed >>> 0
  return () => {
    state = (state + 0x6d2b79f5) >>> 0
    let t = state
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function finishTexture(canvas: HTMLCanvasElement, repeatX: number, repeatY: number, srgb = true) {
  const texture = new THREE.CanvasTexture(canvas)
  if (srgb) texture.colorSpace = THREE.SRGBColorSpace
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping
  texture.repeat.set(repeatX, repeatY)
  texture.anisotropy = 8
  return texture
}

/** Light xuan-paper wall: fine fibers, cloud-like mottling and sparse faint ink dots. Canvas covers 3 m x 3 m. */
function makeWallTextures() {
  const size = 1024
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const random = mulberry32(173)

  const bump = document.createElement('canvas')
  bump.width = bump.height = size
  const bumpContext = bump.getContext('2d')!

  context.fillStyle = INK.wall
  context.fillRect(0, 0, size, size)
  bumpContext.fillStyle = '#7f7f7f'
  bumpContext.fillRect(0, 0, size, size)

  // paper fiber streaks — short, soft, mostly horizontal with some vertical
  for (let i = 0; i < 2600; i += 1) {
    const x = random() * size
    const y = random() * size
    const length = 6 + random() * 26
    const light = random() > 0.5
    context.strokeStyle = light
      ? `rgba(255,255,255,${0.015 + random() * 0.03})`
      : `rgba(110,108,105,${0.012 + random() * 0.026})`
    context.lineWidth = 0.6 + random() * 0.8
    context.beginPath()
    if (random() > 0.22) {
      context.moveTo(x, y)
      context.lineTo(x + length, y + (random() - 0.5) * 2.4)
    } else {
      context.moveTo(x, y)
      context.lineTo(x + (random() - 0.5) * 2.4, y + length)
    }
    context.stroke()
  }
  // cloud-floc mottling — broad, very low contrast light/dark patches
  for (let i = 0; i < 44; i += 1) {
    const px = random() * size
    const py = random() * size
    const radius = 60 + random() * 190
    const light = random() > 0.45
    const gradient = context.createRadialGradient(px, py, 0, px, py, radius)
    gradient.addColorStop(0, light ? `rgba(255,255,255,${0.02 + random() * 0.028})` : `rgba(96,94,91,${0.014 + random() * 0.024})`)
    gradient.addColorStop(1, 'rgba(128,126,123,0)')
    context.fillStyle = gradient
    context.fillRect(0, 0, size, size)
  }
  // sparse faint ink dots — small and pale, never dirty
  for (let i = 0; i < 380; i += 1) {
    const dot = 0.5 + random() * 1.5
    context.fillStyle = `rgba(88,86,83,${0.035 + random() * 0.05})`
    context.beginPath()
    context.arc(random() * size, random() * size, dot, 0, Math.PI * 2)
    context.fill()
  }
  // gentle paper tooth in the bump map
  for (let i = 0; i < 9000; i += 1) {
    const shade = 118 + Math.floor(random() * 22)
    bumpContext.fillStyle = `rgba(${shade},${shade},${shade},0.5)`
    bumpContext.fillRect(random() * size, random() * size, 1.2, 1.2)
  }

  return {
    map: finishTexture(canvas, 6, 1.2),
    bumpMap: finishTexture(bump, 6, 1.2, false),
  }
}

/** Matte neutral-gray stone floor: large soft tiles, low contrast, no polish. Canvas covers 4 m x 4 m (four 1 m tiles). */
function makeFloorTextures() {
  const size = 1024
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const random = mulberry32(911)

  const bump = document.createElement('canvas')
  bump.width = bump.height = size
  const bumpContext = bump.getContext('2d')!
  bumpContext.fillStyle = '#828282'
  bumpContext.fillRect(0, 0, size, size)

  const tile = size / 4
  for (let row = 0; row < 4; row += 1) {
    for (let col = 0; col < 4; col += 1) {
      const x = col * tile
      const y = row * tile
      const tone = 0.97 + random() * 0.06
      const base = [0xb3, 0xb1, 0xae].map(channel => Math.round(channel * tone))
      context.fillStyle = `rgb(${base[0]},${base[1]},${base[2]})`
      context.fillRect(x, y, tile, tile)
      // fine mineral speckle, kept faint
      for (let i = 0; i < 1100; i += 1) {
        const light = random() > 0.5
        context.fillStyle = light
          ? `rgba(255,255,255,${0.015 + random() * 0.03})`
          : `rgba(70,68,66,${0.015 + random() * 0.03})`
        const dot = 0.6 + random() * 1.5
        context.fillRect(x + random() * tile, y + random() * tile, dot, dot)
      }
      // occasional soft vein
      if (random() > 0.5) {
        context.strokeStyle = `rgba(96,94,92,${0.04 + random() * 0.04})`
        context.lineWidth = 1 + random() * 1.2
        context.beginPath()
        let vy = y + random() * tile
        context.moveTo(x, vy)
        for (let vx = 0; vx <= tile; vx += 24) {
          vy += (random() - 0.5) * 22
          context.lineTo(x + vx, vy)
        }
        context.stroke()
      }
      bumpContext.fillStyle = `rgb(${126 + Math.floor(random() * 18)},126,126)`
      bumpContext.fillRect(x + 2, y + 2, tile - 4, tile - 4)
    }
  }
  // thin grout seams
  context.fillStyle = 'rgba(118,116,113,0.55)'
  bumpContext.fillStyle = '#5f5f5f'
  for (let i = 0; i <= 4; i += 1) {
    context.fillRect(0, i * tile - 1.5, size, 3)
    context.fillRect(i * tile - 1.5, 0, 3, size)
    bumpContext.fillRect(0, i * tile - 2, size, 4)
    bumpContext.fillRect(i * tile - 2, 0, 4, size)
  }
  // faint matte tonal drift
  for (let i = 0; i < 14; i += 1) {
    const gradient = context.createRadialGradient(random() * size, random() * size, 0, random() * size, random() * size, 110 + random() * 180)
    gradient.addColorStop(0, `rgba(255,255,255,${0.01 + random() * 0.016})`)
    gradient.addColorStop(1, 'rgba(255,255,255,0)')
    context.fillStyle = gradient
    context.fillRect(0, 0, size, size)
  }

  return {
    map: finishTexture(canvas, 5.5, 1.5),
    bumpMap: finishTexture(bump, 5.5, 1.5, false),
  }
}

/** Warm veined stone for the display plinth. Canvas covers roughly 1.2 m x 1.2 m. */
function makeStoneTexture() {
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const random = mulberry32(417)
  context.fillStyle = '#d8d2c4'
  context.fillRect(0, 0, size, size)
  for (let i = 0; i < 14; i += 1) {
    context.strokeStyle = `rgba(120,112,96,${0.05 + random() * 0.07})`
    context.lineWidth = 0.8 + random() * 1.8
    context.beginPath()
    let y = random() * size
    context.moveTo(-10, y)
    for (let x = 0; x <= size + 20; x += 26) {
      y += (random() - 0.5) * 34
      context.lineTo(x, y)
    }
    context.stroke()
  }
  for (let i = 0; i < 5200; i += 1) {
    context.fillStyle = random() > 0.5
      ? `rgba(255,252,244,${0.02 + random() * 0.04})`
      : `rgba(90,84,70,${0.02 + random() * 0.04})`
    const dot = 0.5 + random() * 1.4
    context.fillRect(random() * size, random() * size, dot, dot)
  }
  return finishTexture(canvas, 3, 0.5)
}

/** Light matte ceiling panels with hairline seams. */
function makeCeilingTexture() {
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const random = mulberry32(77)
  context.fillStyle = INK.ceiling
  context.fillRect(0, 0, size, size)
  context.strokeStyle = 'rgba(90,88,85,0.16)'
  context.lineWidth = 2
  for (let i = 0; i <= 4; i += 1) {
    context.beginPath(); context.moveTo(0, i * 128); context.lineTo(size, i * 128); context.stroke()
    context.beginPath(); context.moveTo(i * 128, 0); context.lineTo(i * 128, size); context.stroke()
  }
  for (let i = 0; i < 7000; i += 1) {
    const shade = 196 + Math.floor(random() * 24)
    context.fillStyle = `rgba(${shade},${shade},${shade},0.3)`
    context.fillRect(random() * size, random() * size, 1, 1)
  }
  return finishTexture(canvas, 9, 2)
}

/** Soft radial dark gradient used for baked contact shadows. */
function makeShadowBlobTexture() {
  const size = 256
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  gradient.addColorStop(0, 'rgba(0,0,0,0.55)')
  gradient.addColorStop(0.62, 'rgba(0,0,0,0.3)')
  gradient.addColorStop(1, 'rgba(0,0,0,0)')
  context.fillStyle = gradient
  context.fillRect(0, 0, size, size)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

function textLines(context: CanvasRenderingContext2D, text: string, maxWidth: number) {
  const output: string[] = []
  for (const paragraph of text.split('\n')) {
    const words = paragraph.split(/\s+/)
    let line = ''
    for (const word of words) {
      const candidate = line ? `${line} ${word}` : word
      if (context.measureText(candidate).width > maxWidth && line) {
        output.push(line)
        line = word
      } else line = candidate
    }
    output.push(line)
  }
  return output
}

/* ------------------------------------------------------------------------ */
/* Ink-wash corner ornaments — procedural sumi-e style, black & gray only.  */
/* ------------------------------------------------------------------------ */

/** One tapered ink stroke between two points. */
function inkStroke(
  context: CanvasRenderingContext2D,
  x1: number, y1: number, x2: number, y2: number,
  width: number, tone: string, alpha: number,
) {
  const steps = Math.max(3, Math.round(Math.hypot(x2 - x1, y2 - y1) / 26))
  for (let i = 0; i < steps; i += 1) {
    const t0 = i / steps
    const t1 = (i + 1) / steps
    context.strokeStyle = `rgba(${tone},${alpha * (1 - t0 * 0.55)})`
    context.lineWidth = Math.max(0.6, width * (1 - t0 * 0.6))
    context.lineCap = 'round'
    context.beginPath()
    context.moveTo(x1 + (x2 - x1) * t0, y1 + (y2 - y1) * t0)
    context.lineTo(x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1)
    context.stroke()
  }
}

/** A single pointed bamboo leaf. */
function inkLeaf(context: CanvasRenderingContext2D, x: number, y: number, angle: number, length: number, tone: string, alpha: number) {
  context.save()
  context.translate(x, y)
  context.rotate(angle)
  context.fillStyle = `rgba(${tone},${alpha})`
  context.beginPath()
  context.moveTo(0, 0)
  context.quadraticCurveTo(length * 0.42, -length * 0.16, length, 0)
  context.quadraticCurveTo(length * 0.42, length * 0.16, 0, 0)
  context.fill()
  context.restore()
}

/** Ink bamboo growing from a corner: tapered segmented stalk + leaf sprays. */
function drawInkBamboo(context: CanvasRenderingContext2D, width: number, height: number, random: () => number, corner: 'tl' | 'bl') {
  const dirY = corner === 'tl' ? 1 : -1
  const baseX = width * 0.04
  const baseY = corner === 'tl' ? height * 0.02 : height * 0.98
  // main stalks, gently curving away from the corner
  const stalks = [
    { ex: width * 0.62, sway: 0.10, w: 11 },
    { ex: width * 0.36, sway: -0.06, w: 7.5 },
    { ex: width * 0.85, sway: 0.16, w: 5.5 },
  ]
  for (const stalk of stalks) {
    const joints = 5
    let px = baseX + width * 0.05 * random()
    let py = baseY
    for (let j = 0; j < joints; j += 1) {
      const t = (j + 1) / joints
      const nx = baseX + stalk.ex * t + Math.sin(t * 2.4) * width * stalk.sway
      const ny = baseY + dirY * height * 0.94 * t
      inkStroke(context, px, py, nx, ny, stalk.w * (1 - t * 0.5), '38,38,38', 0.62 - t * 0.1)
      // joint ring
      context.fillStyle = 'rgba(38,38,38,0.4)'
      context.beginPath()
      context.ellipse(nx, ny, stalk.w * 0.62, stalk.w * 0.34, Math.atan2(ny - py, nx - px), 0, Math.PI * 2)
      context.fill()
      // leaf spray at every other joint
      if (j >= 1 && j % 2 === 1) {
        const leaves = 4 + Math.floor(random() * 4)
        for (let l = 0; l < leaves; l += 1) {
          const side = random() > 0.5 ? 1 : -1
          const angle = (corner === 'tl' ? 0 : Math.PI) + side * (0.5 + random() * 0.9)
          const lx = nx + (random() - 0.5) * 26
          const ly = ny + dirY * (random() - 0.4) * 20
          inkLeaf(context, lx, ly, angle, 50 + random() * 60, random() > 0.3 ? '42,42,42' : '110,108,105', 0.42 + random() * 0.3)
        }
      }
      px = nx; py = ny
    }
  }
}

/** Distant ink-mountain silhouette: a cluster of slender soft peaks hugging one edge. */
function drawInkMountains(context: CanvasRenderingContext2D, x0: number, width: number, yBase: number, amplitude: number, random: () => number, tone: string, alpha: number) {
  const peaks = 3 + Math.floor(random() * 2)
  for (let p = 0; p < peaks; p += 1) {
    const px = x0 + width * ((p + 0.5) / peaks) + (random() - 0.5) * width * 0.14
    const peakH = amplitude * (0.45 + random() * 0.55)
    const halfW = width / peaks * (0.34 + random() * 0.22)
    const gradient = context.createLinearGradient(0, yBase - peakH, 0, yBase)
    gradient.addColorStop(0, `rgba(${tone},${alpha})`)
    gradient.addColorStop(1, `rgba(${tone},${alpha * 0.55})`)
    context.fillStyle = gradient
    context.beginPath()
    context.moveTo(px - halfW, yBase)
    context.quadraticCurveTo(px - halfW * 0.3, yBase - peakH * 0.72, px, yBase - peakH)
    context.quadraticCurveTo(px + halfW * 0.35, yBase - peakH * 0.6, px + halfW, yBase)
    context.closePath()
    context.fill()
  }
}

/** Small moored skiff with a canopy and a seated figure. */
function drawInkBoat(context: CanvasRenderingContext2D, x: number, y: number, scale: number, flip: boolean) {
  context.save()
  context.translate(x, y)
  context.scale(flip ? -scale : scale, scale)
  context.fillStyle = 'rgba(32,32,32,0.78)'
  // hull
  context.beginPath()
  context.moveTo(-56, 0)
  context.quadraticCurveTo(-30, 16, 0, 15)
  context.quadraticCurveTo(38, 14, 58, -6)
  context.quadraticCurveTo(40, 22, 0, 24)
  context.quadraticCurveTo(-42, 23, -56, 0)
  context.fill()
  // canopy
  context.beginPath()
  context.moveTo(-18, -2)
  context.quadraticCurveTo(0, -26, 22, -4)
  context.closePath()
  context.fill()
  // seated figure
  context.beginPath()
  context.arc(-2, -10, 5, 0, Math.PI * 2)
  context.fill()
  context.fillRect(-7, -7, 11, 9)
  // pole
  context.strokeStyle = 'rgba(32,32,32,0.45)'
  context.lineWidth = 2.4
  context.beginPath()
  context.moveTo(34, -8)
  context.lineTo(48, 14)
  context.stroke()
  context.restore()
}

/** Mountains + water ripples + skiff, anchored to a bottom corner. */
function drawInkBoatScene(context: CanvasRenderingContext2D, width: number, height: number, random: () => number, corner: 'br' | 'bl') {
  const flip = corner === 'bl'
  const anchorX = flip ? 0 : width
  const dirX = flip ? 1 : -1
  // two faint ridges of distant peaks hugging the outer edge
  drawInkMountains(context, width * 0.3, width * 0.68, height * 0.52, height * 0.2, random, '118,116,113', 0.26)
  drawInkMountains(context, width * 0.42, width * 0.56, height * 0.56, height * 0.13, random, '142,140,137', 0.24)
  // water ripples — thin broken horizontal strokes
  for (let i = 0; i < 16; i += 1) {
    const y = height * (0.6 + random() * 0.28)
    const start = anchorX + dirX * (width * 0.06 + random() * width * 0.3)
    const len = 30 + random() * 90
    context.strokeStyle = `rgba(70,68,66,${0.16 + random() * 0.2})`
    context.lineWidth = 1.4
    context.beginPath()
    context.moveTo(start, y)
    context.quadraticCurveTo(start + dirX * len * 0.5, y - 3, start + dirX * len, y)
    context.stroke()
  }
  // the skiff
  drawInkBoat(context, anchorX + dirX * width * 0.42, height * 0.7, 2.1 + random() * 0.5, flip)
  // a few drifting ink flecks
  for (let i = 0; i < 10; i += 1) {
    context.fillStyle = `rgba(60,58,56,${0.12 + random() * 0.16})`
    context.beginPath()
    context.arc(anchorX + dirX * random() * width * 0.85, height * (0.3 + random() * 0.6), 1 + random() * 2.2, 0, Math.PI * 2)
    context.fill()
  }
}

type InkOrnamentKind = 'bamboo-tl' | 'boat-br'

/** Renders one ink-wash motif on a transparent canvas, anchored to the named corner. */
function makeInkOrnamentTexture(kind: InkOrnamentKind) {
  const size = 1024
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const random = mulberry32(kind === 'bamboo-tl' ? 501 : 733)
  if (kind === 'bamboo-tl') drawInkBamboo(context, size, size, random, 'tl')
  else drawInkBoatScene(context, size, size, random, 'br')
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 8
  return texture
}

function makeZoneTexture(zone: WallZone, language: Language, showLabels: boolean, selected: boolean) {
  const width = Math.min(2048, Math.max(384, Math.round(zone.w * 900)))
  const height = Math.max(64, Math.round(width * zone.h / zone.w))
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')!
  const px = (meters: number) => meters / zone.w * width
  const text = zone.text[language]?.trim() ?? ''
  context.clearRect(0, 0, width, height)

  const serifStack = 'Georgia, "Songti SC", "STSong", "SimSun", serif'
  const sansStack = 'Inter, "Helvetica Neue", Helvetica, "PingFang SC", "Microsoft YaHei", sans-serif'
  const monoStack = '"SFMono-Regular", ui-monospace, Consolas, monospace'
  // Curatorial paper cards for every plaque-style zone; section headers stay bare on the wall.
  const hasCard = zone.style !== 'section'
  const isSerif = zone.style === 'title' || zone.style === 'verticalTitle' || zone.style === 'object' || zone.style === 'section'
  const textColor = zone.style === 'meta' || zone.style === 'subtitle'
    ? INK.inkMuted
    : zone.style === 'body' || zone.style === 'caption'
      ? INK.inkBody
      : INK.inkStrong

  const drawCard = () => {
    if (!hasCard) return
    const radius = Math.max(3, px(0.008))
    const path = () => {
      context.beginPath()
      context.moveTo(radius, 0.5)
      context.lineTo(width - radius - 0.5, 0.5)
      context.arcTo(width - 0.5, 0.5, width - 0.5, radius + 0.5, radius)
      context.lineTo(width - 0.5, height - radius - 0.5)
      context.arcTo(width - 0.5, height - 0.5, width - radius - 0.5, height - 0.5, radius)
      context.arcTo(radius + 0.5, height - 0.5, 0.5, height - radius - 0.5, radius)
      context.arcTo(0.5, 0.5, radius + 0.5, 0.5, radius)
      context.closePath()
    }
    context.fillStyle = INK.paper
    path()
    context.fill()
    context.strokeStyle = selected ? INK.select : INK.paperEdge
    context.lineWidth = selected ? Math.max(1.5, px(0.0022)) : Math.max(1, px(0.0012))
    context.stroke()
  }

  if (!text) {
    // Empty container: a complete, stable blank paper card — never any placeholder text.
    drawCard()
    if (hasCard) {
      // faint baseline rules suggesting the reserved typography bands
      const bands: [number, number][] = [[0.3, 0.46], [0.56, 0.68], [0.78, 0.34]]
      context.fillStyle = INK.baseline
      const lineHeight = Math.max(1.5, height * 0.045)
      for (const [cy, cw] of bands) {
        if (height * cy + lineHeight > height - 4) continue
        const wLine = width * cw * (0.9 + (zone.bay % 3) * 0.05)
        context.fillRect((width - wLine) / 2, height * cy, wLine, lineHeight)
      }
    } else {
      // bare empty section: faint corner ticks only
      context.strokeStyle = INK.inkFaint
      context.lineWidth = Math.max(1, px(0.002))
      const tick = Math.min(20, height * 0.16, width * 0.04)
      for (const [x, y, sx, sy] of [[0, 0, 1, 1], [width, 0, -1, 1], [0, height, 1, -1], [width, height, -1, -1]] as const) {
        context.beginPath()
        context.moveTo(x, y + sy * tick)
        context.lineTo(x, y)
        context.lineTo(x + sx * tick, y)
        context.stroke()
      }
    }
    if (showLabels) {
      const fontSize = clamp(px(0.032), 12, 25)
      context.font = `500 ${fontSize}px ${monoStack}`
      context.fillStyle = selected ? INK.select : INK.debug
      context.textAlign = 'left'
      context.textBaseline = 'top'
      const label = `[${zone.label}]`
      const lx = hasCard ? px(0.03) : px(0.035)
      const ly = hasCard ? px(0.024) : px(0.03)
      context.fillText(label, lx, ly, width - lx * 2)
    }
  } else {
    const worldSizes = { title: 0.26, verticalTitle: 0.3, subtitle: 0.04, body: 0.032, section: 0.09, object: 0.07, caption: 0.026, meta: 0.018 }
    const size = px(worldSizes[zone.style])
    drawCard()
    context.font = `${isSerif ? 500 : 400} ${size}px ${isSerif ? serifStack : sansStack}`
    context.fillStyle = textColor
    context.textBaseline = 'top'
    if (zone.style === 'verticalTitle') {
      const pad = hasCard ? px(0.02) : 0
      const characters = [...text.replace(/\s/g, '')].slice(0, zone.chars ?? 8)
      const lineHeight = Math.min(size * 1.12, (height - pad * 2) / Math.max(characters.length, 1))
      context.textAlign = 'center'
      characters.forEach((character, index) => context.fillText(character, width / 2, pad + Math.max(0, (height - pad * 2 - lineHeight * characters.length) / 2 + index * lineHeight)))
    } else {
      const padding = px(0.014) + (hasCard ? px(0.008) : 0)
      const maxTextWidth = width - padding * 2
      context.textAlign = zone.align
      const x = zone.align === 'center' ? width / 2 : zone.align === 'right' ? width - padding : padding
      if (zone.lines <= 1) {
        // Single-line fields (names, titles, meta): shrink the type to fit instead of truncating.
        let fitSize = size
        const minSize = size * 0.5
        while (fitSize > minSize && context.measureText(text).width > maxTextWidth) {
          fitSize = Math.max(minSize, fitSize * 0.93)
          context.font = `${isSerif ? 500 : 400} ${fitSize}px ${isSerif ? serifStack : sansStack}`
        }
        context.fillText(text, x, padding)
      } else {
        const lines = textLines(context, text, maxTextWidth).slice(0, zone.lines)
        const lineHeight = size * (zone.style === 'body' || zone.style === 'caption' ? 1.5 : 1.18)
        lines.forEach((line, index) => context.fillText(line, x, padding + index * lineHeight))
      }
    }
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.minFilter = THREE.LinearFilter
  texture.magFilter = THREE.LinearFilter
  texture.generateMipmaps = false
  return texture
}

const PROXY_PLAQUE_MATERIAL = new THREE.MeshStandardMaterial({ color: '#9a7440', metalness: 1, roughness: 0.35, envMapIntensity: 1.2 })

const PROXY_MATERIALS: THREE.MeshStandardMaterial[] = [
  new THREE.MeshStandardMaterial({ color: '#4a4a4a', metalness: 0.9, roughness: 0.4, envMapIntensity: 1.1 }),
  new THREE.MeshStandardMaterial({ color: '#e8e6e2', metalness: 0.02, roughness: 0.24, envMapIntensity: 0.9 }),
  new THREE.MeshStandardMaterial({ color: '#6e6c69', metalness: 0.05, roughness: 0.32, envMapIntensity: 1.0 }),
  new THREE.MeshStandardMaterial({ color: '#2e2e2e', metalness: 0.1, roughness: 0.16, envMapIntensity: 1.2 }),
  new THREE.MeshStandardMaterial({ color: '#b5b3b0', metalness: 0.02, roughness: 0.72, envMapIntensity: 0.4 }),
  new THREE.MeshStandardMaterial({ color: '#c9c7c4', metalness: 0.05, roughness: 0.1, transparent: true, opacity: 0.6, envMapIntensity: 1.4 }),
]

export class WallScene {
  private container: HTMLElement
  private config: WallConfig
  private callbacks: SceneCallbacks
  private renderer: THREE.WebGLRenderer
  private scene = new THREE.Scene()
  private camera: THREE.PerspectiveCamera
  private zoneGroup = new THREE.Group()
  private objectGroup = new THREE.Group()
  private models = new Map<number, THREE.Group>()
  private suppressedBays = new Set<number>()
  private loadingBays = new Set<number>()
  private resizeObserver: ResizeObserver
  private animationId = 0
  private lastFrame = performance.now()
  private lastSnapshot = 0
  private frames = 0
  private fpsTimer = performance.now()
  private fps = 60
  private time = 0
  private playing = true
  private speed = 1
  private mode: ViewMode = 'tour'
  private language: Language = 'en'
  private showLabels = true
  private selectedId = ''
  private quality: Quality = 'high'
  private reducedMotion = false
  private keys = new Set<string>()
  private yaw = 0
  private pitch = 0
  private raycaster = new THREE.Raycaster()
  private pointer = new THREE.Vector2()
  private disposed = false
  private dust: THREE.Points | null = null
  private dustVelocity: Float32Array | null = null
  private dustPhase: Float32Array | null = null

  constructor(container: HTMLElement, config: WallConfig, callbacks: SceneCallbacks) {
    this.container = container
    this.config = config
    this.callbacks = callbacks
    this.scene.background = new THREE.Color(INK.background)
    this.scene.fog = new THREE.FogExp2(INK.background, 0.006)
    this.camera = new THREE.PerspectiveCamera(52, 1, 0.05, 60)
    this.camera.rotation.order = 'YXZ'
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = BASE_EXPOSURE
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    this.renderer.domElement.className = 'wall-canvas'
    this.renderer.domElement.setAttribute('aria-label', 'Interactive continuous museum entrance wall')
    container.appendChild(this.renderer.domElement)
    RectAreaLightUniformsLib.init()

    // Neutral HDRI-style environment for convincing metal / glass / floor reflections.
    const pmrem = new THREE.PMREMGenerator(this.renderer)
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
    this.scene.environmentIntensity = 0.35
    pmrem.dispose()

    this.buildArchitecture()
    this.scene.add(this.zoneGroup, this.objectGroup)
    this.rebuildZones()
    this.rebuildObjects()
    void this.loadConfiguredModels()
    this.applyTour(0)
    this.bindEvents()
    this.resizeObserver = new ResizeObserver(() => this.resize())
    this.resizeObserver.observe(container)
    this.resize()
    const params = new URLSearchParams(window.location.search)
    if (params.has('t')) this.setTime(Number(params.get('t')) || 0)
    if (params.get('tour') !== '1') this.playing = false
    this.animate()
  }

  private mesh(geometry: THREE.BufferGeometry, material: THREE.Material, position: [number, number, number], parent: THREE.Object3D = this.scene) {
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(...position)
    parent.add(mesh)
    return mesh
  }

  private buildArchitecture() {
    const wallTextures = makeWallTextures()
    const wallMaterial = new THREE.MeshStandardMaterial({
      map: wallTextures.map,
      bumpMap: wallTextures.bumpMap,
      bumpScale: 0.45,
      color: '#ffffff',
      roughness: 0.92,
      envMapIntensity: 0.12,
    })
    const floorTextures = makeFloorTextures()
    const floorMaterial = new THREE.MeshStandardMaterial({
      map: floorTextures.map,
      bumpMap: floorTextures.bumpMap,
      bumpScale: 0.3,
      color: '#ffffff',
      roughness: 0.62,
      metalness: 0.02,
      envMapIntensity: 0.2,
    })
    const ceilingMaterial = new THREE.MeshStandardMaterial({ map: makeCeilingTexture(), color: '#ffffff', roughness: 0.96, envMapIntensity: 0.06 })
    const stoneMaterial = new THREE.MeshStandardMaterial({ map: makeStoneTexture(), color: '#ddd6c8', roughness: 0.58, envMapIntensity: 0.3 })
    const brassMaterial = new THREE.MeshStandardMaterial({ color: '#9a7440', metalness: 1.0, roughness: 0.3, envMapIntensity: 1.3 })
    const darkMaterial = new THREE.MeshStandardMaterial({ color: INK.frame, roughness: 0.85 })
    const trimMaterial = new THREE.MeshStandardMaterial({ color: INK.trim, roughness: 0.55, metalness: 0.1, envMapIntensity: 0.3 })
    const datumMaterial = new THREE.MeshStandardMaterial({ color: '#7c7a77', roughness: 0.5, metalness: 0.2, envMapIntensity: 0.3 })
    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: '#e2ece4',
      transparent: true,
      opacity: 0.09,
      roughness: 0.04,
      metalness: 0,
      clearcoat: 1,
      clearcoatRoughness: 0.06,
      envMapIntensity: 1.6,
      depthWrite: false,
      side: THREE.DoubleSide,
    })

    const wall = this.mesh(new THREE.BoxGeometry(18, 3.4, 0.4), wallMaterial, [9, 1.7, -0.2])
    wall.receiveShadow = true
    const floor = this.mesh(new THREE.PlaneGeometry(22, 6), floorMaterial, [9, 0, 1.7])
    floor.rotation.x = -Math.PI / 2
    floor.receiveShadow = true
    this.mesh(new THREE.PlaneGeometry(22, 4), ceilingMaterial, [9, 3.4, 1.5]).rotation.x = Math.PI / 2

    // side return walls close the gallery volume
    const sideMaterial = new THREE.MeshStandardMaterial({ color: INK.side, roughness: 0.92, envMapIntensity: 0.08 })
    const sideLeft = this.mesh(new THREE.PlaneGeometry(6, 3.4), sideMaterial, [0, 1.7, 1.7])
    sideLeft.rotation.y = Math.PI / 2
    const sideRight = this.mesh(new THREE.PlaneGeometry(6, 3.4), sideMaterial, [18, 1.7, 1.7])
    sideRight.rotation.y = -Math.PI / 2
    const entryFrame = this.mesh(new THREE.BoxGeometry(0.14, 3.4, 0.5), darkMaterial, [0.07, 1.7, -0.05])
    entryFrame.castShadow = true

    // ink-wash corner ornaments, tucked just in front of the paper wall
    const inkPlanes: [InkOrnamentKind, number, number, number, number][] = [
      // [kind, width m, height m, centerX, centerY] — corners only, the middle 80% stays blank
      ['bamboo-tl', 2.0, 1.7, 0.9, 2.6],
      ['boat-br', 2.4, 1.5, 16.9, 1.05],
    ]
    for (const [kind, w, h, cx, cy] of inkPlanes) {
      const ink = new THREE.Mesh(
        new THREE.PlaneGeometry(w, h),
        new THREE.MeshBasicMaterial({ map: makeInkOrnamentTexture(kind), transparent: true, opacity: 0.5, depthWrite: false, fog: false }),
      )
      ink.position.set(cx, cy, 0.01)
      ink.renderOrder = 1
      this.scene.add(ink)
    }

    // skirting + crown shadow gap + datum line
    this.mesh(new THREE.BoxGeometry(18, 0.12, 0.03), trimMaterial, [9, 0.06, 0.016])
    this.mesh(new THREE.BoxGeometry(18, 0.05, 0.02), darkMaterial, [9, 3.36, 0.012])
    this.mesh(new THREE.BoxGeometry(18, 0.005, 0.008), new THREE.MeshBasicMaterial({ color: '#7a7875' }), [9, 1.35, 0.009])
    this.mesh(new THREE.BoxGeometry(0.04, 0.04, 0.009), new THREE.MeshBasicMaterial({ color: '#6e6c69' }), [0.04, 1.35, 0.013])
    this.mesh(new THREE.BoxGeometry(0.02, 1.9, 0.025), new THREE.MeshBasicMaterial({ color: '#8a8885' }), [17.99, 1.35, 0.014])
    this.mesh(new THREE.BoxGeometry(18, 0.008, 0.016), darkMaterial, [9, 0.132, 0.014])
    this.mesh(new THREE.BoxGeometry(18, 0.02, 0.025), datumMaterial, [9, 1.52, 0.028])

    // pilasters with cap and foot
    const pilasterMaterial = new THREE.MeshStandardMaterial({ color: INK.pilaster, roughness: 0.93, envMapIntensity: 0.1 })
    for (const x of [4.2, 6.2, 8.2, 10.2, 12.2, 14.2, 16.2]) {
      this.mesh(new THREE.BoxGeometry(0.12, 3.4, 0.06), pilasterMaterial, [x, 1.7, 0.03])
      this.mesh(new THREE.BoxGeometry(0.18, 0.06, 0.1), pilasterMaterial, [x, 3.31, 0.04])
      this.mesh(new THREE.BoxGeometry(0.18, 0.1, 0.1), pilasterMaterial, [x, 0.17, 0.04])
      this.mesh(new THREE.BoxGeometry(0.16, 0.012, 0.09), datumMaterial, [x, 3.27, 0.045])
    }

    // display plinth: rounded body, overhanging top slab, brass reveals
    const base = this.mesh(new RoundedBoxGeometry(12, 0.9, 0.55, 4, 0.015), stoneMaterial, [10.2, 0.45, 0.275])
    base.castShadow = true
    base.receiveShadow = true
    const slab = this.mesh(new RoundedBoxGeometry(12.06, 0.06, 0.6, 4, 0.02), stoneMaterial, [10.2, 0.93, 0.28])
    slab.castShadow = true
    slab.receiveShadow = true
    this.mesh(new THREE.BoxGeometry(12, 0.022, 0.56), brassMaterial, [10.2, 1.4, 0.28])
    // brass corner guards on the plinth
    for (const x of [4.23, 16.17]) {
      this.mesh(new THREE.BoxGeometry(0.035, 0.9, 0.035), brassMaterial, [x, 0.45, 0.53])
    }

    // glass vitrine: front pane, top pane, framed edges + mullions
    this.mesh(new THREE.PlaneGeometry(12, 0.5), glassMaterial, [10.2, 1.15, 0.565])
    this.mesh(new THREE.PlaneGeometry(12, 0.6), glassMaterial, [10.2, 1.4, 0.28]).rotation.x = Math.PI / 2
    this.mesh(new THREE.BoxGeometry(12.04, 0.02, 0.02), brassMaterial, [10.2, 1.4, 0.585])
    this.mesh(new THREE.BoxGeometry(12.04, 0.015, 0.015), brassMaterial, [10.2, 0.905, 0.572])
    for (const x of [4.2, 6.2, 8.2, 10.2, 12.2, 14.2, 16.2]) {
      this.mesh(new THREE.BoxGeometry(0.04, 0.5, 0.025), brassMaterial, [x, 1.15, 0.572])
    }

    // baked contact shadows: floor under plinth, wall behind plinth
    const blobTexture = makeShadowBlobTexture()
    const floorBlobMaterial = new THREE.MeshBasicMaterial({ map: blobTexture, transparent: true, opacity: 0.62, depthWrite: false })
    const floorBlob = this.mesh(new THREE.PlaneGeometry(13.2, 2.2), floorBlobMaterial, [10.2, 0.002, 0.62])
    floorBlob.rotation.x = -Math.PI / 2
    const wallBlob = this.mesh(new THREE.PlaneGeometry(12.3, 0.5), floorBlobMaterial.clone(), [10.2, 0.28, 0.004])
    wallBlob.material.opacity = 0.45

    // cove light strip + track
    this.mesh(new THREE.BoxGeometry(18, 0.12, 0.1), new THREE.MeshStandardMaterial({ color: '#efece7', emissive: INK.lampNeutral, emissiveIntensity: 1.1 }), [9, 3.25, 0.075])
    this.mesh(new THREE.BoxGeometry(18, 0.06, 0.06), darkMaterial, [9, 3.31, 1.3])

    const coneMaterial = new THREE.MeshBasicMaterial({
      color: '#f3efe8',
      transparent: true,
      opacity: 0.013,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
      fog: false,
    })
    for (let i = 1; i <= 6; i += 1) {
      const x = 4.2 + (i - 0.5) * 2
      const fixture = this.mesh(new THREE.CylinderGeometry(0.045, 0.055, 0.12, 16), darkMaterial, [x, 3.22, 1.3])
      fixture.rotation.x = -0.35
      const spot = new THREE.SpotLight(INK.lampNeutral, 8, 4.6, 0.34, 0.6, 1.6)
      spot.position.set(x, 3.16, 1.3)
      spot.target.position.set(x, 1.1, 0.28)
      this.scene.add(spot, spot.target)
      const caseLight = new THREE.SpotLight('#ffd09a', 2.1, 1.1, 0.5, 0.65, 1.4)
      caseLight.position.set(x, 1.36, 0.3)
      caseLight.target.position.set(x, 0.9, 0.3)
      this.scene.add(caseLight, caseLight.target)

      // faint volumetric cone from track spot down to the case
      const from = new THREE.Vector3(x, 3.13, 1.28)
      const to = new THREE.Vector3(x, 1.0, 0.3)
      const direction = to.clone().sub(from)
      const length = direction.length()
      const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.38, length, 20, 1, true), coneMaterial)
      cone.position.copy(from).add(to).multiplyScalar(0.5)
      cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), direction.clone().normalize())
      this.scene.add(cone)
    }
    this.buildDust()

    const washer = new THREE.RectAreaLight('#fdf9f3', 3.0, 18, 0.12)
    washer.position.set(9, 3.23, 0.16)
    washer.lookAt(9, 1.2, 0)
    this.scene.add(washer)
    const titleLight = new THREE.RectAreaLight('#fdf9f3', 1.6, 4.2, 0.15)
    titleLight.position.set(2.1, 3.18, 0.5)
    titleLight.lookAt(2.1, 1.8, 0)
    this.scene.add(titleLight)
    const fill = new THREE.HemisphereLight('#f2f0ed', '#b9b7b4', 0.9)
    this.scene.add(fill)
    const shadowLight = new THREE.DirectionalLight('#f5f2ed', 1.1)
    shadowLight.position.set(6.5, 3.3, 2.9)
    shadowLight.target.position.set(10.2, 0.6, 0.2)
    shadowLight.castShadow = true
    shadowLight.shadow.mapSize.set(2048, 2048)
    shadowLight.shadow.camera.left = -8
    shadowLight.shadow.camera.right = 8
    shadowLight.shadow.camera.top = 4
    shadowLight.shadow.camera.bottom = -3
    shadowLight.shadow.camera.far = 14
    shadowLight.shadow.bias = -0.0004
    shadowLight.shadow.radius = 5
    this.scene.add(shadowLight, shadowLight.target)
  }

  private buildDust() {
    const count = 260
    const random = mulberry32(2024)
    const positions = new Float32Array(count * 3)
    this.dustVelocity = new Float32Array(count)
    this.dustPhase = new Float32Array(count)
    for (let i = 0; i < count; i += 1) {
      positions[i * 3] = 4.2 + random() * 12
      positions[i * 3 + 1] = 0.9 + random() * 2.2
      positions[i * 3 + 2] = 0.1 + random() * 2.1
      this.dustVelocity[i] = 0.008 + random() * 0.02
      this.dustPhase[i] = random() * Math.PI * 2
    }
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const material = new THREE.PointsMaterial({
      color: INK.dust,
      size: 0.011,
      transparent: true,
      opacity: 0.2,
      blending: THREE.NormalBlending,
      depthWrite: false,
      sizeAttenuation: true,
    })
    this.dust = new THREE.Points(geometry, material)
    this.scene.add(this.dust)
  }

  private updateDust(elapsed: number, delta: number) {
    if (!this.dust || !this.dustVelocity || !this.dustPhase) return
    const positions = this.dust.geometry.getAttribute('position') as THREE.BufferAttribute
    const array = positions.array as Float32Array
    for (let i = 0; i < this.dustVelocity.length; i += 1) {
      let y = array[i * 3 + 1] + this.dustVelocity[i] * delta
      if (y > 3.15) y = 0.9
      array[i * 3 + 1] = y
      array[i * 3] += Math.sin(elapsed * 0.35 + this.dustPhase[i]) * 0.00035
    }
    positions.needsUpdate = true
  }

  private rebuildZones() {
    for (const child of [...this.zoneGroup.children]) {
      const mesh = child as THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>
      mesh.geometry.dispose()
      mesh.material.map?.dispose()
      mesh.material.dispose()
      this.zoneGroup.remove(child)
    }
    for (const zone of this.config.zones) {
      const material = new THREE.MeshBasicMaterial({ map: makeZoneTexture(zone, this.language, this.showLabels, this.selectedId === zone.id), transparent: true, alphaTest: 0.015, depthWrite: false, side: THREE.DoubleSide })
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(zone.w, zone.h), material)
      mesh.position.set(zone.x + zone.w / 2, zone.y + zone.h / 2, 0.014 + zone.bay * 0.00005)
      mesh.renderOrder = 2
      mesh.userData.zoneId = zone.id
      this.zoneGroup.add(mesh)
    }
  }

  private rebuildObjects() {
    for (const child of [...this.objectGroup.children]) {
      if (![...this.models.values()].includes(child as THREE.Group)) {
        child.traverse(node => {
          if (node instanceof THREE.Mesh) {
            node.geometry.dispose()
            const materials = Array.isArray(node.material) ? node.material : [node.material]
            for (const material of materials) {
              if (!PROXY_MATERIALS.includes(material) && material !== PROXY_PLAQUE_MATERIAL) material.dispose()
            }
          }
        })
      }
      this.objectGroup.remove(child)
    }
    for (const object of this.config.objects) {
      const model = this.models.get(object.bay)
      if (model) this.objectGroup.add(model)
      else this.objectGroup.add(this.makeProxy(object))
    }
  }

  private makeProxy(object: WallObject) {
    const x = 4.2 + (object.bay - 0.5) * 2
    const radius = Math.min(object.proxy.w, object.proxy.h, object.proxy.d) * 0.12
    const material = PROXY_MATERIALS[(object.bay - 1) % PROXY_MATERIALS.length]
    const mesh = new THREE.Mesh(new RoundedBoxGeometry(object.proxy.w, object.proxy.h, object.proxy.d, 3, radius), material)
    mesh.position.set(x, 0.985 + object.proxy.h / 2, 0.29)
    mesh.rotation.y = (object.bay % 2 ? 1 : -1) * 0.14
    mesh.castShadow = true
    mesh.receiveShadow = true
    mesh.userData.objectId = object.id
    const group = new THREE.Group()
    group.userData.objectId = object.id
    group.add(mesh)
    // small brass label plaque on the plinth front
    const plaque = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.05, 0.008), PROXY_PLAQUE_MATERIAL)
    plaque.position.set(x, 0.7, 0.556)
    group.add(plaque)
    return group
  }

  private bindEvents() {
    window.addEventListener('keydown', this.onKeyDown)
    window.addEventListener('keyup', this.onKeyUp)
    document.addEventListener('pointerlockchange', this.onPointerLock)
    document.addEventListener('mousemove', this.onMouseMove)
    this.renderer.domElement.addEventListener('click', this.onClick)
    this.renderer.domElement.addEventListener('pointermove', this.onHover)
  }

  private onKeyDown = (event: KeyboardEvent) => {
    if ((event.target as HTMLElement)?.matches('input, textarea, select, [contenteditable="true"]')) return
    if (['KeyW', 'KeyA', 'KeyS', 'KeyD'].includes(event.code)) {
      event.preventDefault()
      if (this.mode !== 'walk') this.setMode('walk')
      this.keys.add(event.code)
    }
  }

  private onKeyUp = (event: KeyboardEvent) => this.keys.delete(event.code)
  private onPointerLock = () => undefined

  private onMouseMove = (event: MouseEvent) => {
    if (document.pointerLockElement !== this.renderer.domElement || this.mode !== 'walk') return
    this.yaw -= event.movementX * 0.0018
    this.pitch = clamp(this.pitch - event.movementY * 0.0018, -1.15, 1.15)
  }

  private onClick = (event: MouseEvent) => {
    if (this.mode === 'walk') {
      if (document.pointerLockElement !== this.renderer.domElement) this.renderer.domElement.requestPointerLock?.()
      return
    }
    const rect = this.renderer.domElement.getBoundingClientRect()
    this.pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1)
    this.raycaster.setFromCamera(this.pointer, this.camera)
    const hits = this.raycaster.intersectObjects([...this.objectGroup.children, ...this.zoneGroup.children], true)
    for (const hit of hits) {
      let node: THREE.Object3D | null = hit.object
      let objectId = ''
      while (node && node !== this.objectGroup && node !== this.zoneGroup) {
        if (node.userData.objectId) { objectId = node.userData.objectId; break }
        node = node.parent
      }
      if (objectId) { this.callbacks.onObjectClick(objectId); return }
      if (hit.object.userData.zoneId) {
        this.selectedId = hit.object.userData.zoneId
        this.rebuildZones()
        this.callbacks.onSelect(this.selectedId)
        return
      }
    }
  }

  private onHover = (event: PointerEvent) => {
    if (this.mode === 'walk' && document.pointerLockElement === this.renderer.domElement) return
    const rect = this.renderer.domElement.getBoundingClientRect()
    this.pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1)
    this.raycaster.setFromCamera(this.pointer, this.camera)
    const hit = this.raycaster.intersectObjects([...this.objectGroup.children, ...this.zoneGroup.children], true)[0]
    let node: THREE.Object3D | null = hit?.object ?? null
    let interactive = false
    while (node && node !== this.objectGroup && node !== this.zoneGroup) {
      if (node.userData.objectId || node.userData.zoneId) { interactive = true; break }
      node = node.parent
    }
    this.renderer.domElement.style.cursor = interactive ? 'pointer' : ''
  }

  private resize() {
    const width = Math.max(this.container.clientWidth, 1)
    const height = Math.max(this.container.clientHeight, 1)
    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(width, height, false)
  }

  private applyTour(time: number) {
    const segment = TOUR_SEGMENTS.find(item => time >= item.start && time <= item.end) ?? TOUR_SEGMENTS[TOUR_SEGMENTS.length - 1]
    const progress = segment.dwell ? 0 : ease(clamp((time - segment.start) / (segment.end - segment.start), 0, 1))
    const x = THREE.MathUtils.lerp(STATION_X[segment.from], STATION_X[segment.to], progress)
    const fromLook = STATION_LOOK[segment.from]
    const toLook = STATION_LOOK[segment.to]
    this.camera.position.set(x, 1.6, 2.8)
    this.camera.lookAt(
      THREE.MathUtils.lerp(fromLook[0], toLook[0], progress),
      THREE.MathUtils.lerp(fromLook[1], toLook[1], progress),
      0,
    )
    const fade = time > 84 ? 1 - (time - 84) / 6 * 0.58 : 1
    this.renderer.toneMappingExposure = BASE_EXPOSURE * fade
  }

  private updateWalk(delta: number) {
    this.camera.rotation.set(this.pitch, this.yaw, 0, 'YXZ')
    const forward = new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw))
    const right = new THREE.Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw))
    const movement = new THREE.Vector3()
    if (this.keys.has('KeyW')) movement.add(forward)
    if (this.keys.has('KeyS')) movement.sub(forward)
    if (this.keys.has('KeyD')) movement.add(right)
    if (this.keys.has('KeyA')) movement.sub(right)
    if (movement.lengthSq() > 0) {
      movement.normalize().multiplyScalar(delta * 1.65)
      this.camera.position.add(movement)
      this.camera.position.x = clamp(this.camera.position.x, 0.15, 17.85)
      this.camera.position.z = clamp(this.camera.position.z, 0.83, 3.05)
      this.camera.position.y = 1.6
    }
  }

  private currentBay() {
    const x = this.camera.position.x
    if (x < 4.2) return 0
    if (x >= 16.2) return 7
    return clamp(Math.floor((x - 4.2) / 2) + 1, 1, 6)
  }

  private animate = () => {
    if (this.disposed) return
    this.animationId = requestAnimationFrame(this.animate)
    const now = performance.now()
    const delta = Math.min((now - this.lastFrame) / 1000, 0.05)
    const elapsed = now / 1000
    this.lastFrame = now
    if (this.mode === 'tour') {
      if (this.playing) {
        const next = this.time + delta * this.speed
        this.time = next >= 90 ? (this.reducedMotion ? 90 : 0) : next
      }
      this.applyTour(this.time)
    } else {
      this.renderer.toneMappingExposure = BASE_EXPOSURE
      this.updateWalk(delta)
    }
    this.updateDust(elapsed, delta)
    this.renderer.render(this.scene, this.camera)
    this.frames += 1
    if (now - this.fpsTimer > 1000) {
      this.fps = Math.round(this.frames * 1000 / (now - this.fpsTimer))
      this.frames = 0
      this.fpsTimer = now
    }
    if (now - this.lastSnapshot > 180) {
      this.callbacks.onSnapshot({ time: this.time, playing: this.playing, mode: this.mode, bay: this.currentBay(), fps: this.fps })
      this.lastSnapshot = now
    }
  }

  setTime(value: number) {
    this.time = clamp(value, 0, 90)
    this.mode = 'tour'
    this.playing = false
    if (document.pointerLockElement) document.exitPointerLock()
    this.applyTour(this.time)
    this.callbacks.onModeChange('tour')
  }

  setPlaying(playing: boolean) {
    if (this.mode !== 'tour') this.setMode('tour')
    if (this.time >= 90 && playing) this.time = 0
    this.playing = playing
  }

  setSpeed(speed: number) { this.speed = speed }

  setMode(mode: ViewMode) {
    if (mode === this.mode) return
    this.mode = mode
    this.playing = false
    this.keys.clear()
    if (mode === 'walk') {
      const direction = this.camera.getWorldDirection(new THREE.Vector3())
      this.yaw = Math.atan2(-direction.x, -direction.z)
      this.pitch = Math.asin(clamp(direction.y, -1, 1))
      this.camera.position.y = 1.6
      this.renderer.domElement.requestPointerLock?.()
    } else {
      if (document.pointerLockElement) document.exitPointerLock()
      this.applyTour(this.time)
    }
    this.callbacks.onModeChange(mode)
  }

  jumpToBay(bay: number) {
    const index = clamp(bay, 0, 7)
    let cursor = 0
    for (let i = 0; i < index; i += 1) cursor += (i === 0 ? 8 : 6) + 40 / 7
    this.setTime(cursor)
  }

  setLanguage(language: Language) { this.language = language; this.rebuildZones() }
  setShowLabels(show: boolean) { this.showLabels = show; this.rebuildZones() }
  setReducedMotion(reduced: boolean) { this.reducedMotion = reduced }
  setQuality(quality: Quality) {
    this.quality = quality
    this.renderer.setPixelRatio(this.quality === 'high' ? Math.min(window.devicePixelRatio, 2) : 1)
    this.renderer.shadowMap.enabled = this.quality === 'high'
    if (this.dust) this.dust.visible = this.quality === 'high'
    this.resize()
  }

  selectZone(id: string) { this.selectedId = id; this.rebuildZones() }
  updateConfig(config: WallConfig) {
    // Re-place models whose configured source or rotation changed; custom imports stay untouched.
    for (const object of config.objects) {
      const cached = this.models.get(object.bay)
      if (!cached || cached.userData.customImport) continue
      const sameModel = (cached.userData.modelUrl ?? null) === (object.model ?? null)
      const sameRotation = (cached.userData.rotationY ?? 0) === (object.rotationY ?? 0)
      if (!sameModel || !sameRotation) {
        this.disposeModel(object.bay)
        this.suppressedBays.delete(object.bay)
      }
    }
    this.config = config
    this.rebuildZones()
    this.rebuildObjects()
    void this.loadConfiguredModels()
  }

  /** Center a loaded GLB on the plinth of the given bay, fitted to a 0.25 m maximum dimension. */
  private wrapModel(source: THREE.Object3D, bay: number, objectId: string, rotationY = 0, modelUrl: string | null = null) {
    if (rotationY) {
      const pivot = new THREE.Group()
      source.rotation.y = THREE.MathUtils.degToRad(rotationY)
      pivot.add(source)
      source = pivot
    }
    source.updateMatrixWorld(true)
    const box = new THREE.Box3().setFromObject(source)
    if (box.isEmpty()) throw new Error('The GLB does not contain visible geometry.')
    const size = box.getSize(new THREE.Vector3())
    const scale = 0.25 / Math.max(size.x, size.y, size.z)
    const center = box.getCenter(new THREE.Vector3())
    const wrapper = new THREE.Group()
    source.scale.setScalar(scale)
    source.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale)
    wrapper.add(source)
    wrapper.position.set(4.2 + (bay - 0.5) * 2, 0.985, 0.29)
    wrapper.userData.objectId = objectId
    wrapper.userData.bay = bay
    wrapper.userData.rotationY = rotationY
    wrapper.userData.modelUrl = modelUrl
    wrapper.traverse(child => {
      child.userData.objectId = child.userData.objectId ?? objectId
      if (child instanceof THREE.Mesh) { child.castShadow = true; child.receiveShadow = true }
    })
    return wrapper
  }

  private disposeModel(bay: number) {
    this.models.get(bay)?.traverse(child => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose()
        const materials = Array.isArray(child.material) ? child.material : [child.material]
        for (const material of materials) {
          for (const value of Object.values(material)) {
            if (value instanceof THREE.Texture) value.dispose()
          }
          material.dispose()
        }
      }
    })
    this.models.delete(bay)
  }

  /** Load the GLB models configured in wall.json into their display cases. */
  private async loadConfiguredModels() {
    const loader = new GLTFLoader()
    loader.setMeshoptDecoder(MeshoptDecoder)
    let stale = false
    for (const object of this.config.objects) {
      if (!object.model || this.models.has(object.bay) || this.suppressedBays.has(object.bay) || this.loadingBays.has(object.bay)) continue
      this.loadingBays.add(object.bay)
      try {
        const gltf = await loader.loadAsync(object.model)
        // The config may have changed while the GLB was downloading; only place the model if it is still current.
        const current = this.config.objects.find(entry => entry.bay === object.bay)
        if (current && current.model === object.model && (current.rotationY ?? 0) === (object.rotationY ?? 0)) {
          this.models.set(object.bay, this.wrapModel(gltf.scene, object.bay, object.id, object.rotationY ?? 0, object.model))
          this.callbacks.onModelStatus(object.bay, object.model.split('/').pop() ?? object.model)
        } else {
          stale = true
        }
      } catch {
        this.callbacks.onError(`Could not load model for B${object.bay} — placeholder kept.`)
      }
      this.loadingBays.delete(object.bay)
      this.rebuildObjects()
    }
    if (stale) void this.loadConfiguredModels()
  }

  async importGlb(bay: number, file: File) {
    if (!file.name.toLowerCase().endsWith('.glb')) throw new Error('Please choose a binary .glb model.')
    if (file.size > 50 * 1024 * 1024) throw new Error('Please use a GLB smaller than 50 MB.')
    const buffer = await file.arrayBuffer()
    const gltf = await new GLTFLoader().parseAsync(buffer, '')
    const objectId = this.config.objects.find(object => object.bay === bay)?.id ?? `bay-${bay}`
    const rotationY = this.config.objects.find(object => object.bay === bay)?.rotationY ?? 0
    this.disposeModel(bay)
    const wrapper = this.wrapModel(gltf.scene, bay, objectId, rotationY)
    wrapper.userData.customImport = true
    this.suppressedBays.delete(bay)
    this.models.set(bay, wrapper)
    this.callbacks.onModelStatus(bay, file.name)
    this.rebuildObjects()
  }

  resetModel(bay: number) {
    this.disposeModel(bay)
    this.suppressedBays.add(bay)
    this.callbacks.onModelStatus(bay, null)
    this.rebuildObjects()
  }

  capture() {
    this.renderer.render(this.scene, this.camera)
    const link = document.createElement('a')
    link.download = `entrance-wall-${Math.round(this.time)}s.png`
    link.href = this.renderer.domElement.toDataURL('image/png')
    link.click()
  }

  dispose() {
    this.disposed = true
    cancelAnimationFrame(this.animationId)
    this.resizeObserver.disconnect()
    window.removeEventListener('keydown', this.onKeyDown)
    window.removeEventListener('keyup', this.onKeyUp)
    document.removeEventListener('pointerlockchange', this.onPointerLock)
    document.removeEventListener('mousemove', this.onMouseMove)
    this.renderer.domElement.removeEventListener('click', this.onClick)
    this.renderer.domElement.removeEventListener('pointermove', this.onHover)
    if (document.pointerLockElement) document.exitPointerLock()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
