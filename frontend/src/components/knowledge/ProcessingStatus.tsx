import { useEffect, useState } from "react";
import * as api from "../../api/client";
import { StatusBadge } from "../ui/StatusBadge";

export function ProcessingStatus({
  adminKey,
  jobId,
  initialStatus,
  onSettled,
}: {
  adminKey: string;
  jobId: number;
  initialStatus: string;
  onSettled: () => void;
}) {
  const [job, setJob] = useState<api.KnowledgeJobStatus | null>(null);

  useEffect(() => {
    if (initialStatus === "READY" || initialStatus === "FAILED") return;
    let cancelled = false;
    let handle: ReturnType<typeof setInterval>;

    const poll = async () => {
      try {
        const j = await api.getKnowledgeJob(adminKey, jobId);
        if (cancelled) return;
        setJob(j);
        if (j.status === "COMPLETED" || j.status === "FAILED") {
          clearInterval(handle);
          onSettled();
        }
      } catch {
        clearInterval(handle);
      }
    };

    poll();
    handle = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(handle);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  if (!job) return <StatusBadge status={initialStatus.toLowerCase()} />;

  if (job.status === "RUNNING" || job.status === "PENDING") {
    return (
      <div className="flex items-center gap-2">
        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-ink-border">
          <div
            className="h-full rounded-full bg-brass transition-all"
            style={{ width: `${Math.max(job.progress, 5)}%` }}
          />
        </div>
        <span className="text-xs text-dust">{job.progress}%</span>
      </div>
    );
  }

  return <StatusBadge status={job.status === "COMPLETED" ? "ready" : "failed"} />;
}
