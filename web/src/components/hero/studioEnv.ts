/**
 * Procedural reflection environment for the WebGL pieces.
 *
 * Both hero sculptures need a believable glossy-black surface to reflect, and
 * an environment map is what makes near-black metal read as metal rather than
 * as flat silhouette. There is no HDRI asset to load, so the environment is a
 * handful of emissive planes baked through PMREM at startup: a black void with
 * a few long light strips. One-time cost, no network, no file.
 *
 * The strips are the lighting rig, not decoration. Their placement is what puts
 * a long soft highlight along the top-left of every tube and a violet edge on the
 * far side, so the geometry appears to emerge from darkness rather than being
 * lit evenly.
 */
import * as THREE from "three";

/**
 * Build the baked environment texture for a renderer.
 *
 * The caller owns the returned texture and must dispose it.
 */
export function buildStudioEnvironment(renderer: THREE.WebGLRenderer): THREE.Texture {
  const env = new THREE.Scene();
  env.background = new THREE.Color(0x010102);

  const strip = (
    w: number,
    h: number,
    color: THREE.Color,
    pos: [number, number, number],
    rot: [number, number, number]
  ) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide })
    );
    m.position.set(...pos);
    m.rotation.set(...rot);
    env.add(m);
  };

  // Key strip - large soft white overhead-left
  strip(10, 2.4, new THREE.Color(5.5, 5.5, 5.8), [-5, 6, 3], [-0.5, 0.5, 0.15]);
  // Long thin white rim strip right
  strip(0.7, 9, new THREE.Color(4.2, 4.4, 4.8), [6.5, 0.5, -1], [0, -1.05, 0]);
  // Deep blue wash low-left
  strip(7, 1.6, new THREE.Color(0.35, 0.62, 2.6), [-4.5, -4.2, -2.5], [0.6, 0.6, 0]);
  // Violet accent behind
  strip(5, 1.1, new THREE.Color(1.35, 0.8, 3.2), [2.5, 3.2, -6], [0.15, -0.35, 0]);
  // Faint neutral floor bounce
  strip(12, 3, new THREE.Color(0.5, 0.52, 0.6), [0, -7, 1.5], [1.35, 0, 0]);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const rt = pmrem.fromScene(env, 0.05);
  pmrem.dispose();
  // The scene and its geometries are only inputs to the bake.
  env.traverse((o) => {
    if (o instanceof THREE.Mesh) {
      o.geometry.dispose();
      (o.material as THREE.Material).dispose();
    }
  });
  return rt.texture;
}