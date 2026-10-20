"use client";

import { useRouter } from "next/navigation";

import Icon from "@/components/Icon";
import { COURSE_COOKIE, saveCookie } from "@/lib/i18n";

// Make a course the current one, then go to its progress page.
export default function OpenCourse({ course, label }: { course: string; label: string }) {
  const router = useRouter();
  return (
    <button
      type="button"
      className="btn btn-primary"
      onClick={() => {
        saveCookie(COURSE_COOKIE, course);
        router.push("/");
        router.refresh();
      }}
    >
      {label}
      <Icon name="arrow" />
    </button>
  );
}
