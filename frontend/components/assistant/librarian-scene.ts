import {
  AnimationMixer,
  Mesh,
  OrthographicCamera,
  Scene,
  SkinnedMesh,
  Texture,
  TextureLoader,
  WebGLRenderer,
  type Group,
} from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export interface LibrarianScene {
  setVisible(visible: boolean): void;
}

function disposeCharacter(character: Group) {
  character.traverse((node) => {
    if (!(node instanceof Mesh)) return;
    node.geometry.dispose();
    if (node instanceof SkinnedMesh) node.skeleton.dispose();
    const materials = Array.isArray(node.material)
      ? node.material
      : [node.material];
    for (const material of materials) {
      if (material.map instanceof Texture) material.map.dispose();
      material.dispose();
    }
  });
}

export async function createLibrarianScene(
  element: HTMLElement,
  modelUrl: string,
  portraitAspect: number,
  signal: AbortSignal,
  onContextLost: () => void,
): Promise<LibrarianScene | null> {
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
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  let frame = 0;
  const dispose = () => {
    cancelAnimationFrame(frame);
    canvas.removeEventListener("webglcontextlost", onContextLost);
    canvas.remove();
    renderer.dispose();
    renderer.forceContextLoss();
  };
  signal.addEventListener("abort", dispose, { once: true });
  canvas.addEventListener("webglcontextlost", onContextLost);

  const response = await fetch(modelUrl, { signal });
  if (!response.ok) throw new Error("Librarian model unavailable");
  const loader = new GLTFLoader();
  loader.register((parser) => {
    // Embedded textures can load through img-src under the site's CSP.
    parser.textureLoader = new TextureLoader(loader.manager);
    return { name: "LoginPortraitTextures" };
  });
  const { scene: character, animations } = await loader.parseAsync(
    await response.arrayBuffer(),
    "",
  );
  if (signal.aborted) {
    disposeCharacter(character);
    return null;
  }

  const scene = new Scene();
  scene.add(character);
  const camera = new OrthographicCamera(-1, 1, 1, 0, 0.01, 6);
  camera.position.z = 3;
  const mixer = new AnimationMixer(character);
  for (const clip of animations) mixer.clipAction(clip).play();
  element.append(canvas);

  function resize() {
    const { width, height } = element.getBoundingClientRect();
    if (!width || !height) return;
    // The orthographic crop and bottom alignment match the static poster.
    const aspect = width / height;
    camera.top = Math.max(1, portraitAspect / aspect);
    camera.right = camera.top * aspect * 0.5;
    camera.left = -camera.right;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    renderer.render(scene, camera);
  }
  resize();
  const observer = new ResizeObserver(resize);
  observer.observe(element);
  signal.addEventListener(
    "abort",
    () => {
      observer.disconnect();
      mixer.uncacheRoot(character);
      disposeCharacter(character);
    },
    { once: true },
  );

  let previousTime = 0;
  function animate(now: number) {
    const elapsed = now - previousTime;
    if (elapsed >= 1000 / 30) {
      mixer.update(Math.min(elapsed / 1000, 0.1));
      renderer.render(scene, camera);
      previousTime = now;
    }
    frame = requestAnimationFrame(animate);
  }
  return {
    setVisible(visible) {
      if (visible && !frame && !signal.aborted) {
        previousTime = performance.now();
        frame = requestAnimationFrame(animate);
      } else if (!visible) {
        cancelAnimationFrame(frame);
        frame = 0;
      }
    },
  };
}
