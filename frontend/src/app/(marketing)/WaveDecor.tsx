import React from "react";

interface WaveDecorProps {
  className?: string;
  color?: string;
  opacity?: number;
}

export function WaveDecor({
  className = "",
  color = "#F2661F",
  opacity = 0.28,
}: WaveDecorProps) {
  return (
    <svg
      className={`pointer-events-none select-none ${className}`}
      viewBox="0 0 1440 600"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M-100 120 C 300 40, 680 260, 1100 140 C 1280 90, 1420 160, 1600 200"
        stroke={color}
        strokeWidth="1.25"
        strokeOpacity={opacity}
      />
      <path
        d="M-100 170 C 320 90, 700 310, 1120 190 C 1300 140, 1440 210, 1600 250"
        stroke={color}
        strokeWidth="1.25"
        strokeOpacity={opacity * 0.9}
      />
      <path
        d="M-100 220 C 340 140, 720 360, 1140 240 C 1320 190, 1460 260, 1600 300"
        stroke={color}
        strokeWidth="1.25"
        strokeOpacity={opacity * 0.8}
      />
      <path
        d="M-100 270 C 360 190, 740 410, 1160 290 C 1340 240, 1480 310, 1600 350"
        stroke={color}
        strokeWidth="1.25"
        strokeOpacity={opacity * 0.7}
      />
      <path
        d="M-100 320 C 380 240, 760 460, 1180 340 C 1360 290, 1500 360, 1600 400"
        stroke={color}
        strokeWidth="1.25"
        strokeOpacity={opacity * 0.6}
      />
    </svg>
  );
}
