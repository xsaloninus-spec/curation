import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
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

/** Painted masonry wall: staggered block courses, mortar joints, weathering. Canvas covers 3 m x 3 m. */
function makeWallTextures() {
  const size = 1024
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const random = mulberry32(173)

  const bump = document.createElement('canvas')
  bump.width = bump.height = size
  const bumpContext = bump.getContext('2d')!

  context.fillStyle = '#454a3f'
  context.fillRect(0, 0, size, size)
  bumpContext.fillStyle = '#9a9a9a'
  bumpContext.fillRect(0, 0, size, size)

  const course = size / 8 // 0.375 m per course
  const block = size / 4 // 0.75 m per block
  for (let row = 0; row < 8; row += 1) {
    const y = row * course
    const offset = row % 2 ? block / 2 : 0
    for (let col = -1; col < 5; col += 1) {
      const x = col * block + offset
      const tone = 0.9 + random() * 0.22
      const r = Math.round(0x45 * tone)
      const g = Math.round(0x4a * tone)
      const b = Math.round(0x3f * tone)
      context.fillStyle = `rgb(${r},${g},${b})`
      context.fillRect(x + 2, y + 2, block - 4, course - 4)
      // per-block mottling
      for (let i = 0; i < 90; i += 1) {
        const shade = Math.floor(random() * 36)
        context.fillStyle = random() > 0.45
          ? `rgba(238,232,214,${0.02 + random() * 0.035})`
          : `rgba(${shade},${shade},${shade},${0.025 + random() * 0.04})`
        const dot = 1 + random() * 2.4
        context.fillRect(x + 2 + random() * (block - 6), y + 2 + random() * (course - 6), dot, dot)
      }
      // faint vertical drip stains on some blocks
      if (random() > 0.55) {
        const stainX = x + 6 + random() * (block - 12)
        const gradient = context.createLinearGradient(0, y, 0, y + course)
        gradient.addColorStop(0, `rgba(24,28,22,${0.05 + random() * 0.07})`)
        gradient.addColorStop(1, 'rgba(24,28,22,0)')
        context.fillStyle = gradient
        context.fillRect(stainX, y, 3 + random() * 7, course)
      }
      bumpContext.fillStyle = `rgb(${150 + Math.floor(random() * 40)},${150},${150})`
      bumpContext.fillRect(x + 2, y + 2, block - 4, course - 4)
    }
  }
  // mortar joints (recessed in bump)
  bumpContext.fillStyle = '#1c1c1c'
  for (let row = 0; row <= 8; row += 1) bumpContext.fillRect(0, row * course - 2, size, 4)
  for (let row = 0; row < 8; row += 1) {
    const offset = row % 2 ? block / 2 : 0
    for (let col = 0; col < 5; col += 1) bumpContext.fillRect(col * block + offset - 2, row * course, 4, course)
  }
  // broad tonal weathering patches
  for (let i = 0; i < 26; i += 1) {
    const px = random() * size
    const py = random() * size
    const radius = 120 + random() * 220
    const gradient = context.createRadialGradient(px, py, 0, px, py, radius)
    gradient.addColorStop(0, `rgba(18,22,17,${0.02 + random() * 0.03})`)
    gradient.addColorStop(1, 'rgba(18,22,17,0)')
    context.fillStyle = gradient
    context.fillRect(0, 0, size, size)
  }

  return {
    map: finishTexture(canvas, 6, 1.2),
    bumpMap: finishTexture(bump, 6, 1.2, false),
  }
}

