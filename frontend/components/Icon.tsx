// Small inline icon set (24x24, 1.8px strokes, currentColor): no icon library needed.
const PATHS = {
  progress: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  ask: "M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12Z",
  feynman: "M9 18h6M10 21.5h4M12 2.5a6.5 6.5 0 0 0-3.9 11.7c.6.5.9 1.1.9 1.8v.5h6V16c0-.7.3-1.3.9-1.8A6.5 6.5 0 0 0 12 2.5Z",
  quiz: "M9 11.5l2 2 4-4.5M5 3.5h14a1.5 1.5 0 0 1 1.5 1.5v14a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 19V5A1.5 1.5 0 0 1 5 3.5Z",
  library: "M4 4.5h4v15H4zM10 4.5h4v15h-4zM16.2 5.3l3.8-1 3 14.6-3.8 1z",
  book: "M12 6.5c-1.8-1.6-4.8-2-8-1.5v13c3.2-.5 6.2-.1 8 1.5 1.8-1.6 4.8-2 8-1.5V5c-3.2-.5-6.2-.1-8 1.5Zm0 0V19.5",
  check: "M5 12.5l4.5 4.5L19 7.5",
  cross: "M6 6l12 12M18 6L6 18",
  shield: "M12 3l7.5 3v5.5c0 4.5-3.2 8.3-7.5 9.5-4.3-1.2-7.5-5-7.5-9.5V6L12 3Zm-3.5 9l2.5 2.5 4.5-5",
  alert: "M12 8.5v5M12 16.5v.5M10.3 4l-7.8 13.5A2 2 0 0 0 4.2 20.5h15.6a2 2 0 0 0 1.7-3L13.7 4a2 2 0 0 0-3.4 0Z",
  info: "M12 11v5.5M12 7.5v.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  external: "M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
  send: "M12 19V5M5.5 11.5L12 5l6.5 6.5",
  spark: "M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8",
  arrow: "M5 12h14M13 6l6 6-6 6",
  dot: "M12 12m-4 0a4 4 0 1 0 8 0 4 4 0 1 0-8 0",
  minus: "M6 12h12",
  plus: "M12 5v14M5 12h14",
  refresh: "M20 11a8 8 0 0 0-14.3-4.9L4 8M4 4v4h4M4 13a8 8 0 0 0 14.3 4.9L20 16M20 20v-4h-4",
} as const;

export type IconName = keyof typeof PATHS;

export default function Icon({ name, label }: { name: IconName; label?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1em"
      height="1em"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={label ? undefined : true}
      role={label ? "img" : undefined}
      aria-label={label}
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

// Level -> icon, so a mastery level is never shown by colour alone.
export const LEVEL_ICONS: Record<string, IconName> = {
  WEAK: "alert",
  LEARNING: "dot",
  MASTERED: "check",
  NONE: "minus",
};
