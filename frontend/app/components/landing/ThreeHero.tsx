"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function ThreeHero() {
  const mountRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.z = 5;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    // Lighting
    const ambient = new THREE.AmbientLight(0x0C0C0E, 0.2);
    scene.add(ambient);

    // Orbiting red-pink point light
    const redLight = new THREE.PointLight(0xF43F5E, 2.0, 20);
    scene.add(redLight);

    // Static green counter-light
    const greenLight = new THREE.PointLight(0x4ADE80, 1.2, 20);
    greenLight.position.set(2, 1, 3);
    scene.add(greenLight);

    // Directional light
    const dirLight = new THREE.DirectionalLight(0x1A0A0E, 0.5);
    dirLight.position.set(3, 4, 2);
    scene.add(dirLight);

    // Shattered Icosphere — dark red-black metal shards
    const icoGeo = new THREE.IcosahedronGeometry(1.6, 2);
    const pos = icoGeo.attributes.position;
    const indices = icoGeo.index ? Array.from(icoGeo.index.array) : null;

    const group = new THREE.Group();
    const faceMeshes: THREE.Mesh[] = [];
    const faceCount = indices ? indices.length / 3 : pos.count / 3;

    for (let i = 0; i < faceCount; i++) {
      const verts: THREE.Vector3[] = [];
      const centroid = new THREE.Vector3();

      for (let j = 0; j < 3; j++) {
        const idx = indices ? indices[i * 3 + j] : i * 3 + j;
        const v = new THREE.Vector3(pos.getX(idx), pos.getY(idx), pos.getZ(idx));
        verts.push(v);
        centroid.add(v);
      }
      centroid.divideScalar(3);

      const geo = new THREE.BufferGeometry();
      const positions = new Float32Array(9);
      for (let j = 0; j < 3; j++) {
        positions[j * 3]     = verts[j].x - centroid.x;
        positions[j * 3 + 1] = verts[j].y - centroid.y;
        positions[j * 3 + 2] = verts[j].z - centroid.z;
      }
      geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      geo.computeVertexNormals();

      const mat = new THREE.MeshStandardMaterial({
        color: 0x1A0A0E,
        roughness: 0.08,
        metalness: 0.92,
        side: THREE.DoubleSide,
      });

      const mesh = new THREE.Mesh(geo, mat);
      const dir = centroid.clone().normalize();
      const offset = 0.06 + Math.random() * 0.04;
      mesh.position.copy(centroid.clone().add(dir.multiplyScalar(offset)));
      group.add(mesh);
      faceMeshes.push(mesh);
    }
    scene.add(group);

    // Inner nodes — even = red (bearish), odd = green (bullish)
    const nodes: THREE.Mesh[] = [];
    for (let i = 0; i < 10; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1);
      const r     = 0.55 + Math.random() * 0.5;
      const x     = r * Math.sin(phi) * Math.cos(theta);
      const y     = r * Math.sin(phi) * Math.sin(theta);
      const z     = r * Math.cos(phi);

      const isBearish = i % 2 === 0;
      const emissiveColor = isBearish ? 0xF43F5E : 0x4ADE80;

      const nodeGeo = new THREE.SphereGeometry(0.04, 8, 8);
      const nodeMat = new THREE.MeshStandardMaterial({
        color: emissiveColor,
        emissive: emissiveColor,
        emissiveIntensity: 2.5,
      });
      const node = new THREE.Mesh(nodeGeo, nodeMat);
      node.position.set(x, y, z);
      group.add(node);
      nodes.push(node);
    }

    // Animation loop
    let frame = 0;
    let animId: number;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      frame++;

      group.rotation.y += 0.002;
      group.rotation.x += 0.0005;

      // Orbit red light
      const t = frame * 0.01;
      redLight.position.set(Math.sin(t) * 4, Math.cos(t * 0.7) * 2, Math.cos(t) * 4);

      // Staggered pulse per node
      nodes.forEach((n, i) => {
        const s = 1 + 0.35 * Math.sin(frame * 0.03 + i * 1.2);
        n.scale.set(s, s, s);
      });

      // Mouse parallax — lerp camera
      const targetX = mouseRef.current.x * 0.3;
      const targetY = mouseRef.current.y * 0.3;
      camera.position.x += (targetX - camera.position.x) * 0.05;
      camera.position.y += (targetY - camera.position.y) * 0.05;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    };
    animate();

    const handleMouse = (e: MouseEvent) => {
      mouseRef.current.x =  (e.clientX / window.innerWidth  - 0.5) * 2;
      mouseRef.current.y = -(e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", handleMouse);

    const handleResize = () => {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("mousemove", handleMouse);
      window.removeEventListener("resize", handleResize);
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  return (
    <div ref={mountRef} style={{
      position: "absolute", top: 0, left: 0, width: "100%", height: "100vh", zIndex: 0,
    }} />
  );
}
