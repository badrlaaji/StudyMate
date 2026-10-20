"use client";

import { useRouter } from "next/navigation";

import type { Course } from "@/lib/api";
import { COURSE_COOKIE, saveCookie, type Dict } from "@/lib/i18n";

// Pick the course: stored in a cookie, then the server pages render again.
export default function CourseSwitcher({
  courses,
  current,
  t,
  id,
}: {
  courses: Course[];
  current: Course | null;
  t: Dict;
  id: string;
}) {
  const router = useRouter();
  if (!current) return null;

  function choose(courseId: string) {
    saveCookie(COURSE_COOKIE, courseId);
    router.refresh();
  }

  return (
    <div className="course-switch">
      <label className="eyebrow" htmlFor={id}>
        {t.course.label}
      </label>
      <select
        id={id}
        className="select"
        value={current.id}
        onChange={(event) => choose(event.target.value)}
        aria-label={t.course.switch}
      >
        {courses.map((course) => (
          <option key={course.id} value={course.id}>
            {course.title}
          </option>
        ))}
      </select>
      <span className="course-scope">{current.scope}</span>
    </div>
  );
}
