"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import { pdfUrl } from "@/lib/i18n";

// The worker must be set in the same module as <Document>/<Page> (react-pdf docs).
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const MAX_WIDTH = 760;
const MIN_MATCH = 15; // only whole lines: short items ("random forest") would match anywhere

function normalize(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

type Props = { course: string; page: number; excerpt: string; loadingText: string; errorText: string };

export default function PdfViewer({ course, page, excerpt, loadingText, errorText }: Props) {
  const [failed, setFailed] = useState(false);
  const [width, setWidth] = useState(560);
  const frame = useRef<HTMLDivElement>(null);
  const target = normalize(excerpt);

  // Render the page at the panel's width (the text layer must match the canvas).
  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setWidth(Math.min(MAX_WIDTH, Math.floor(entry.contentRect.width)));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Highlight the text items of the page that belong to the cited excerpt.
  const renderText = useCallback(
    ({ str }: { str: string }) => {
      const item = normalize(str);
      const safe = escapeHtml(str);
      return target && item.length >= MIN_MATCH && target.includes(item) ? `<mark>${safe}</mark>` : safe;
    },
    [target],
  );

  if (failed) {
    return <p role="alert" style={{ padding: "var(--space-4)" }}>{errorText}</p>;
  }
  return (
    <div ref={frame}>
      <Document
        file={pdfUrl(course)}
        loading={<p style={{ padding: "var(--space-4)" }}>{loadingText}</p>}
        onLoadError={() => setFailed(true)}
      >
        {/* No annotation layer: the book's internal links are unlabelled, tiny targets. */}
        <Page pageNumber={page} width={width} customTextRenderer={renderText} renderAnnotationLayer={false} />
      </Document>
    </div>
  );
}
