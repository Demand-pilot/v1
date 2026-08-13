import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Move3d, Sparkles, ShieldCheck } from 'lucide-react';

export default function SupermarketWebGLHero({ scrollProgress = 0 }) {
  const containerRef = useRef(null);
  const elevationRef = useRef(1); // 0 to 2
  const scrollRef = useRef(scrollProgress);

  useEffect(() => {
    scrollRef.current = scrollProgress;
    if (scrollProgress > 0) {
      elevationRef.current = 0.4 + Math.min(1, Math.max(0, scrollProgress)) * 1.8;
    }
  }, [scrollProgress]);

  // Window scroll listener for scroll-driven elevation using ref (zero re-render overhead)
  useEffect(() => {
    const handleWindowScroll = () => {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? Math.min(1, Math.max(0, scrollY / (docHeight * 0.6))) : 0;
      elevationRef.current = 0.4 + progress * 1.8;
    };

    window.addEventListener('scroll', handleWindowScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleWindowScroll);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.background = null;

    const width = container.clientWidth;
    const height = container.clientHeight;

    const aspect = width / height;
    const d = 16;
    const camera = new THREE.OrthographicCamera(-d * aspect, d * aspect, d, -d, 1, 1000);
    
    // Isometric Camera Angle
    camera.position.set(24, 28, 24);
    camera.lookAt(0, 2, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    container.appendChild(renderer.domElement);

    // Warm Minimal Lighting
    const ambientLight = new THREE.AmbientLight(0xfff8f0, 1.3);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffecd2, 1.8);
    dirLight.position.set(20, 40, 20);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    dirLight.shadow.camera.near = 10;
    dirLight.shadow.camera.far = 100;
    dirLight.shadow.bias = -0.001;
    scene.add(dirLight);

    const accentLight = new THREE.PointLight(0xc45d3e, 2.5, 30);
    accentLight.position.set(0, 10, 0);
    scene.add(accentLight);

    // Group for the entire elevating supermarket
    const supermarketGroup = new THREE.Group();
    scene.add(supermarketGroup);

    // 1. Base Ground Platform
    const baseGeo = new THREE.BoxGeometry(22, 1.2, 18);
    const baseMat = new THREE.MeshStandardMaterial({ 
      color: 0xeee8df, 
      roughness: 0.7,
      metalness: 0.1
    });
    const baseMesh = new THREE.Mesh(baseGeo, baseMat);
    baseMesh.position.y = 0;
    baseMesh.receiveShadow = true;
    supermarketGroup.add(baseMesh);

    // Foundation Trim Border (Terracotta)
    const trimGeo = new THREE.BoxGeometry(22.4, 0.3, 18.4);
    const trimMat = new THREE.MeshStandardMaterial({ color: 0xc45d3e, roughness: 0.5 });
    const trimMesh = new THREE.Mesh(trimGeo, trimMat);
    trimMesh.position.y = 0.6;
    supermarketGroup.add(trimMesh);

    // 2. Supermarket Store Walls & Entrance Glass
    const wallMat = new THREE.MeshStandardMaterial({ color: 0xf5f1eb, roughness: 0.8 });
    const glassMat = new THREE.MeshPhysicalMaterial({ 
      color: 0xffffff, 
      transparent: true, 
      opacity: 0.35, 
      roughness: 0.1, 
      transmission: 0.8 
    });

    // Back & Side Walls
    const backWall = new THREE.Mesh(new THREE.BoxGeometry(20, 6, 0.8), wallMat);
    backWall.position.set(0, 3.6, -8);
    backWall.castShadow = true;
    supermarketGroup.add(backWall);

    const leftWall = new THREE.Mesh(new THREE.BoxGeometry(0.8, 6, 16), wallMat);
    leftWall.position.set(-10, 3.6, 0);
    leftWall.castShadow = true;
    supermarketGroup.add(leftWall);

    // Front Glass Facade & Entrance Canopy
    const frontGlass = new THREE.Mesh(new THREE.BoxGeometry(20, 4.5, 0.2), glassMat);
    frontGlass.position.set(0, 2.85, 8);
    supermarketGroup.add(frontGlass);

    const canopy = new THREE.Mesh(new THREE.BoxGeometry(10, 0.4, 3.5), trimMat);
    canopy.position.set(0, 4.8, 8.5);
    canopy.castShadow = true;
    supermarketGroup.add(canopy);

    // 3. Supermarket Product Aisles & Inventory Modules
    const aisles = [];
    const aisleData = [
      { name: 'Aisle 1: Fresh Produce', color: 0x2d6a4f, x: -6, z: -3, surge: '+5% Steady', confidence: '96.5%' },
      { name: 'Aisle 2: Beverages & Payday Peak', color: 0x355e7a, x: -2, z: -3, surge: '+8.0% Payday Surge', confidence: '91.8%' },
      { name: 'Aisle 3: Grocery Staples', color: 0xb07d1e, x: 2, z: -3, surge: '+12% Weekly Replenishment', confidence: '93.4%' },
      { name: 'Aisle 4: School Supplies', color: 0xc45d3e, x: 6, z: -3, surge: '+145% Sierra Academic Surge', confidence: '94.2%' }
    ];

    aisleData.forEach((data) => {
      const aisleGroup = new THREE.Group();
      aisleGroup.position.set(data.x, 1, data.z);

      // Shelf Frame
      const shelfGeo = new THREE.BoxGeometry(2.4, 3.2, 7);
      const shelfMat = new THREE.MeshStandardMaterial({ color: 0xded6c9, roughness: 0.6 });
      const shelfMesh = new THREE.Mesh(shelfGeo, shelfMat);
      shelfMesh.position.y = 1.6;
      shelfMesh.castShadow = true;
      shelfMesh.receiveShadow = true;
      aisleGroup.add(shelfMesh);

      // Inventory Stock Blocks on Shelves
      for (let i = 0; i < 3; i++) {
        const itemGeo = new THREE.BoxGeometry(2.2, 0.6, 6.4);
        const itemMat = new THREE.MeshStandardMaterial({ 
          color: data.color, 
          roughness: 0.4,
          emissive: data.color === 0xc45d3e ? 0xc45d3e : 0x000000,
          emissiveIntensity: data.color === 0xc45d3e ? 0.3 : 0.0
        });
        const itemMesh = new THREE.Mesh(itemGeo, itemMat);
        itemMesh.position.y = 0.8 + i * 1.0;
        aisleGroup.add(itemMesh);
      }

      // Glowing Stockout Prediction Beacon / Pin
      const beaconGeo = new THREE.CylinderGeometry(0.1, 0.1, 1.5, 12);
      const beaconMat = new THREE.MeshStandardMaterial({ color: data.color, emissive: data.color, emissiveIntensity: 0.6 });
      const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
      beaconMesh.position.set(0, 4.2, 0);
      aisleGroup.add(beaconMesh);

      const sphereGeo = new THREE.SphereGeometry(0.35, 16, 16);
      const sphereMesh = new THREE.Mesh(sphereGeo, beaconMat);
      sphereMesh.position.set(0, 5.0, 0);
      aisleGroup.add(sphereMesh);

      aisleGroup.userData = data;
      supermarketGroup.add(aisleGroup);
      aisles.push(aisleGroup);
    });

    // 4. Logistics Delivery Truck at the Dock
    const truckGroup = new THREE.Group();
    truckGroup.position.set(13, 0.6, 2);

    const cabGeo = new THREE.BoxGeometry(2.2, 2.4, 2.5);
    const cabMat = new THREE.MeshStandardMaterial({ color: 0x2d2a26, roughness: 0.5 });
    const cab = new THREE.Mesh(cabGeo, cabMat);
    cab.position.set(0, 1.2, 2.5);
    cab.castShadow = true;
    truckGroup.add(cab);

    const trailerGeo = new THREE.BoxGeometry(2.4, 3.2, 5.5);
    const trailerMat = new THREE.MeshStandardMaterial({ color: 0xc45d3e, roughness: 0.4 });
    const trailer = new THREE.Mesh(trailerGeo, trailerMat);
    trailer.position.set(0, 1.6, -1.8);
    trailer.castShadow = true;
    truckGroup.add(trailer);

    supermarketGroup.add(truckGroup);

    // Animation Loop with Elevation Physics
    let frameId;
    let clock = new THREE.Clock();

    const animate = () => {
      frameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Elevation floating oscillation + scroll driven target
      const floatOffset = Math.sin(elapsedTime * 1.5) * 0.25;
      const targetElevation = (elevationRef.current * 2.2) + floatOffset;
      supermarketGroup.position.y += (targetElevation - supermarketGroup.position.y) * 0.08;

      // Subtle slow isometric orbit rotation
      supermarketGroup.rotation.y = Math.sin(elapsedTime * 0.3) * 0.08;

      // Pulse beacon pins
      aisles.forEach((aisle, idx) => {
        const beaconPin = aisle.children[aisle.children.length - 1];
        if (beaconPin) {
          beaconPin.scale.setScalar(1 + Math.sin(elapsedTime * 3 + idx) * 0.15);
        }
      });

      renderer.render(scene, camera);
    };

    animate();

    // Resize Handler
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      const asp = w / h;
      camera.left = -d * asp;
      camera.right = d * asp;
      camera.top = d;
      camera.bottom = -d;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '460px', borderRadius: 'var(--radius-xl)', overflow: 'hidden', backgroundColor: 'transparent', transition: 'all var(--transition-normal)' }}>
      
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Floating Elevation Status Badge */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          left: '16px',
          backgroundColor: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(12px)',
          padding: '8px 16px',
          borderRadius: 'var(--radius-pill)',
          border: '1px solid rgba(45, 42, 38, 0.06)',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.78rem',
          fontWeight: '600',
          color: 'var(--text-primary)'
        }}
      >
        <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--accent-terracotta)', animation: 'pulseGlow 2s infinite' }} />
        <span>3D Store Elevation • Scroll Linked</span>
      </div>

      {/* Floating Category Telemetry */}
      <div
        style={{
          position: 'absolute',
          bottom: '16px',
          right: '16px',
          backgroundColor: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(12px)',
          padding: '8px 14px',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid rgba(45, 42, 38, 0.06)',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          gap: '12px',
          fontSize: '0.72rem'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#c45d3e' }} />
          <span>School Supplies (+145% • 94.2% AI Conf)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#355e7a' }} />
          <span>Beverages (+8.0% Payday)</span>
        </div>
      </div>

    </div>
  );
}
