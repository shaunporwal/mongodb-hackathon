import { Component, useEffect, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";

// Decorative WebGL layer; network data and hit targets remain in the SVG above it.
const vertexShader = /* glsl */ `
  uniform float uTime;
  varying vec3 vNormal;
  varying vec3 vViewPosition;

  float pseudoNoise(vec3 p, float t) {
    return sin(p.x * 2.0 + t) * cos(p.y * 2.3 - t * 0.7) * sin(p.z * 1.7 + t * 1.3);
  }

  void main() {
    vNormal = normalize(normalMatrix * normal);
    float n = pseudoNoise(position * 1.5, uTime * 0.6);
    vec3 displaced = position + normal * n * 0.09;
    vec4 mvPosition = modelViewMatrix * vec4(displaced, 1.0);
    vViewPosition = -mvPosition.xyz;
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = /* glsl */ `
  uniform float uTime;
  varying vec3 vNormal;
  varying vec3 vViewPosition;

  void main() {
    vec3 viewDir = normalize(vViewPosition);
    float fresnel = pow(1.0 - max(dot(normalize(vNormal), viewDir), 0.0), 2.2);

    vec3 red = vec3(1.0, 0.231, 0.188);
    vec3 blue = vec3(0.0, 0.478, 1.0);
    float mixFactor = 0.5 + 0.5 * sin(uTime * 0.3 + vNormal.x * 2.0);
    vec3 rim = mix(blue, red, mixFactor);

    vec3 base = vec3(0.02, 0.03, 0.07);
    vec3 color = base + rim * fresnel * 1.15;

    gl_FragColor = vec4(color, fresnel * 0.6 + 0.035);
  }
`;

function GlowSphere({ reducedMotion }) {
  const materialRef = useRef(null);
  const groupRef = useRef(null);
  const [uniforms] = useState(() => ({ uTime: { value: 0 } }));

  useFrame((_, delta) => {
    if (reducedMotion) return;
    if (!materialRef.current) return;
    const elapsed = materialRef.current.uniforms.uTime.value + Math.min(delta, 0.05);
    materialRef.current.uniforms.uTime.value = elapsed;
    if (groupRef.current) {
      groupRef.current.rotation.y = elapsed * 0.09;
      groupRef.current.rotation.z = Math.sin(elapsed * 0.12) * 0.08;
    }
  });

  return (
    <group ref={groupRef}>
      <mesh>
        <icosahedronGeometry args={[1.6, 4]} />
        <shaderMaterial
          ref={materialRef}
          uniforms={uniforms}
          vertexShader={vertexShader}
          fragmentShader={fragmentShader}
          transparent
        />
      </mesh>
      <mesh>
        <icosahedronGeometry args={[1.75, 2]} />
        <meshBasicMaterial color="#007AFF" wireframe transparent opacity={0.16} />
      </mesh>
      <group rotation={[0.7, 0.25, -0.4]}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[1.94, 0.006, 6, 160]} />
          <meshBasicMaterial color="#669AFF" transparent opacity={0.38} />
        </mesh>
        <mesh rotation={[0.4, 0.8, 0.5]}>
          <torusGeometry args={[1.87, 0.004, 6, 160]} />
          <meshBasicMaterial color="#FF604C" transparent opacity={0.26} />
        </mesh>
      </group>
    </group>
  );
}

class SceneBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? null : this.props.children; }
}

export function VoiceSphereScene() {
  const hostRef = useRef(null);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [visible, setVisible] = useState(true);
  const [pageVisible, setPageVisible] = useState(() => !document.hidden);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onMotion = () => setReducedMotion(query.matches);
    const onVisibility = () => setPageVisible(!document.hidden);
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting));
    if (hostRef.current) observer.observe(hostRef.current);
    query.addEventListener("change", onMotion);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      observer.disconnect();
      query.removeEventListener("change", onMotion);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);
  return (
    <div className="network-atmosphere" ref={hostRef} aria-hidden="true">
      <SceneBoundary>
        <Canvas
          camera={{ position: [0, 0, 5.6], fov: 45 }}
          dpr={[1, 1.5]}
          frameloop={reducedMotion || !visible || !pageVisible ? "demand" : "always"}
          gl={{ alpha: true, antialias: true, powerPreference: "low-power" }}
          fallback={null}
        >
          <GlowSphere reducedMotion={reducedMotion} />
        </Canvas>
      </SceneBoundary>
    </div>
  );
}
