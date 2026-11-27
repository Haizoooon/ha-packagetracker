import { css } from "lit";

export const sharedStyles = css`
  :host {
    --pt-radius: var(--ha-card-border-radius, 16px);
    --pt-ease: cubic-bezier(0.2, 0.7, 0.25, 1);
    --pt-transit: var(--info-color, #2f7de1);
    --pt-success: var(--success-color, #43a047);
    --pt-warning: var(--warning-color, #f2a33a);
    --pt-danger: var(--error-color, #d9534f);
    --pt-pickup: #8e6bd8;
    --pt-muted: var(--secondary-text-color, #727272);
    --pt-border: var(--divider-color, rgba(127, 127, 127, 0.22));
    --pt-surface: var(--secondary-background-color, rgba(127, 127, 127, 0.06));
    color: var(--primary-text-color);
    font-family: var(
      --paper-font-common-base_-_font-family,
      "Roboto",
      system-ui,
      -apple-system,
      sans-serif
    );
  }

  * {
    box-sizing: border-box;
  }

  button,
  input,
  select {
    font: inherit;
    color: inherit;
  }

  button {
    cursor: pointer;
  }

  .mono {
    font-family: ui-monospace, "SF Mono", "Roboto Mono", Menlo, monospace;
    letter-spacing: 0.02em;
  }

  .muted {
    color: var(--secondary-text-color);
  }

  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border: 1px solid transparent;
    border-radius: 12px;
    background: transparent;
    color: var(--secondary-text-color);
    transition:
      background 160ms var(--pt-ease),
      color 160ms var(--pt-ease),
      transform 160ms var(--pt-ease);
  }

  .icon-btn:hover {
    background: var(--pt-surface);
    color: var(--primary-text-color);
  }

  .icon-btn:active {
    transform: scale(0.94);
  }

  :focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    max-width: 100%;
    padding: 4px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.02em;
    line-height: 1.2;
    white-space: nowrap;
    background: var(--pt-surface);
    color: var(--pt-muted);
  }

  .pill.transit {
    color: var(--pt-transit);
    background: color-mix(in srgb, var(--pt-transit) 12%, transparent);
  }

  .pill.success {
    color: var(--pt-success);
    background: color-mix(in srgb, var(--pt-success) 13%, transparent);
  }

  .pill.warning {
    color: var(--pt-warning);
    background: color-mix(in srgb, var(--pt-warning) 16%, transparent);
  }

  .pill.danger {
    color: var(--pt-danger);
    background: color-mix(in srgb, var(--pt-danger) 12%, transparent);
  }

  .pill.pickup {
    color: var(--pt-pickup);
    background: color-mix(in srgb, var(--pt-pickup) 13%, transparent);
  }

  .pill.ordered {
    color: var(--pt-muted);
  }

  .skeleton {
    position: relative;
    overflow: hidden;
    background: var(--pt-surface);
    border-radius: 8px;
  }

  .skeleton::after {
    content: "";
    position: absolute;
    inset: 0;
    transform: translateX(-100%);
    background: linear-gradient(
      90deg,
      transparent,
      color-mix(in srgb, var(--primary-text-color) 7%, transparent),
      transparent
    );
    animation: pt-shimmer 1.4s infinite;
  }

  @keyframes pt-shimmer {
    100% {
      transform: translateX(100%);
    }
  }

  @keyframes pt-fade-up {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation-duration: 0.001ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.001ms !important;
    }
  }
`;
