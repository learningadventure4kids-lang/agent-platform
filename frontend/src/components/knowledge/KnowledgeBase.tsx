import { useCallback, useEffect, useState } from "react";
import * as api from "../../api/client";
import { DocumentUpload } from "./DocumentUpload";
import { DocumentList } from "./DocumentList";

export function KnowledgeBase({ adminKey, agentId }: { adminKey: string; agentId: number }) {
  const [documents, setDocuments] = useState<api.KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [jobIds, setJobIds] = useState<Record<number, number>>({});

  const load = useCallback(async () => {
    const docs = await api.listDocuments(adminKey, agentId);
    setDocuments(docs);
    setLoading(false);
  }, [adminKey, agentId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleUploaded = (result: { document_id: number; job_id: number }) => {
    setJobIds((prev) => ({ ...prev, [result.document_id]: result.job_id }));
    load();
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="font-display text-lg text-parchment">Knowledge base</h2>
          <p className="text-sm text-dust">
            Documents the assistant can draw on when answering business-specific questions.
          </p>
        </div>
        <DocumentUpload adminKey={adminKey} agentId={agentId} onUploaded={handleUploaded} />
      </div>

      {loading ? (
        <p className="text-sm text-dust">Loading…</p>
      ) : (
        <DocumentList adminKey={adminKey} documents={documents} jobIds={jobIds} onChanged={load} />
      )}
    </div>
  );
}
