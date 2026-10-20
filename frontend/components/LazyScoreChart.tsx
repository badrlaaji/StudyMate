"use client";

import dynamic from "next/dynamic";

// Recharts is heavy: load the chart after the page is shown (not in the first bundle).
const ScoreChart = dynamic(() => import("@/components/ScoreChart"), {
  ssr: false,
  loading: () => <div style={{ minHeight: 160 }} />,
});

export default ScoreChart;