/** Polished stone floor tiles. Canvas covers 4 m x 4 m (four 1 m tiles). */
function makeFloorTextures() {
  const size = 1024
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const random = mulberry32(911)

  const bump = document.createElement('canvas')
  bump.width = bump.height = size
  const bumpContext = bump.getContext('2d')!
  bumpContext.fillStyle = '#8c8c8c'
  bumpContext.fillRect(0, 0, size, size)

  const tile = size / 4
  for (let row = 0; row < 4; row += 1) {
    for (let col = 0; col < 4; col += 1) {
      const x = col * tile
      const y = row * tile
      const tone = 0.88 + random() * 0.24
      const base = [0x6e, 0x6c, 0x62].map(channel => Math.round(channel * tone))
      context.fillStyle = `rgb(${base[0]},${base[1]},${base[2]})`
      context.fillRect(x, y, tile, tile)
      // mineral speckle
      for (let i = 0; i < 1500; i += 1) {
        const light = random() > 0.5
        context.fillStyle = light
          ? `rgba(235,230,214,${0.02 + random() * 0.05})`
          : `rgba(30,32,28,${0.02 + random() * 0.05})`
        const dot = 0.6 + random() * 1.6
        context.fillRect(x + random() * tile, y + random() * tile, dot, dot)
      }
      // occasional veins
      if (random() > 0.5) {
        context.strokeStyle = `rgba(52,54,48,${0.06 + random() * 0.06})`
        context.lineWidth = 1 + random() * 1.4
        context.beginPath()
        let vy = y + random() * tile
        context.moveTo(x, vy)
        for (let vx = 0; vx <= tile; vx += 24) {
          vy += (random() - 0.5) * 26
          context.lineTo(x + vx, vy)
        }
        context.stroke()
      }
      bumpContext.fillStyle = `rgb(${140 + Math.floor(random() * 30)},140,140)`
      bumpContext.fillRect(x + 2, y + 2, tile - 4, tile - 4)
    }
  }
  // grout lines
  context.fillStyle = 'rgba(26,28,24,0.85)'
  bumpContext.fillStyle = '#141414'
  for (let i = 0; i <= 4; i += 1) {
    context.fillRect(0, i * tile - 2, size, 4)
    context.fillRect(i * tile - 2, 0, 4, size)
    bumpContext.fillRect(0, i * tile - 3, size, 6)
    bumpContext.fillRect(i * tile - 3, 0, 6, size)
  }
  // subtle polish sheen variation
  for (let i = 0; i < 18; i += 1) {
    const gradient = context.createRadialGradient(random() * size, random() * size, 0, random() * size, random() * size, 90 + random() * 160)
    gradient.addColorStop(0, `rgba(255,252,240,${0.015 + random() * 0.02})`)
    gradient.addColorStop(1, 'rgba(255,252,240,0)')
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

/** Dark acoustic ceiling panels. */
function makeCeilingTexture() {
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const random = mulberry32(77)
  context.fillStyle = '#131412'
  context.fillRect(0, 0, size, size)
  context.strokeStyle = 'rgba(0,0,0,0.6)'
  context.lineWidth = 3
  for (let i = 0; i <= 4; i += 1) {
    context.beginPath(); context.moveTo(0, i * 128); context.lineTo(size, i * 128); context.stroke()
    context.beginPath(); context.moveTo(i * 128, 0); context.lineTo(i * 128, size); context.stroke()
  }
  for (let i = 0; i < 9000; i += 1) {
    const shade = 14 + Math.floor(random() * 22)
    context.fillStyle = `rgba(${shade},${shade},${shade},0.35)`
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
  gradient.addColorStop(0, 'rgba(0,0,0,0.5)')
  gradient.addColorStop(0.62, 'rgba(0,0,0,0.28)')
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

  if (!text) {
    context.strokeStyle = selected ? 'rgba(183,145,85,0.9)' : 'rgba(242,235,221,0.22)'
    context.lineWidth = Math.max(1, px(0.002))
    context.strokeRect(1, 1, width - 2, height - 2)
    const tick = Math.min(20, height * 0.16, width * 0.04)
    context.strokeStyle = selected ? '#b79155' : 'rgba(242,235,221,0.55)'
    context.lineWidth = Math.max(1.5, px(0.003))
    for (const [x, y, sx, sy] of [[0, 0, 1, 1], [width, 0, -1, 1], [0, height, 1, -1], [width, height, -1, -1]] as const) {
      context.beginPath()
      context.moveTo(x, y + sy * tick)
      context.lineTo(x, y)
      context.lineTo(x + sx * tick, y)
      context.stroke()
    }
    if (showLabels) {
      const fontSize = clamp(px(0.032), 12, 25)
      context.font = `500 ${fontSize}px "SFMono-Regular", Consolas, monospace`
      context.fillStyle = selected ? 'rgba(211,176,117,0.95)' : 'rgba(242,235,221,0.52)'
      context.textAlign = 'left'
      context.textBaseline = 'top'
      const label = `[${zone.label}]`
      context.fillText(label, px(0.035), px(0.03), width - px(0.07))
    }
  } else {
    const worldSizes = { title: 0.26, verticalTitle: 0.3, subtitle: 0.04, body: 0.032, section: 0.09, object: 0.07, caption: 0.026, meta: 0.018 }
    const size = px(worldSizes[zone.style])
    const serif = zone.style === 'title' || zone.style === 'verticalTitle' || zone.style === 'object' || zone.style === 'section'
    context.font = `${serif ? 500 : 400} ${size}px ${serif ? 'Georgia, "Songti SC", serif' : 'Inter, Helvetica, "PingFang SC", sans-serif'}`
    context.fillStyle = '#f2ebdd'
    context.textBaseline = 'top'
    if (zone.style === 'verticalTitle') {
      const characters = [...text.replace(/\s/g, '')].slice(0, zone.chars ?? 8)
      const lineHeight = Math.min(size * 1.12, height / Math.max(characters.length, 1))
      context.textAlign = 'center'
      characters.forEach((character, index) => context.fillText(character, width / 2, Math.max(0, (height - lineHeight * characters.length) / 2 + index * lineHeight)))
    } else {
      const padding = px(0.012)
      const lines = textLines(context, text, width - padding * 2).slice(0, zone.lines)
      const lineHeight = size * (zone.style === 'body' || zone.style === 'caption' ? 1.5 : 1.18)
      context.textAlign = zone.align
      const x = zone.align === 'center' ? width / 2 : zone.align === 'right' ? width - padding : padding
      lines.forEach((line, index) => context.fillText(line, x, padding + index * lineHeight))
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
  new THREE.MeshStandardMaterial({ color: '#6e5638', metalness: 0.9, roughness: 0.4, envMapIntensity: 1.1 }),
  new THREE.MeshStandardMaterial({ color: '#e9e2d2', metalness: 0.02, roughness: 0.24, envMapIntensity: 0.9 }),
  new THREE.MeshStandardMaterial({ color: '#7ba08a', metalness: 0.05, roughness: 0.32, envMapIntensity: 1.0 }),
  new THREE.MeshStandardMaterial({ color: '#5a2320', metalness: 0.1, roughness: 0.16, envMapIntensity: 1.2 }),
  new THREE.MeshStandardMaterial({ color: '#b3ac9c', metalness: 0.02, roughness: 0.72, envMapIntensity: 0.4 }),
  new THREE.MeshStandardMaterial({ color: '#c7d6d0', metalness: 0.05, roughness: 0.1, transparent: true, opacity: 0.6, envMapIntensity: 1.4 }),
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
    this.scene.background = new THREE.Color('#11130f')
    this.scene.fog = new THREE.FogExp2('#11130f', 0.02)
    this.camera = new THREE.PerspectiveCamera(52, 1, 0.05, 60)
    this.camera.rotation.order = 'YXZ'
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 0.92
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    this.renderer.domElement.className = 'wall-canvas'
    this.renderer.domElement.setAttribute('aria-label', 'Interactive continuous museum entrance wall')
    container.appendChild(this.renderer.domElement)
    RectAreaLightUniformsLib.init()

    // Neutral HDRI-style environment for convincing metal / glass / floor reflections.
    const pmrem = new THREE.PMREMGenerator(this.renderer)
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
    this.scene.environmentIntensity = 0.22
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
      bumpScale: 0.9,
      color: '#ffffff',
      roughness: 0.94,
      envMapIntensity: 0.12,
    })
    const floorTextures = makeFloorTextures()
    const floorMaterial = new THREE.MeshStandardMaterial({
      map: floorTextures.map,
      bumpMap: floorTextures.bumpMap,
      bumpScale: 0.35,
      color: '#c9c7bc',
      roughness: 0.24,
      metalness: 0.06,
      envMapIntensity: 0.85,
    })
    const ceilingMaterial = new THREE.MeshStandardMaterial({ map: makeCeilingTexture(), color: '#b9bab4', roughness: 0.96, envMapIntensity: 0.05 })
    const stoneMaterial = new THREE.MeshStandardMaterial({ map: makeStoneTexture(), color: '#ddd6c8', roughness: 0.58, envMapIntensity: 0.3 })
    const brassMaterial = new THREE.MeshStandardMaterial({ color: '#9a7440', metalness: 1.0, roughness: 0.3, envMapIntensity: 1.3 })
    const darkMaterial = new THREE.MeshStandardMaterial({ color: '#11120f', roughness: 0.85 })
    const trimMaterial = new THREE.MeshStandardMaterial({ color: '#191a1c', roughness: 0.38, metalness: 0.25, envMapIntensity: 0.6 })
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
    const sideMaterial = new THREE.MeshStandardMaterial({ color: '#23261f', roughness: 0.92, envMapIntensity: 0.08 })
    const sideLeft = this.mesh(new THREE.PlaneGeometry(6, 3.4), sideMaterial, [0, 1.7, 1.7])
    sideLeft.rotation.y = Math.PI / 2
    const sideRight = this.mesh(new THREE.PlaneGeometry(6, 3.4), sideMaterial, [18, 1.7, 1.7])
    sideRight.rotation.y = -Math.PI / 2
    const entryFrame = this.mesh(new THREE.BoxGeometry(0.14, 3.4, 0.5), darkMaterial, [0.07, 1.7, -0.05])
    entryFrame.castShadow = true

    // skirting + crown shadow gap + datum line
    this.mesh(new THREE.BoxGeometry(18, 0.12, 0.03), trimMaterial, [9, 0.06, 0.016])
    this.mesh(new THREE.BoxGeometry(18, 0.05, 0.02), darkMaterial, [9, 3.36, 0.012])
    this.mesh(new THREE.BoxGeometry(18, 0.005, 0.008), new THREE.MeshBasicMaterial({ color: '#141414' }), [9, 1.35, 0.009])
    this.mesh(new THREE.BoxGeometry(0.04, 0.04, 0.009), new THREE.MeshBasicMaterial({ color: '#9e2b25' }), [0.04, 1.35, 0.013])
    this.mesh(new THREE.BoxGeometry(0.02, 1.9, 0.025), new THREE.MeshBasicMaterial({ color: '#050605' }), [17.99, 1.35, 0.014])
    this.mesh(new THREE.BoxGeometry(18, 0.008, 0.016), darkMaterial, [9, 0.132, 0.014])
    this.mesh(new THREE.BoxGeometry(18, 0.02, 0.025), brassMaterial, [9, 1.52, 0.028])

    // pilasters with cap and foot
    const pilasterMaterial = new THREE.MeshStandardMaterial({ color: '#363b32', roughness: 0.93, envMapIntensity: 0.1 })
    for (const x of [4.2, 6.2, 8.2, 10.2, 12.2, 14.2, 16.2]) {
      this.mesh(new THREE.BoxGeometry(0.12, 3.4, 0.06), pilasterMaterial, [x, 1.7, 0.03])
      this.mesh(new THREE.BoxGeometry(0.18, 0.06, 0.1), pilasterMaterial, [x, 3.31, 0.04])
      this.mesh(new THREE.BoxGeometry(0.18, 0.1, 0.1), pilasterMaterial, [x, 0.17, 0.04])
      this.mesh(new THREE.BoxGeometry(0.16, 0.012, 0.09), brassMaterial, [x, 3.27, 0.045])
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
    const floorBlobMaterial = new THREE.MeshBasicMaterial({ map: blobTexture, transparent: true, opacity: 0.55, depthWrite: false })
    const floorBlob = this.mesh(new THREE.PlaneGeometry(13.2, 2.2), floorBlobMaterial, [10.2, 0.002, 0.62])
    floorBlob.rotation.x = -Math.PI / 2
    const wallBlob = this.mesh(new THREE.PlaneGeometry(12.3, 0.5), floorBlobMaterial.clone(), [10.2, 0.28, 0.004])
    wallBlob.material.opacity = 0.4

    // cove light strip + track
    this.mesh(new THREE.BoxGeometry(18, 0.12, 0.1), new THREE.MeshStandardMaterial({ color: '#ffd6a0', emissive: '#ffc27a', emissiveIntensity: 2.1 }), [9, 3.25, 0.075])
    this.mesh(new THREE.BoxGeometry(18, 0.06, 0.06), darkMaterial, [9, 3.31, 1.3])

    const coneMaterial = new THREE.MeshBasicMaterial({
      color: '#ffdcae',
      transparent: true,
      opacity: 0.02,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
      fog: false,
    })
    for (let i = 1; i <= 6; i += 1) {
      const x = 4.2 + (i - 0.5) * 2
      const fixture = this.mesh(new THREE.CylinderGeometry(0.045, 0.055, 0.12, 16), darkMaterial, [x, 3.22, 1.3])
      fixture.rotation.x = -0.35
      const spot = new THREE.SpotLight('#ffe0b0', 9, 4.6, 0.34, 0.6, 1.6)
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

    const washer = new THREE.RectAreaLight('#ffddb0', 3.4, 18, 0.12)
    washer.position.set(9, 3.23, 0.16)
    washer.lookAt(9, 1.2, 0)
    this.scene.add(washer)
    const titleLight = new THREE.RectAreaLight('#ffe1b8', 1.8, 4.2, 0.15)
    titleLight.position.set(2.1, 3.18, 0.5)
    titleLight.lookAt(2.1, 1.8, 0)
    this.scene.add(titleLight)
    const fill = new THREE.HemisphereLight('#d8cdb4', '#191b17', 0.3)
    this.scene.add(fill)
    const shadowLight = new THREE.DirectionalLight('#ffddad', 1.1)
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
      color: '#ffe9c8',
      size: 0.011,
      transparent: true,
      opacity: 0.3,
      blending: THREE.AdditiveBlending,
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
    this.renderer.toneMappingExposure = 0.92 * fade
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
      this.renderer.toneMappingExposure = 0.92
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
