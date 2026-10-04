// ---------------------------------------------------------------------------
// Sieve scene (three.js), shared by the landing hero and the inbox strip.
//
// Email cards drift in from the left as a loose, tumbling cloud, pass through
// a glowing ring (the model), and leave on the right in their label colour,
// lined up in one lane per label: chaos in, order out.
//
//   const scene = await createSieveScene(container, {variant, cards, seed})
//     variant  "hero" | "strip"
//     cards    [{label, color}]   one card per email
//   scene.focus("spam" | null)    grey out every other label
//   scene.dispose()
// ---------------------------------------------------------------------------
const THREE_URL = "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js";
let _threePromise = null;
const loadThree = () => (_threePromise ||= import(THREE_URL));

const LANES = ["spam", "suspicious", "promotion", "update", "safe"];
const NEUTRAL = [0.93, 0.93, 0.94];   // card colour before it reaches the model
const DIM = [0.80, 0.80, 0.82];       // card colour when another label is focused

function seeded(seed) {               // deterministic: the same picture every load
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}
const hexToRgb = (hex) => {
  const n = parseInt(hex.replace("#", ""), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
};
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const easeOut = (t) => 1 - Math.pow(1 - t, 3);
const lerp = (a, b, t) => a + (b - a) * t;

function envelopeTexture(THREE) {
  const W = 160, H = 112, r = 14, c = document.createElement("canvas");
  c.width = W; c.height = H;
  const g = c.getContext("2d");
  g.beginPath(); g.roundRect(3, 3, W - 6, H - 6, r);
  g.fillStyle = "#ffffff"; g.fill();
  g.lineWidth = 3; g.strokeStyle = "rgba(20,20,22,.22)"; g.stroke();
  g.beginPath(); g.moveTo(12, 14); g.lineTo(W / 2, H * 0.58); g.lineTo(W - 12, 14);
  g.lineWidth = 3; g.strokeStyle = "rgba(20,20,22,.18)"; g.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function glowTexture(THREE) {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, "rgba(255,255,255,1)");
  grd.addColorStop(0.35, "rgba(255,255,255,.45)");
  grd.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

// Ring: a warm metallic hoop with a highlight running around it.
const RING_VERT = /* glsl */`
  varying vec2 vUv; varying vec3 vN; varying vec3 vView;
  void main() {
    vUv = uv;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vN = normalize(normalMatrix * normal); vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }`;
const RING_FRAG = /* glsl */`
  uniform float uTime; varying vec2 vUv; varying vec3 vN; varying vec3 vView;
  void main() {
    float rim = pow(1.0 - abs(dot(vN, vView)), 2.0);
    float run = pow(0.5 + 0.5 * cos((vUv.x - uTime * 0.12) * 6.2832), 10.0);
    vec3 base = mix(vec3(0.16, 0.12, 0.09), vec3(0.95, 0.62, 0.22), 0.35 + 0.65 * rim);
    vec3 col = base + vec3(1.0, 0.78, 0.42) * run * 0.9;
    gl_FragColor = vec4(col, 1.0);
  }`;
// Membrane: the faint lens inside the ring with a scan line sweeping across.
const MEM_FRAG = /* glsl */`
  uniform float uTime; varying vec2 vUv;
  void main() {
    vec2 p = vUv - 0.5; float d = length(p) * 2.0;
    float edge = smoothstep(0.55, 1.0, d) * (1.0 - smoothstep(0.98, 1.0, d));
    float scan = exp(-pow((p.y - (fract(uTime * 0.18) - 0.5)) * 40.0, 2.0)) * (1.0 - smoothstep(0.9, 1.0, d));
    float a = edge * 0.35 + scan * 0.35;
    gl_FragColor = vec4(vec3(1.0, 0.72, 0.32), a);
  }`;

async function createSieveScene(container, { variant = "hero", cards = [], seed = 7 }) {
  const THREE = await loadThree();
  const hero = variant === "hero";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.domElement.style.cssText = "position:absolute;inset:0;width:100%;height:100%;display:block";
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(hero ? 34 : 28, 1, 0.1, 100);
  camera.position.set(0, 0, hero ? 8 : 7);
  const group = new THREE.Group();
  scene.add(group);

  const envTex = envelopeTexture(THREE), glowTex = glowTexture(THREE);
  const cardGeo = new THREE.PlaneGeometry(1, 0.7);
  const cardMat = new THREE.MeshBasicMaterial({ map: envTex, transparent: true, side: THREE.DoubleSide, depthWrite: false });
  const mesh = new THREE.InstancedMesh(cardGeo, cardMat, Math.max(cards.length, 1));
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.count = cards.length;
  group.add(mesh);

  const ringMat = new THREE.ShaderMaterial({ vertexShader: RING_VERT, fragmentShader: RING_FRAG, uniforms: { uTime: { value: 0 } } });
  const memMat = new THREE.ShaderMaterial({ vertexShader: RING_VERT, fragmentShader: MEM_FRAG, uniforms: { uTime: { value: 0 } }, transparent: true, depthWrite: false, side: THREE.DoubleSide });
  const ring = new THREE.Group();
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xffb347, transparent: true, opacity: hero ? 0.55 : 0.4, depthWrite: false }));
  group.add(halo, ring);

  // layout (recomputed on resize)
  const L = {};
  const rnd = seeded(seed);
  const cardsState = cards.map((c) => ({
    label: c.label, color: hexToRgb(c.color), lane: Math.max(0, LANES.indexOf(c.label)),
    u: rnd(), speed: 0.028 + rnd() * 0.03,
    cloudY: rnd() * 2 - 1, cloudZ: rnd() * 2 - 1, passY: rnd() * 2 - 1, passZ: rnd() * 2 - 1,
    laneJ: rnd() * 2 - 1, spin: rnd() * 6.28, size: 0.85 + rnd() * 0.3, dim: 0,
  }));

  function layout() {
    const w = container.clientWidth || 1, h = container.clientHeight || 1;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    const halfH = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.position.z;
    const halfW = halfH * camera.aspect;
    const narrow = halfW < halfH * 1.2;
    Object.assign(L, { halfW, halfH });
    if (hero) {
      // The scene lives in the upper ~60% of the hero; text sits below it.
      L.R = Math.min(halfH * 0.36, halfW * 0.3);
      L.ringX = narrow ? 0 : halfW * 0.06;
      L.ringY = narrow ? halfH * 0.4 : halfH * 0.26;
      L.xStart = -halfW - 1; L.xEnd = halfW + 1;
      L.cloud = halfH * (narrow ? 0.35 : 0.55);
      L.laneY = (i) => L.ringY + L.R * (0.62 - 0.36 * i);   // five lanes, clear of the nav
      L.laneSpread = L.R * 0.12;
      L.card = L.R * 0.21;
    } else {
      L.R = halfH * 0.62;
      L.ringX = -halfW * 0.12;
      L.ringY = 0;
      L.xStart = -halfW - 0.8; L.xEnd = halfW * 0.5;    // stop before the lane labels
      L.cloud = halfH * 0.9;
      L.laneY = (i) => halfH * (0.68 - 0.34 * i);        // matches the HTML lane labels
      L.laneSpread = halfH * 0.05;
      L.card = halfH * 0.17;
    }
    ring.traverse((o) => o.geometry?.dispose());
    ring.clear();
    const torus = new THREE.Mesh(new THREE.TorusGeometry(L.R, L.R * 0.045, 24, 160), ringMat);
    const mem = new THREE.Mesh(new THREE.CircleGeometry(L.R * 0.98, 96), memMat);
    ring.add(torus, mem);
    ring.position.set(L.ringX, L.ringY, 0);
    ring.rotation.set(0, hero ? 1.05 : 1.15, 0);   // seen at an angle: a hoop the stream passes through
    halo.position.set(L.ringX, L.ringY, -0.6);
    halo.scale.set(L.R * 4.2, L.R * 3.4, 1);
  }
  layout();

  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  const pos = new THREE.Vector3(), scl = new THREE.Vector3(), col = new THREE.Color();
  let focus = null;

  function place(t, dt) {
    cardsState.forEach((c, i) => {
      c.u = (c.u + dt * c.speed) % 1;
      const x = lerp(L.xStart, L.xEnd, c.u);
      let y, z, rot, mix;
      if (x < L.ringX) {   // approaching: wide cloud funnelling into the ring
        const s = smooth(L.xStart, L.ringX, x);
        y = lerp(L.ringY + c.cloudY * L.cloud, L.ringY + c.passY * L.R * 0.55, s);
        z = lerp(c.cloudZ * 1.6, c.passZ * L.R * 0.3, s);
        rot = (1 - s) * 0.9;
      } else {             // leaving: settle into the label lane
        const s = easeOut(Math.min(1, (x - L.ringX) / ((L.xEnd - L.ringX) * 0.7)));
        y = lerp(L.ringY + c.passY * L.R * 0.55, L.laneY(c.lane) + c.laneJ * L.laneSpread, s);
        z = lerp(c.passZ * L.R * 0.3, 0, s);
        rot = (1 - s) * 0.25;
      }
      mix = smooth(L.ringX - L.R * 0.05, L.ringX + L.R * 0.35, x);
      const fade = smooth(0, 0.05, c.u) * (1 - smooth(0.95, 1, c.u));
      const sz = L.card * c.size * fade;
      e.set(Math.sin(t * 0.7 + c.spin) * rot * 0.8, Math.cos(t * 0.5 + c.spin) * rot, Math.sin(t * 0.9 + c.spin) * rot * 0.6);
      q.setFromEuler(e);
      pos.set(x, y, z); scl.set(sz, sz, sz);
      m4.compose(pos, q, scl);
      mesh.setMatrixAt(i, m4);

      const want = focus && c.label !== focus ? 1 : 0;
      c.dim += (want - c.dim) * 0.12;
      const tint = c.color.map((v) => lerp(1, v, 0.82));          // label colour, a touch lighter
      const r = lerp(NEUTRAL[0], tint[0], mix), g = lerp(NEUTRAL[1], tint[1], mix), b = lerp(NEUTRAL[2], tint[2], mix);
      col.setRGB(lerp(r, DIM[0], c.dim), lerp(g, DIM[1], c.dim), lerp(b, DIM[2], c.dim), THREE.SRGBColorSpace);
      mesh.setColorAt(i, col);
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }

  // pointer parallax
  const target = { x: 0, y: 0 };
  const onMove = (ev) => {
    const r = container.getBoundingClientRect();
    target.x = ((ev.clientX - r.left) / r.width - 0.5) * 2;
    target.y = ((ev.clientY - r.top) / r.height - 0.5) * 2;
  };
  window.addEventListener("pointermove", onMove, { passive: true });

  let visible = true, raf = 0, last = performance.now() / 1000;
  const clock = new THREE.Clock();
  function frame(dt) {
    const t = clock.getElapsedTime();
    ringMat.uniforms.uTime.value = memMat.uniforms.uTime.value = t;
    group.rotation.y += (target.x * 0.08 - group.rotation.y) * 0.05;
    group.rotation.x += (target.y * 0.05 - group.rotation.x) * 0.05;
    place(t, dt);
    renderer.render(scene, camera);
  }
  function tick() {
    raf = 0;
    if (!visible) return;
    const now = performance.now() / 1000;
    frame(Math.min(0.05, now - last));
    last = now;
    raf = requestAnimationFrame(tick);
  }
  const io = new IntersectionObserver(([en]) => {
    visible = en.isIntersecting;
    if (visible && !raf && !reduced) { last = performance.now() / 1000; raf = requestAnimationFrame(tick); }
  });
  io.observe(container);
  let resizeTimer = 0;
  const ro = new ResizeObserver(() => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { layout(); frame(0); }, 100);
  });
  ro.observe(container);

  if (reduced) frame(0); else raf = requestAnimationFrame(tick);

  return {
    focus(label) { focus = label; if (reduced) { cardsState.forEach((c) => (c.dim = focus && c.label !== focus ? 1 : 0)); frame(0); } },
    dispose() {
      cancelAnimationFrame(raf); io.disconnect(); ro.disconnect(); clearTimeout(resizeTimer);
      window.removeEventListener("pointermove", onMove);
      ring.traverse((o) => o.geometry?.dispose());
      cardGeo.dispose(); cardMat.dispose(); ringMat.dispose(); memMat.dispose();
      halo.material.dispose(); envTex.dispose(); glowTex.dispose();
      renderer.dispose(); renderer.domElement.remove();
    },
  };
}
