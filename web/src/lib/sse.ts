// The answer stream: POST a request, then read the server's text/event-stream as events.
// EventSource cannot POST, so this reads the response body itself. Each event's data is JSON.
// Comment lines (the server's keep-alives) are skipped.

export type StreamEvent = { type: string; data: unknown };

export async function* streamEvents(
  path: string,
  payload: unknown,
  init: { signal?: AbortSignal } = {},
): AsyncGenerator<StreamEvent> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(payload),
    signal: init.signal,
  });
  if (!response.ok || !response.body) {
    const body = response.ok ? null : await response.json().catch(() => null);
    throw new StreamError(response.status, body && typeof body === "object" ? (body as Record<string, unknown>) : null);
  }
  yield* readEvents(response.body);
}

export class StreamError extends Error {
  // body: the JSON the server answered with instead of a stream, when it sent some.
  constructor(
    readonly status: number,
    readonly body: Record<string, unknown> | null = null,
  ) {
    super(`The stream did not open: HTTP ${status}.`);
  }
}

export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<StreamEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let type = "message";
  let data: string[] = [];
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      // A chunk that ends in CR may be half of a CRLF, so that CR waits for the next chunk.
      const held = !done && buffer.endsWith("\r") ? "\r" : "";
      const lines = buffer.slice(0, buffer.length - held.length).split(/\r\n|\r|\n/);
      buffer = done ? "" : (lines.pop() ?? "") + held;
      for (const line of lines) {
        if (line === "") {
          if (data.length) yield { type, data: JSON.parse(data.join("\n")) };
          type = "message";
          data = [];
        } else if (!line.startsWith(":")) {
          const colon = line.indexOf(":");
          const field = colon === -1 ? line : line.slice(0, colon);
          const text = colon === -1 ? "" : line.slice(colon + 1).replace(/^ /, "");
          if (field === "event") type = text;
          else if (field === "data") data.push(text);
        }
      }
      if (done) {
        if (data.length) yield { type, data: JSON.parse(data.join("\n")) };
        return;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
