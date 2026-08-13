import React, { useState, useEffect } from 'react';

/**
 * AutoAnimatedPointer: An elegant simulated artisan cursor that
 * glides across persona cards to demonstrate interactive selection.
 */
export default function AutoAnimatedPointer({ targetIndex, isUserInteracting }) {
  const [coords, setCoords] = useState({ x: 120, y: 320 });
  const [isClicking, setIsClicking] = useState(false);
  const [activePersonaName, setActivePersonaName] = useState('Store Manager');

  useEffect(() => {
    if (isUserInteracting) return;

    const targets = [
      { name: 'Store Manager', x: 220, y: 380 },
      { name: 'Supply Chain Planner', x: 620, y: 380 },
      { name: 'Executive Leadership', x: 1020, y: 380 }
    ];

    let current = 0;
    const interval = setInterval(() => {
      current = (current + 1) % targets.length;
      const target = targets[current];
      setCoords({ x: target.x, y: target.y });
      setActivePersonaName(target.name);
      
      // Trigger click pulse
      setTimeout(() => {
        setIsClicking(true);
        setTimeout(() => setIsClicking(false), 300);
      }, 700);
    }, 3200);

    return () => clearInterval(interval);
  }, [isUserInteracting]);

  if (isUserInteracting) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: coords.y,
        left: coords.x,
        pointerEvents: 'none',
        zIndex: 50,
        transition: 'all 900ms cubic-bezier(0.22, 1, 0.36, 1)',
        transform: `translate(-10px, -10px) scale(${isClicking ? 0.9 : 1})`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: '6px'
      }}
    >
      {/* Artisan SVG Cursor */}
      <svg
        width="28"
        height="28"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{
          filter: 'drop-shadow(0 4px 10px rgba(196, 93, 62, 0.35))'
        }}
      >
        <path
          d="M3 3L10.07 19.97L12.58 12.58L19.97 10.07L3 3Z"
          fill="#c45d3e"
          stroke="#faf8f5"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>

      {/* Floating Tag */}
      <div
        style={{
          backgroundColor: '#2d2a26',
          color: '#faf8f5',
          fontSize: '0.72rem',
          fontWeight: '600',
          padding: '3px 8px',
          borderRadius: '9999px',
          letterSpacing: '0.04em',
          boxShadow: '0 4px 12px rgba(45, 42, 38, 0.2)',
          whiteSpace: 'nowrap',
          display: 'flex',
          alignItems: 'center',
          gap: '5px'
        }}
      >
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: isClicking ? '#c45d3e' : '#2d6a4f',
            transition: 'background-color 200ms ease'
          }}
        />
        {isClicking ? `Selecting ${activePersonaName}` : 'Auto-Guide: Click to Login'}
      </div>
    </div>
  );
}
