import React from 'react';

function intensityColor(intensity) {
  if (intensity <= 30) return 'var(--green)';
  if (intensity <= 60) return 'var(--yellow)';
  return 'var(--red)';
}

export default function EmotionGauge({ emotion, intensity = 50, confidence, size = 100 }) {
  const radius = 40;
  const strokeWidth = 8;
  const center = 50;
  // Semicircle: from 180deg to 0deg (left to right across the top)
  const startAngle = Math.PI;
  const endAngle = 0;
  const range = startAngle - endAngle;
  const clampedIntensity = Math.max(0, Math.min(100, intensity));
  const angle = startAngle - (clampedIntensity / 100) * range;

  const bgArc = describeArc(center, center, radius, endAngle, startAngle);
  const fillArc = describeArc(center, center, radius, angle, startAngle);

  const color = intensityColor(clampedIntensity);

  return (
    <div className="gauge-container">
      <svg
        className="gauge-svg"
        width={size}
        height={size * 0.6}
        viewBox="0 10 100 55"
      >
        <path
          d={bgArc}
          fill="none"
          stroke="var(--bg-primary)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {clampedIntensity > 0 && (
          <path
            d={fillArc}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        )}
        <text
          x={center}
          y={center + 2}
          textAnchor="middle"
          fill={color}
          fontSize="16"
          fontWeight="700"
          fontFamily="var(--font-mono)"
        >
          {clampedIntensity}
        </text>
      </svg>
      <div className="gauge-label">{emotion || 'Unknown'}</div>
      {confidence != null && (
        <div className="gauge-sublabel">
          Confidence: {confidence}%
        </div>
      )}
    </div>
  );
}

function polarToCartesian(cx, cy, r, angle) {
  return {
    x: cx + r * Math.cos(angle),
    y: cy - r * Math.sin(angle),
  };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}
