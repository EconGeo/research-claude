---
name: ztp-ollama
description: >
  Configure, verify and troubleshoot ZotPilot's local Ollama embedding provider —
  the fully-local, no-API-key indexing path. Trigger on: "set up ollama embeddings",
  "configure zotpilot for local embeddings", "use bge-large", "index without an API key",
  "zotpilot ollama", "switch embedding provider to ollama", "my embeddings are slow /
  failing", "connection refused on indexing", "embedding dimension mismatch". Use this
  INSTEAD OF ztp-setup's provider step whenever the target is Ollama — the setup wizard
  does not offer Ollama and will steer you to a different provider.
allowed-tools: Read, Bash
---

# ztp-ollama — the local Ollama embedding path

ZotPilot can embed entirely locally through [Ollama](https://ollama.com): no API key, no
per-token cost, nothing leaving the machine. This is the recommended path for a library of
licensed PDFs, where shipping full text to a cloud embedding endpoint is the thing you most
want to avoid.

## Read this first: the setup wizard does not know about Ollama

`zotpilot setup --provider` accepts only `gemini`, `dashscope` and `local`. **Ollama is not
in that list**, and there is no wizard flow for it. It is configured entirely through
`zotpilot config set`. If you run the wizard hoping to pick Ollama you will end up on a
different provider, and — because the embedding settings are part of the index fingerprint —
silently invalidate an existing index.

> `local` is **not** Ollama. `local` is a bundled `all-MiniLM-L6-v2` (384-dim) that runs
> in-process. Ollama is a separate server you run yourself, with much stronger retrieval
> models. Both are offline; they are not interchangeable, and they produce incompatible
> indexes.

## One-time setup

**1. Install Ollama and pull an embedding model.** `bge-large` is the default and the right
choice for academic prose — it is retrieval-optimized and 1024-dimensional.

```bash
ollama pull bge-large
```

**2. Point ZotPilot at it.** All four settings matter; set them together.

```bash
zotpilot config set embedding_provider ollama
zotpilot config set embedding_model bge-large
zotpilot config set embedding_dimensions 1024
zotpilot config set ollama_base_url http://localhost:11434
```

`ollama_base_url` defaults to `http://localhost:11434` and only needs setting if Ollama runs
on another host or port. Note it is the **bare Ollama root** — this provider calls Ollama's
native `/api/embed`, so do **not** append `/v1` as you would for an OpenAI-compatible client.

**3. Confirm, then index.**

```bash
zotpilot config list
zotpilot doctor
zotpilot index --limit 20
```

`doctor` treats Ollama as a keyless provider, so it should not complain about a missing API
key. `index` covers **all** Zotero libraries by default, including group libraries.

## `embedding_dimensions` must match the model — nothing checks it for you

On the Ollama path the configured dimension is passed straight through to the vector store
and is **never verified against what the server actually returns**. Set it wrong and you get
a corrupt index rather than an error.

| Model | `embedding_dimensions` | Notes |
|---|---|---|
| `bge-large` | `1024` | Default. Best general choice for academic text. |
| `mxbai-embed-large` | `1024` | Comparable quality; a reasonable alternative. |
| `snowflake-arctic-embed:l` | `1024` | Strong on short queries. |
| `nomic-embed-text` | `768` | Long context (8k), lighter. |
| `all-minilm` | `384` | Fast and weak; only for a smoke test. |

Verify a model's true dimension before trusting the table:

```bash
ollama pull nomic-embed-text && curl -s http://localhost:11434/api/embed -d '{"model":"nomic-embed-text","input":"test"}' | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["embeddings"][0]))'
```

## Changing any embedding setting requires a forced re-index

`embedding_provider`, `embedding_model`, `embedding_dimensions`, `chunk_size`,
`chunk_overlap`, the OCR language and the vision settings are hashed into a fingerprint
stored next to the vector database. When it changes, indexing logs a **warning and carries
on** — it does not re-index, and it does not stop. Old vectors from the previous model stay
in the collection and are silently compared against new ones, which quietly degrades every
search until you rebuild:

```bash
zotpilot index --force
```

Treat any embedding-settings change as "rebuild the index", not "adjust a setting".

## Why this provider prepends text to your queries

For any model with `bge` in its name, `embed_query` prefixes the query with the BAAI
retrieval instruction (`Represent this sentence for searching relevant passages:`) while
documents are embedded bare. That asymmetry is how BGE models are trained to be used and it
materially improves retrieval. It is automatic — do not add the prefix yourself, and do not
"fix" a query that looks oddly verbose in a debug log.

## Chunk sizing against the 512-token window

`bge-large` accepts 512 tokens. `chunk_size` is expressed in **estimated tokens**
(chars ÷ 4) and the embedder independently truncates at a 512-token budget (chars ÷ 3)
before sending. Keeping `chunk_size` at or below ~350 leaves comfortable headroom under
both estimates. If indexing logs `truncate_to_token_budget: truncated N chars`, chunks are
overflowing the model's window and losing their tails — lower `chunk_size` and re-index
with `--force`.

## Troubleshooting

**`Cannot reach ... is the server running?` / connection refused.** Ollama is not up. Start
it with `ollama serve` and confirm with `curl -s http://localhost:11434/api/tags`. Note that
**this provider does not retry** — unlike the Gemini and DashScope paths, it makes a single
attempt per batch, so a server that is merely slow to wake will fail the run outright rather
than recovering. Start Ollama first and let it settle before a long index.

**`model not found`.** The model name in config must exactly match an `ollama list` entry,
tag included (`snowflake-arctic-embed:l`, not `snowflake-arctic-embed`).

**Searches return irrelevant results after a model change.** The index is mixed. Rebuild
with `zotpilot index --force`.

**Indexing is slow.** Expected — embedding runs on local hardware in batches of 16. Index
incrementally with `--limit`; progress is journaled, so a later run resumes rather than
restarting.

## Related

- `ztp-setup` — installation, MCP registration and the *other* providers. Its provider step
  does not apply here.
- `ztp-research`, `ztp-review` — the workflows that consume the index this builds.
