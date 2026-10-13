# Example knowledge documents

Sample files to upload through the admin dashboard's Knowledge Base page
so you can try the RAG feature immediately, without needing your own
business documents yet.

## Kaur Jewellery (`kaur-jewellery/`)

- `return-policy.md`
- `shipping-policy.md`
- `faq.json` (a list of Q&A pairs -- demonstrates the JSON/FAQ loader path)

## Real Estate (`real-estate/`)

- `mortgage-policy.md`
- `communities.txt`
- `faq.csv` (demonstrates the CSV loader path)

## How to use these

1. Start the platform (`./run.sh`, `run.bat`, or `docker compose up`).
2. Sign in to the admin dashboard, open **Agents**, click into
   **Kaur Jewellery** (or **Real Estate**), then **Knowledge base**.
3. Upload the files from the matching folder above.
4. Wait for status to move from "Processing" to "Ready" (a few seconds
   with the deterministic/local setup; longer with a real embedding model
   on first run while Ollama loads it).
5. Open the widget (or use `POST /api/chat` directly) with that agent's
   token and ask a question the documents actually answer -- see
   "Example RAG conversation" in the main README for a worked example,
   including proof that asking the jewellery agent a real-estate question
   correctly returns no knowledge-base match.
