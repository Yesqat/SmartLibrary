# Grounded AI Librarian (PHASE 15)

Reader-only `/assistant` provides persisted owned conversations, bounded history,
starter questions, processing/error states and real book cards. Other Readers and
staff cannot read a Reader's conversation. Core library services do not depend on
an external LLM.

## Architecture and grounding

`LLMClient` supports Groq Chat Completions and OpenAI Responses. Groq submits
the final answer plan through a local function call. OpenAI uses structured output.
The LLM interprets multilingual questions/follow-ups, selects read-only tools and
ranks their returned references. It cannot supply arbitrary final factual prose.
The server renders selected current evidence in the language of the question
(Kazakh, Russian or English) and validates every card against results retrieved
in that turn. Catalog titles, names and excerpts retain their original wording. This answer style
prevents model-written availability, due dates, rules and invented catalog IDs.
It is real LLM tool orchestration; factual formatting is deterministic backend code.
No production fake provider or generated fallback answer exists.

Allowlisted tools:

- search_books / semantic_search_books: real existing search with bounded query,
  availability/language filters and at most eight results; real search events persist.
- get_book_details / check_book_availability: actual catalog/copy aggregation.
- get_similar_books / get_recommendations: actual PHASE 13 algorithms and vectors.
- get_my_borrowings / get_my_reservations: authenticated Reader only, ten/page;
  no user_id input, account contacts, QR credentials or inventory identifiers sent.
- get_library_rules: fresh seven-setting circulation policy from PostgreSQL.

Tools revalidate the live Reader/session before execution. Unknown capabilities,
extra arguments, SQL and write requests fail before dispatch. No tool issues,
returns or reserves. Cards link to Book Details, where the Reader explicitly
presses the normal reservation button and all existing business rules apply.
Descriptions/user messages are untrusted; React escapes displayed content.
Failures produce unavailable evidence, never a fabricated empty catalog.

Final references are validated against this turn's tool outputs. Historical book
cards refresh current availability when loaded. Historical answer text is labeled
with its response time. Old facts are excluded from subsequent model context;
the model receives the previous intent and ordered public book titles/IDs, and queries facts again.
Context is capped at twenty messages and 16,000 characters. Each question is
limited to 2,000 characters, four provider rounds and six tools, with a 60-second
orchestration budget, up to 20 seconds per provider call and bounded HTTP output.

## Storage and concurrency

Existing ai_conversations/ai_messages/ai_message_books are used without a migration.
Creation/message mutations are owned, Origin-protected and rate-limited through
Redis: ten messages/Reader/minute, thirty/IP/minute, 200/Reader/day.
Conversations cap at 500/Reader and 400 messages/conversation as resource bounds.

Request UUIDs derive unique USER/ASSISTANT message IDs within the conversation.
Successful retries return the stored answer; different content with the same key
fails. Short transactions lock live User then owned Conversation, persist a pending
turn, release locks before provider calls, and revalidate before persisting output.
Concurrent turns receive AI_TURN_IN_PROGRESS. After 120 seconds an interrupted
pending turn can be superseded safely; the older writer cannot overwrite it.
Provider failures persist a safe error message/latency. Tool metadata stores only
allowlisted tool names/status, provider/model and validated book references; no raw
arguments, provider payloads, passwords, keys or credentials are logged.

## Configuration and unavailable behavior

Create a GroqCloud API key on your Free tier account. Put the following settings
in the private `.env` used by Docker Compose. Replace the placeholder with your
key. If switching providers, replace the existing provider and model values.
[Groq API keys](https://console.groq.com/keys) · [Free tier limits](https://console.groq.com/docs/rate-limits)

```dotenv
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=<your GroqCloud API key>
```

With the default template, setting only `GROQ_API_KEY` selects the same provider
and model. To use OpenAI, set `LLM_PROVIDER=openai`, an account-accessible
Responses/function-calling `LLM_MODEL` and `LLM_API_KEY`.

From the checkout containing the updated code, recreate the backend with
`docker compose up -d --build --no-deps backend`. For a Compose override or
production setup, pass your usual project, environment and Compose file options.
As a Reader, open `/assistant`, start a conversation and ask about the available
copies of a known catalog title. Compare the count and shelf to the book detail page.

Both adapters send bounded conversation context and tool results over HTTPS
to their fixed API host with redirects disabled. OpenAI requests use `store=false`.

Missing/unsupported configuration, exhausted provider quotas, network failures, timeouts, refusals, invalid
output and ungrounded references produce AI_SERVICE_UNAVAILABLE. Redis failure is
closed safely. Catalog, standard search, local recommendations and circulation
remain independent. New provider implementations belong behind LLMClient only.

## APIs

POST/GET `/api/v1/ai/conversations`; GET `/{id}` (paged newest-message window,
chronological within each page); POST `/{id}/messages` with content/request_id.
No client-selected owner. Returned message includes safe content, books, timestamp
and optional error_code. Raw tool/provider/auth secrets are not API fields.

## Verification

The automated suite checks the reader endpoint, real PostgreSQL copy states,
Redis, conversation ownership and a scripted Groq HTTP round trip.
A separate live check used Groq with an isolated catalog. In one conversation,
it recommended a Python book in Kazakh, reported zero available copies in Russian
after the last copy was reserved, returned the book's metadata in English and
reported an absent ISBN in Kazakh.

Provider documentation covers [Groq local tool calling](https://console.groq.com/docs/tool-use/local-tool-calling),
[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)
and [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs).
