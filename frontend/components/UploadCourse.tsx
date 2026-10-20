"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import CourseJob from "@/components/CourseJob";
import Icon from "@/components/Icon";
import { fmt, type Dict } from "@/lib/i18n";

// Same limits as course/upload.py (MAX_UPLOAD_MB, MAX_STUDY_PAGES).
const MAX_MB = 100;
const MAX_PAGES = 150;
const LICENSES = [
  "CC BY 4.0",
  "CC BY-SA 4.0",
  "CC BY-NC 4.0",
  "CC BY-NC-SA 4.0",
  "Public domain",
  "Own work",
  "Permission from the author",
];

type Chapter = { number: number; title: string; first: number; last: number };
type Upload = { upload_id: string; pages: number; chapters: Chapter[]; title: string };

// Upload a PDF, choose what to study, then follow the processing of the new course.
export default function UploadCourse({ t }: { t: Dict }) {
  const router = useRouter();
  const [upload, setUpload] = useState<Upload | null>(null);
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [title, setTitle] = useState("");
  const [byPages, setByPages] = useState(false);
  const [chosen, setChosen] = useState<number[]>([]);
  const [first, setFirst] = useState(1);
  const [last, setLast] = useState(1);
  const [bookLang, setBookLang] = useState("en");
  const [license, setLicense] = useState(LICENSES[3]);
  const [attribution, setAttribution] = useState("");
  const [rights, setRights] = useState(false);
  const [courseId, setCourseId] = useState<string | null>(null);
  const L = t.library;

  async function send(file: File | undefined) {
    if (!file) return;
    setError("");
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError(L.uploadError);
      return;
    }
    if (file.size > MAX_MB * 1_000_000) {
      setError(L.dropHint);
      return;
    }
    setBusy(true);
    setFileName(file.name);
    try {
      const response = await fetch("/api/uploads", {
        method: "POST",
        headers: { "content-type": "application/pdf" },
        body: file,
      });
      if (!response.ok) throw new Error(String(response.status));
      const body: Upload = await response.json();
      setUpload(body);
      setTitle(body.title || file.name.replace(/\.pdf$/i, ""));
      setByPages(body.chapters.length === 0);
      setChosen([]);
      setFirst(1);
      setLast(Math.min(body.pages, 20));
    } catch {
      setError(L.uploadError);
    } finally {
      setBusy(false);
    }
  }

  const count = !upload
    ? 0
    : byPages
      ? Math.max(0, last - first + 1)
      : upload.chapters.filter((c) => chosen.includes(c.number)).reduce((n, c) => n + c.last - c.first + 1, 0);
  const valid =
    upload !== null &&
    title.trim().length >= 3 &&
    attribution.trim().length >= 2 &&
    rights &&
    count >= 1 &&
    count <= MAX_PAGES &&
    (!byPages || (first >= 1 && last <= upload.pages));

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (!upload || !valid) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/courses", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          upload_id: upload.upload_id,
          title: title.trim(),
          book_lang: bookLang,
          license,
          attribution: attribution.trim(),
          chapters: byPages ? [] : chosen,
          pages: byPages ? [first, last] : [],
          rights,
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : L.uploadError);
      setCourseId(body.id);
      router.refresh(); // the new course card appears in the library
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : L.uploadError);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setUpload(null);
    setCourseId(null);
    setRights(false);
    setError("");
  }

  if (courseId) {
    return (
      <div className="stack">
        <strong className="notion-name">{title}</strong>
        <CourseJob courseId={courseId} initialState="queued" t={t} />
        <button type="button" className="btn btn-secondary" onClick={reset} style={{ justifySelf: "start" }}>
          <Icon name="plus" />
          {L.uploadAnother}
        </button>
      </div>
    );
  }

  if (!upload) {
    return (
      <div className="stack">
        <label
          className="dropzone"
          data-dragging={dragging}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            send(event.dataTransfer.files[0]);
          }}
        >
          <input
            type="file"
            accept="application/pdf,.pdf"
            className="sr-only"
            onChange={(event) => send(event.target.files?.[0])}
            disabled={busy}
          />
          <Icon name="book" />
          <strong>{busy ? L.reading : L.drop}</strong>
          <span className="hint">{L.dropHint}</span>
        </label>
        <div aria-live="polite">
          {error && (
            <p className="callout callout-warn" role="alert">
              <Icon name="alert" />
              {error}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <form className="stack" onSubmit={create}>
      <p className="callout">
        <Icon name="book" />
        <span>
          <strong>{fileName}</strong> · {fmt(L.found, { pages: upload.pages, chapters: upload.chapters.length })}
        </span>
      </p>

      <div className="field">
        <label className="field-label" htmlFor="course-title">
          {L.courseTitle}
        </label>
        <input id="course-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} />
      </div>

      <fieldset className="field fieldset">
        <legend className="field-label">{L.whatToStudy}</legend>
        {upload.chapters.length > 0 ? (
          <div className="segmented" role="group" aria-label={L.whatToStudy} style={{ justifySelf: "start" }}>
            <button type="button" aria-pressed={!byPages} onClick={() => setByPages(false)}>
              {L.byChapters}
            </button>
            <button type="button" aria-pressed={byPages} onClick={() => setByPages(true)}>
              {L.byPages}
            </button>
          </div>
        ) : (
          <p className="hint">{L.noChapters}</p>
        )}
        {byPages ? (
          <div className="row">
            <label className="field">
              <span className="hint">{L.from}</span>
              <input type="number" className="input" min={1} max={upload.pages} value={first} onChange={(e) => setFirst(Number(e.target.value))} />
            </label>
            <label className="field">
              <span className="hint">{L.to}</span>
              <input type="number" className="input" min={1} max={upload.pages} value={last} onChange={(e) => setLast(Number(e.target.value))} />
            </label>
          </div>
        ) : (
          <ul className="chapter-list">
            {upload.chapters.map((chapter) => (
              <li key={chapter.number}>
                <label className="chapter">
                  <input
                    type="checkbox"
                    checked={chosen.includes(chapter.number)}
                    onChange={(e) =>
                      setChosen((old) =>
                        e.target.checked ? [...old, chapter.number] : old.filter((n) => n !== chapter.number),
                      )
                    }
                  />
                  <span>
                    <strong>{chapter.title}</strong>
                    <span className="hint">
                      {" "}
                      {fmt(L.chapterPages, {
                        first: chapter.first,
                        last: chapter.last,
                        count: chapter.last - chapter.first + 1,
                      })}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}
        <span className="hint" data-warn={count > MAX_PAGES} aria-live="polite">
          {fmt(L.selected, { count, max: MAX_PAGES })}
        </span>
      </fieldset>

      <div className="row" style={{ alignItems: "flex-start" }}>
        <div className="field" style={{ flex: 1, minWidth: 180 }}>
          <label className="field-label" htmlFor="book-lang">
            {L.bookLang}
          </label>
          <select id="book-lang" className="select" value={bookLang} onChange={(e) => setBookLang(e.target.value)}>
            <option value="en">{L.langs.en}</option>
            <option value="fr">{L.langs.fr}</option>
          </select>
        </div>
        <div className="field" style={{ flex: 1, minWidth: 180 }}>
          <label className="field-label" htmlFor="license">
            {L.license}
          </label>
          <select id="license" className="select" value={license} onChange={(e) => setLicense(e.target.value)}>
            {LICENSES.map((item) => (
              <option key={item} value={item}>
                {L.licenses[item as keyof typeof L.licenses] ?? item}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="field">
        <label className="field-label" htmlFor="attribution">
          {L.attribution}
        </label>
        <input
          id="attribution"
          className="input"
          value={attribution}
          onChange={(e) => setAttribution(e.target.value)}
          placeholder={L.attributionHint}
          maxLength={300}
        />
      </div>

      <label className="chapter">
        <input type="checkbox" checked={rights} onChange={(e) => setRights(e.target.checked)} />
        <span>{L.rights}</span>
      </label>

      <div aria-live="polite">
        {error && (
          <p className="callout callout-warn" role="alert">
            <Icon name="alert" />
            {error}
          </p>
        )}
      </div>

      <div className="row">
        <button type="submit" className="btn btn-primary" disabled={busy || !valid}>
          <Icon name="plus" />
          {busy ? L.creating : L.create}
        </button>
        <button type="button" className="btn btn-ghost" onClick={reset}>
          {L.cancel}
        </button>
      </div>
    </form>
  );
}
