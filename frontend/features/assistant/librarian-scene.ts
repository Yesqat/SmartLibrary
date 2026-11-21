import {
  AmbientLight,
  AnimationMixer,
  Box3,
  DirectionalLight,
  Group,
  LoopOnce,
  MathUtils,
  Mesh,
  OrthographicCamera,
  Scene,
  Texture,
  TextureLoader,
  Vector3,
  WebGLRenderer,
} from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export interface PortraitScene {
  rotate(degrees: number): void;
  greet(): void;
  setTyping(typing: boolean): void;
}

function disposeModel(model: Group) {
  const textures = new Set<Texture>();
  model.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    object.geometry.dispose();
    const materials = Array.isArray(object.material)
      ? object.material
      : [object.material];
    for (const material of materials) {
      for (const value of Object.values(material)) {
        if (value instanceof Texture) textures.add(value);
      }
      material.dispose();
    }
  });
  for (const texture of textures) {
    texture.dispose();
    if (
      typeof ImageBitmap !== "undefined" &&
      texture.image instanceof ImageBitmap
    ) {
      texture.image.close();
    }
  }
}

export async function createPortrait(
  element: HTMLElement,
  signal: AbortSignal,
  onContextLost: () => void,
): Promise<PortraitScene | null> {
  const canvas = document.createElement("canvas");
  const options = {
    alpha: true,
    antialias: true,
    powerPreference: "low-power",
  } as const;
  const context = canvas.getContext("webgl2", options);
  if (!(context instanceof WebGL2RenderingContext)) return null;

  const renderer = new WebGLRenderer({ canvas, context, ...options });
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  let frame = 0;
  function cleanup() {
    cancelAnimationFrame(frame);
    canvas.removeEventListener("webglcontextlost", onContextLost);
    canvas.remove();
    renderer.dispose();
    renderer.forceContextLoss();
  }
  signal.addEventListener("abort", cleanup, { once: true });
  canvas.addEventListener("webglcontextlost", onContextLost);

  // The GLB is self-contained. Abort the request if the reader leaves the page.
  const response = await fetch("/assistant/librarian.glb", { signal });
  if (!response.ok) throw new Error("Portrait asset unavailable");
  const loader = new GLTFLoader();
  loader.register((parser) => {
    // Embedded images are allowed by img-src. Decode them with <img> so they
    // never require a blob: fetch under the application's connect-src policy.
    parser.textureLoader = new TextureLoader(loader.manager);
    return { name: "PortraitTextures" };
  });
  const { scene: character, animations } = await loader.parseAsync(
    await response.arrayBuffer(),
    "",
  );
  if (signal.aborted) {
    disposeModel(character);
    return null;
  }
  signal.addEventListener("abort", () => disposeModel(character), {
    once: true,
  });

  const scene = new Scene();
  const pivot = new Group();
  // Frame the neutral bust, including while the animated arm is below the crop.
  const bounds = character.userData.portraitBounds;
  const box = bounds
    ? new Box3(
        new Vector3().fromArray(bounds.min),
        new Vector3().fromArray(bounds.max),
      )
    : new Box3().setFromObject(character);
  const size = box.getSize(new Vector3());
  character.position.sub(box.getCenter(new Vector3()));
  pivot.add(character);
  scene.add(pivot);

  const mixer = new AnimationMixer(character);
  const greetingClip = animations.find((clip) => clip.name === "Greeting");
  const greeting =
    greetingClip && mixer.clipAction(greetingClip).setLoop(LoopOnce, 1);
  const readingClip = animations.find((clip) => clip.name === "Reading");
  const reading = readingClip && mixer.clipAction(readingClip);
  if (reading) {
    // Sample this pose on demand, independent of the arm's one-shot clip.
    reading.paused = true;
    reading.play();
    mixer.update(0);
  }
  signal.addEventListener("abort", () => mixer.uncacheRoot(character), {
    once: true,
  });

  // The portrait texture contains its studio shadows. A soft key adds shape as it turns.
  scene.add(new AmbientLight(0xffffff, 2.8));
  const key = new DirectionalLight(0xfff7ec, 0.55);
  key.position.set(-2, 3, 4);
  scene.add(key);
  const camera = new OrthographicCamera(-1, 1, 1, -1, 0.01, 4 * size.length());
  camera.position.z = 2 * size.length();
  element.append(canvas);

  function resize() {
    const { width, height } = element.getBoundingClientRect();
    if (!width || !height) return;
    const aspect = width / height;
    // Match the closely cropped poster, including its hair and shoulder margins.
    const span = Math.max(size.y * 1.005, (size.x * 1.023) / aspect);
    const halfWidth = (span * aspect) / 2;
    // Give the raised elbow drawing room while keeping the face aligned with the poster.
    const extraWorld = Math.max(
      0,
      (character.userData.greetingLeftExtent ?? 0) - halfWidth,
    );
    const extraPixels = Math.ceil((extraWorld * height) / span);
    camera.left = -halfWidth - (extraPixels * span) / height;
    camera.right = halfWidth;
    camera.bottom = -size.y / 2;
    camera.top = camera.bottom + span;
    camera.updateProjectionMatrix();
    canvas.style.width = `${width + extraPixels}px`;
    canvas.style.marginLeft = `${-extraPixels}px`;
    renderer.setSize(width + extraPixels, height, false);
    renderer.render(scene, camera);
  }

  const observer = new ResizeObserver(resize);
  signal.addEventListener("abort", () => observer.disconnect(), { once: true });
  observer.observe(element);
  resize();

  let targetYaw = 0;
  let readingProgress = 0;
  let targetReading = 0;
  let previousTime = 0;

  function animate(time: number) {
    const elapsed = Math.max(0, (time - previousTime) / 1000);
    previousTime = time;
    pivot.rotation.y = MathUtils.damp(pivot.rotation.y, targetYaw, 17, elapsed);
    if (Math.abs(pivot.rotation.y - targetYaw) < 0.0005)
      pivot.rotation.y = targetYaw;
    if (reading && readingProgress !== targetReading) {
      const step = elapsed / 0.48;
      readingProgress = MathUtils.clamp(
        readingProgress + (targetReading ? step : -step),
        0,
        1,
      );
      reading.time =
        MathUtils.smoothstep(readingProgress, 0, 1) *
        reading.getClip().duration;
    }
    mixer.update(elapsed);
    renderer.render(scene, camera);
    frame =
      greeting?.isRunning() ||
      pivot.rotation.y !== targetYaw ||
      readingProgress !== targetReading
        ? requestAnimationFrame(animate)
        : 0;
  }

  function requestMovement() {
    if (frame) return;
    previousTime = performance.now();
    frame = requestAnimationFrame(animate);
  }
  return {
    rotate(degrees) {
      targetYaw = MathUtils.degToRad(MathUtils.clamp(degrees, -12, 12));
      if (targetYaw !== pivot.rotation.y) requestMovement();
    },
    greet() {
      if (!greeting) return;
      greeting.reset().play();
      requestMovement();
    },
    setTyping(typing) {
      if (!reading) return;
      targetReading = typing ? 1 : 0;
      if (readingProgress !== targetReading) requestMovement();
    },
  };
}
