"use client";

import { useCallback, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// The worker must be set in the same module as <Document>/<Page> (react-pdf docs).
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const PAGE_WIDTH = 560;
const MIN_MATCH = 15; // only whole lines: short items ("random forest") would match anywhere

function normalize(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

type Props = { page: number; excerpt: string; loadingText: string; errorText: string };

export default function PdfViewer({ page, excerpt, loadingText, errorText }: Props) {
  const [failed, setFailed] = useState(false);
  const target = normalize(excerpt);

  // Highlight the text items of the page that belong to the cited excerpt.
  const renderText = useCallback(
    ({ str }: { str: string }) => {
      const item = normalize(str);
      const safe = escapeHtml(str);
      return item.length >= MIN_MATCH && target.includes(item) ? `<mark>${safe}</mark>` : safe;
    },
    [target],
  );

  if (failed) {
    return <p role="alert">{errorText}</p>;
  }
  return (
    <Document file="/api/book.pdf" loading={<p>{loadingText}</p>} onLoadError={() => setFailed(true)}>
      <Page pageNumber={page} width={PAGE_WIDTH} customTextRenderer={renderText} />
    </Document>
  );
}
