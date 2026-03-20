import React, { useState, useEffect, useRef } from 'react';
import { getCooldown } from '../api';

export default function CooldownTimer() {
  const [cooldown, setCooldown] = useState(null);
  const [remaining, setRemaining] = useState(0);
  const intervalRef = useRef(null);

  // Fetch cooldown status
  useEffect(() => {
    let cancelled = false;

    async function fetchCooldown() {
      try {
        const data = await getCooldown();
        if (!cancelled) {
          if (data.active) {
            setCooldown(data);
            setRemaining(data.remaining_seconds);
          } else {
            setCooldown(null);
            setRemaining(0);
          }
        }
      } catch {
        // ignore errors
      }
    }

    fetchCooldown();
    const pollInterval = setInterval(fetchCooldown, 30000);
    return () => {
      cancelled = true;
      clearInterval(pollInterval);
    };
  }, []);

  // Countdown timer
  useEffect(() => {
    if (remaining <= 0) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }

    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          setCooldown(null);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [remaining > 0]);

  if (!cooldown || remaining <= 0) return null;

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const progress = cooldown.cooldown_minutes > 0
    ? ((cooldown.cooldown_minutes * 60 - remaining) / (cooldown.cooldown_minutes * 60)) * 100
    : 0;

  return (
    <div className="cooldown-timer-bar">
      <div className="cooldown-timer-content">
        <span className="cooldown-timer-icon">&#9202;</span>
        <div className="cooldown-timer-info">
          <span className="cooldown-timer-label">
            Active Cooldown ({cooldown.state_label})
          </span>
          <span className="cooldown-timer-time">
            {mins}:{secs.toString().padStart(2, '0')} remaining
          </span>
        </div>
        <div className="cooldown-timer-progress-bg">
          <div
            className="cooldown-timer-progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}
