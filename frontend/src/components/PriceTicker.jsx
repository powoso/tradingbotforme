import React, { useState, useEffect, useRef } from 'react';
import { getPrices, getFearGreed } from '../api';

function formatPrice(price) {
  if (price == null) return '-';
  if (price >= 1000) return `$${price.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  if (price >= 1) return `$${price.toFixed(2)}`;
  if (price >= 0.001) return `$${price.toFixed(4)}`;
  return `$${price.toFixed(6)}`;
}

function formatChange(pct) {
  if (pct == null) return '-';
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

function MiniSparkline({ data, color, width = 60, height = 20 }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="sparkline-svg">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FearGreedMeter({ value, label }) {
  const getColor = (v) => {
    if (v <= 25) return 'var(--red)';
    if (v <= 45) return 'var(--orange)';
    if (v <= 55) return 'var(--yellow)';
    if (v <= 75) return 'var(--green)';
    return 'var(--green)';
  };

  const color = getColor(value);
  const rotation = (value / 100) * 180 - 90;

  return (
    <div className="fear-greed-meter">
      <div className="fgm-label">Fear & Greed</div>
      <div className="fgm-gauge">
        <svg viewBox="0 0 100 55" width="80" height="44">
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke="var(--bg-primary)"
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke={`url(#fgGradient)`}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <defs>
            <linearGradient id="fgGradient" x1="0" x2="1">
              <stop offset="0%" stopColor="var(--red)" />
              <stop offset="25%" stopColor="var(--orange)" />
              <stop offset="50%" stopColor="var(--yellow)" />
              <stop offset="75%" stopColor="var(--green)" />
              <stop offset="100%" stopColor="var(--green)" />
            </linearGradient>
          </defs>
          <line
            x1="50"
            y1="50"
            x2={50 + 30 * Math.cos((rotation * Math.PI) / 180)}
            y2={50 - 30 * Math.sin((rotation * Math.PI) / 180)}
            stroke={color}
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="50" cy="50" r="3" fill={color} />
        </svg>
      </div>
      <div className="fgm-value" style={{ color }}>{value}</div>
      <div className="fgm-classification">{label}</div>
    </div>
  );
}

export default function PriceTicker() {
  const [prices, setPrices] = useState({});
  const [fearGreed, setFearGreed] = useState(null);
  const [error, setError] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      try {
        const [priceData, fgData] = await Promise.all([
          getPrices().catch(() => ({})),
          getFearGreed().catch(() => null),
        ]);
        if (!cancelled) {
          setPrices(priceData);
          if (fgData) setFearGreed(fgData);
          setError(false);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    }

    fetchAll();
    const interval = setInterval(fetchAll, 60000); // Refresh every 60s
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  const symbols = Object.keys(prices);

  if (symbols.length === 0 && !fearGreed) {
    return null; // Don't render if no data
  }

  return (
    <div className="price-ticker-container">
      {fearGreed && (
        <FearGreedMeter value={fearGreed.value} label={fearGreed.label} />
      )}
      <div className="price-ticker-scroll" ref={scrollRef}>
        {symbols.map((sym) => {
          const coin = prices[sym];
          if (!coin || !coin.price) return null;
          const changeColor = (coin.change_24h || 0) >= 0 ? 'var(--green)' : 'var(--red)';
          return (
            <div key={sym} className="price-ticker-item">
              <div className="ticker-symbol">{sym}</div>
              <div className="ticker-price">{formatPrice(coin.price)}</div>
              <div className="ticker-change" style={{ color: changeColor }}>
                {formatChange(coin.change_24h)}
              </div>
              <MiniSparkline
                data={coin.sparkline}
                color={changeColor}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
