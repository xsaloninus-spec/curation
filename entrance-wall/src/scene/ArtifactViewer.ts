import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'

export type ViewerStatus = 'loading' | 'ready' | 'error'

interface ArtifactViewerOptions {
  onStatus?: (status: ViewerStatus) => void
  /** Y rotation in degrees applied before fitting (fixes off-axis exports). */
  rotationY?: number
}

const HOME_POSITION = new THREE.Vector3(1.45, 0.85, 2.1)
const HOME_TARGET = new THREE.Vector3(0, 0.02, 0)
const clamp = THREE.MathUtils.clamp
/** Soft radial dark gradient used to ground the object. */
function makeGroundTexture() {
  const size = 512
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const context = canvas.getContext('2d')!
  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  gradient.addColorStop(0, 'rgba(0,0,0,0.55)')
  gradient.addColorStop(0.55, 'rgba(0,0,0,0.28)')
  gradient.addColorStop(1, 'rgba(0,0,0,0)')
  context.fillStyle = gradient
  context.fillRect(0, 0, size, size)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

/**
 * Self-contained 360° inspection viewer for a single artifact.
 * Damped orbit controls, pinch / wheel zoom limits, idle auto-rotation,
 * museum-style lighting with a contact shadow, and full resource disposal.
 */
export class ArtifactViewer {
  private container: HTMLElement
  private options: ArtifactViewerOptions
  private renderer: THREE.WebGLRenderer
  private scene = new THREE.Scene()
  private camera: THREE.PerspectiveCamera
  private controls: OrbitControls
  private resizeObserver: ResizeObserver
  private pmrem: THREE.PMREMGenerator
  private animationId = 0
  private disposed = false
  private autoRotateWanted = true
  private idleTimer = 0
  private model: THREE.Group | null = null
  private modelRadius = 1
  private homePosition = HOME_POSITION.clone()
  private homeTarget = HOME_TARGET.clone()

  constructor(container: HTMLElement, url: string, options: ArtifactViewerOptions = {}) {
    this.container = container
    this.options = options
    options.onStatus?.('loading')

    this.scene.background = new THREE.Color('#131511')
    this.camera = new THREE.PerspectiveCamera(42, 1, 0.02, 60)
    this.camera.position.copy(this.homePosition)

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 1.0
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    this.renderer.domElement.className = 'artifact-canvas'
    container.appendChild(this.renderer.domElement)

    this.pmrem = new THREE.PMREMGenerator(this.renderer)
    this.scene.environment = this.pmrem.fromScene(new RoomEnvironment(), 0.04).texture
    this.scene.environmentIntensity = 0.45

    this.buildStage()

    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.07
    this.controls.minDistance = 0.6
    this.controls.maxDistance = 7
    this.controls.minPolarAngle = 0.05
    this.controls.maxPolarAngle = Math.PI - 0.05
    this.controls.autoRotate = true
    this.controls.autoRotateSpeed = 1.4
    this.controls.target.copy(this.homeTarget)
    this.controls.addEventListener('start', this.onControlStart)
    this.controls.addEventListener('end', this.onControlEnd)

    this.resizeObserver = new ResizeObserver(() => this.resize())
    this.resizeObserver.observe(container)
    this.resize()

    void this.load(url)
    this.animate()
  }

  private buildStage() {
    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(2.4, 48),
      new THREE.MeshBasicMaterial({ map: makeGroundTexture(), transparent: true, depthWrite: false }),
    )
    ground.rotation.x = -Math.PI / 2
    ground.position.y = -0.7
    this.scene.add(ground)

    const shadowPlane = new THREE.Mesh(
      new THREE.CircleGeometry(1.7, 48),
      new THREE.ShadowMaterial({ opacity: 0.42 }),
    )
    shadowPlane.rotation.x = -Math.PI / 2
    shadowPlane.position.y = -0.69
    shadowPlane.receiveShadow = true
    this.scene.add(shadowPlane)

    const key = new THREE.SpotLight('#ffe3bb', 140, 0, 0.55, 0.5, 2)
    key.position.set(2.4, 3.1, 1.6)
    key.castShadow = true
    key.shadow.mapSize.set(1024, 1024)
    key.shadow.bias = -0.0002
    key.shadow.radius = 4
    this.scene.add(key, key.target)

    const rim = new THREE.DirectionalLight('#b8c8e8', 1.6)
    rim.position.set(-2.2, 1.4, -2.4)
    this.scene.add(rim)

    const fill = new THREE.HemisphereLight('#d9cfba', '#15170f', 0.5)
    this.scene.add(fill)
  }

  private async load(url: string) {
    try {
      const gltf = await new GLTFLoader().loadAsync(url)
      if (this.disposed) return
      let source: THREE.Object3D = gltf.scene
      if (this.options.rotationY) {
        const pivot = new THREE.Group()
        source.rotation.y = THREE.MathUtils.degToRad(this.options.rotationY)
        pivot.add(source)
        source = pivot
      }
      source.updateMatrixWorld(true)
      const box = new THREE.Box3().setFromObject(source)
      if (box.isEmpty()) throw new Error('empty')
      const size = box.getSize(new THREE.Vector3())
      const center = box.getCenter(new THREE.Vector3())
      const scale = 1.3 / Math.max(size.x, size.y, size.z)
      this.modelRadius = Math.max(size.x, size.y, size.z) * scale * 0.5
      source.scale.setScalar(scale)
      source.position.set(-center.x * scale, -box.min.y * scale - 0.7, -center.z * scale)
      this.model = new THREE.Group()
      this.model.add(source)
      this.model.traverse(child => {
        if (child instanceof THREE.Mesh) { child.castShadow = true; child.receiveShadow = true }
      })
      this.scene.add(this.model)
      // aim the camera rig at the model's actual vertical centre (flat objects
      // like mirrors sit almost entirely on the ground plane otherwise)
      const wrapped = new THREE.Box3().setFromObject(this.model)
      const centre = wrapped.getCenter(new THREE.Vector3())
      const lift = centre.y - this.homeTarget.y
      this.homeTarget.y += lift
      this.homePosition.y += lift
      this.controls.target.copy(this.homeTarget)
      this.camera.position.copy(this.homePosition)
      this.controls.minDistance = Math.max(0.25, this.modelRadius * 0.55)
      this.controls.maxDistance = this.modelRadius * 5 + 2
      this.options.onStatus?.('ready')
    } catch {
      if (!this.disposed) this.options.onStatus?.('error')
    }
  }

  private onControlStart = () => {
    this.controls.autoRotate = false
    window.clearTimeout(this.idleTimer)
  }

  private onControlEnd = () => {
    window.clearTimeout(this.idleTimer)
    this.idleTimer = window.setTimeout(() => {
      if (!this.disposed && this.autoRotateWanted) this.controls.autoRotate = true
    }, 2600)
  }

  private resize() {
    const width = Math.max(this.container.clientWidth, 1)
    const height = Math.max(this.container.clientHeight, 1)
    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(width, height, false)
  }

  private animate = () => {
    if (this.disposed) return
    this.animationId = requestAnimationFrame(this.animate)
    this.controls.update()
    this.renderer.render(this.scene, this.camera)
  }

  setAutoRotate(enabled: boolean) {
    this.autoRotateWanted = enabled
    this.controls.autoRotate = enabled
  }

  getAutoRotate() { return this.autoRotateWanted }

  zoomBy(factor: number) {
    const offset = this.camera.position.clone().sub(this.controls.target)
    const distance = clamp(offset.length() * factor, this.controls.minDistance, this.controls.maxDistance)
    offset.setLength(distance)
    this.camera.position.copy(this.controls.target).add(offset)
  }

  rotateBy(deltaX: number, deltaY: number) {
    const offset = this.camera.position.clone().sub(this.controls.target)
    const spherical = new THREE.Spherical().setFromVector3(offset)
    spherical.theta -= deltaX * 0.008
    spherical.phi = clamp(spherical.phi - deltaY * 0.008, this.controls.minPolarAngle, this.controls.maxPolarAngle)
    offset.setFromSpherical(spherical)
    this.camera.position.copy(this.controls.target).add(offset)
    this.camera.lookAt(this.controls.target)
  }

  resetView() {
    this.camera.position.copy(this.homePosition)
    this.controls.target.copy(this.homeTarget)
    this.controls.autoRotate = this.autoRotateWanted
    this.controls.update()
  }

  dispose() {
    this.disposed = true
    cancelAnimationFrame(this.animationId)
    window.clearTimeout(this.idleTimer)
    this.resizeObserver.disconnect()
    this.controls.removeEventListener('start', this.onControlStart)
    this.controls.removeEventListener('end', this.onControlEnd)
    this.controls.dispose()
    this.scene.traverse(child => {
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
    this.pmrem.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
