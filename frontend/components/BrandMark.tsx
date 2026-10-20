// Logo: an open book on the accent colour, with a highlighter stroke.
export default function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 36 36" aria-hidden="true" focusable="false">
      <rect width="36" height="36" rx="11" fill="var(--accent)" />
      <path
        d="M18 12.2c-2.4-1.9-5.6-2.3-9-1.7v13.8c3.4-.6 6.6-.2 9 1.7 2.4-1.9 5.6-2.3 9-1.7V10.5c-3.4-.6-6.6-.2-9 1.7Zm0 0v13.8"
        fill="none"
        stroke="var(--accent-ink)"
        strokeWidth="1.9"
        strokeLinejoin="round"
      />
      <path d="M20.6 16.4h4" stroke="var(--accent-ink)" strokeWidth="2.6" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}
