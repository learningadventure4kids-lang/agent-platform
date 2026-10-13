import { AlertCircle, RotateCw, Trash2 } from "lucide-react";
import * as api from "../../api/client";
import { ProcessingStatus } from "./ProcessingStatus";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentList({
  adminKey,
  documents,
  jobIds,
  onChanged,
}: {
  adminKey: string;
  documents: api.KnowledgeDocument[];
  jobIds: Record<number, number>;
  onChanged: () => void;
}) {
  const remove = async (id: number) => {
    if (!confirm("Delete this document? It will no longer be searchable.")) return;
    await api.deleteDocument(adminKey, id);
    onChanged();
  };

  const reprocess = async (id: number) => {
    await api.reprocessDocument(adminKey, id);
    onChanged();
  };

  if (documents.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-ink-border px-6 py-10 text-center text-sm text-dust">
        No documents yet. Upload a PDF, DOCX, TXT, CSV, JSON, or Markdown file to get started.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-ink-border">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-ink-border text-xs uppercase tracking-wide text-dust/70">
            <th className="px-4 py-3 font-medium">Filename</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium">Size</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Chunks</th>
            <th className="px-4 py-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((d) => (
            <tr key={d.id} className="border-b border-ink-border/60 last:border-0">
              <td className="px-4 py-3 text-parchment">{d.original_filename}</td>
              <td className="px-4 py-3 uppercase text-dust-light">{d.file_type}</td>
              <td className="px-4 py-3 text-dust-light">{formatSize(d.file_size)}</td>
              <td className="px-4 py-3">
                {jobIds[d.id] ? (
                  <ProcessingStatus
                    adminKey={adminKey}
                    jobId={jobIds[d.id]}
                    initialStatus={d.status}
                    onSettled={onChanged}
                  />
                ) : (
                  <span className="text-xs capitalize text-dust-light">{d.status.toLowerCase()}</span>
                )}
                {d.status === "FAILED" && d.processing_error && (
                  <p className="mt-1 flex items-start gap-1 text-xs text-red-300">
                    <AlertCircle size={12} className="mt-0.5 shrink-0" />
                    {d.processing_error}
                  </p>
                )}
              </td>
              <td className="px-4 py-3 tabular-nums text-dust-light">{d.chunk_count || "—"}</td>
              <td className="px-4 py-3">
                <div className="flex gap-1.5">
                  <button
                    onClick={() => reprocess(d.id)}
                    title="Reprocess"
                    className="rounded-full p-1.5 text-dust hover:bg-white/5 hover:text-parchment"
                  >
                    <RotateCw size={14} />
                  </button>
                  <button
                    onClick={() => remove(d.id)}
                    title="Delete"
                    className="rounded-full p-1.5 text-dust hover:bg-red-500/10 hover:text-red-300"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
