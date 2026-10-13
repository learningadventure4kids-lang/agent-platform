import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import * as api from "../../api/client";
import { Button } from "../ui/Button";

const ACCEPTED = ".pdf,.docx,.txt,.csv,.json,.md";

export function DocumentUpload({
  adminKey,
  agentId,
  onUploaded,
}: {
  adminKey: string;
  agentId: number;
  onUploaded: (result: { document_id: number; job_id: number }) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        const result = await api.uploadDocument(adminKey, agentId, file);
        onUploaded(result);
      }
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <Button size="sm" disabled={uploading} onClick={() => inputRef.current?.click()} className="gap-1.5">
        <Upload size={14} />
        {uploading ? "Uploading…" : "Upload document"}
      </Button>
      {error && <p className="mt-2 text-sm text-red-300">{error}</p>}
      <p className="mt-2 text-xs text-dust">Supported: PDF, DOCX, TXT, CSV, JSON, Markdown.</p>
    </div>
  );
}
