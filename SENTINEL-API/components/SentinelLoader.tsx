"use client";

import React from "react";
import styled from "styled-components";

interface SentinelLoaderProps {
  size?: number;
}

const SentinelLoader: React.FC<SentinelLoaderProps> = ({ size = 64 }) => {
  return (
    <StyledWrapper $size={size}>
      <div className="loader">
        <svg height={0} width={0} viewBox="0 0 256 256" className="absolute">
          <defs xmlns="http://www.w3.org/2000/svg">
            {/* Bright green gradient for the L-shape */}
            <linearGradient gradientUnits="userSpaceOnUse" y2={256} x2={128} y1={0} x1={0} id="logo-grad-a">
              <stop stopColor="#00ff88" />
              <stop stopColor="#06d6a0" offset={1} />
            </linearGradient>
            {/* Animated rotating gradient for the circle */}
            <linearGradient gradientUnits="userSpaceOnUse" y2={0} x2={0} y1={256} x1={0} id="logo-grad-b">
              <stop stopColor="#34d399" />
              <stop stopColor="#00ff88" offset={1} />
              <animateTransform
                repeatCount="indefinite"
                keySplines=".42,0,.58,1;.42,0,.58,1;.42,0,.58,1;.42,0,.58,1;.42,0,.58,1;.42,0,.58,1;.42,0,.58,1;.42,0,.58,1"
                keyTimes="0; 0.125; 0.25; 0.375; 0.5; 0.625; 0.75; 0.875; 1"
                dur="8s"
                values="0 128 128;-270 128 128;-270 128 128;-540 128 128;-540 128 128;-810 128 128;-810 128 128;-1080 128 128;-1080 128 128"
                type="rotate"
                attributeName="gradientTransform"
              />
            </linearGradient>
          </defs>
        </svg>

        {/* Logo paths */}
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 256 256" height={size} width={size} className="inline-block logo-svg">
          <path
            strokeLinejoin="round"
            strokeLinecap="round"
            strokeWidth={18}
            stroke="url(#logo-grad-b)"
            d="M 92 72 C 142.81 72 184 113.19 184 164 C 184 214.81 142.81 256 92 256 C 41.19 256 0 214.81 0 164 C 0 113.19 41.19 72 92 72 Z"
            className="spin"
            pathLength={360}
          />
          <path
            strokeLinejoin="round"
            strokeLinecap="round"
            strokeWidth={20}
            stroke="url(#logo-grad-a)"
            d="M 256 0 L 256 256 L 184 256 L 184 72 L 0 72 L 0 0 Z"
            className="dash"
            pathLength={360}
          />
        </svg>
      </div>
    </StyledWrapper>
  );
};

const StyledWrapper = styled.div<{ $size: number }>`
  .absolute {
    position: absolute;
  }

  .inline-block {
    display: inline-block;
  }

  .loader {
    display: flex;
    align-items: center;
    margin: 0;
  }

  .logo-svg {
    filter: drop-shadow(0 0 8px rgba(0, 255, 136, 0.6))
            drop-shadow(0 0 20px rgba(0, 255, 136, 0.3));
    animation: logoGlow 2s ease-in-out infinite alternate;
  }

  @keyframes logoGlow {
    from {
      filter: drop-shadow(0 0 8px rgba(0, 255, 136, 0.6))
              drop-shadow(0 0 20px rgba(0, 255, 136, 0.3));
    }
    to {
      filter: drop-shadow(0 0 12px rgba(0, 255, 136, 0.8))
              drop-shadow(0 0 30px rgba(0, 255, 136, 0.5));
    }
  }

  .dash {
    animation: dashArray 2s ease-in-out infinite,
      dashOffset 2s linear infinite;
  }

  .spin {
    animation: spinDashArray 2s ease-in-out infinite,
      dashOffset 2s linear infinite;
    transform-origin: 92px 164px;
  }

  @keyframes dashArray {
    0% {
      stroke-dasharray: 0 1 359 0;
    }
    50% {
      stroke-dasharray: 0 359 1 0;
    }
    100% {
      stroke-dasharray: 359 1 0 0;
    }
  }

  @keyframes spinDashArray {
    0% {
      stroke-dasharray: 270 90;
    }
    50% {
      stroke-dasharray: 0 360;
    }
    100% {
      stroke-dasharray: 270 90;
    }
  }

  @keyframes dashOffset {
    0% {
      stroke-dashoffset: 365;
    }
    100% {
      stroke-dashoffset: 5;
    }
  }
`;

export default SentinelLoader;
