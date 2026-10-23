// The client side of the answer stream (seam 3): the web app reads the stream the server
// writes. The recorded stream is the one the server tests check the server against.
import { expect, test } from "@playwright/test";
import { readEvents } from "../src/lib/sse";
import { recorded } from "./mocked";

function streamOf(text: string, chunkSize: number): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  let offset = 0;
  return new ReadableStream({
    pull(controller) {
      if (offset >= bytes.length) return controller.close();
      controller.enqueue(bytes.slice(offset, offset + chunkSize));
      offset += chunkSize;
    },
  });
}

async function collect(body: ReadableStream<Uint8Array>) {
  const events = [];
  for await (const event of readEvents(body)) events.push(event);
  return events;
}

const NO_AGENT = [
  { type: "error", data: { code: "no_agent" } },
  { type: "done", data: { run_id: "run-0001" } },
];

test("the client reads the server's recorded stream as its events, in order", async () => {
  expect(await collect(streamOf(await recorded("ask-no-agent.sse"), 4096))).toEqual(NO_AGENT);
});

test("the client reads the stream the same way when it arrives a few bytes at a time", async () => {
  const text = await recorded("ask-no-agent.sse");
  for (const size of [1, 3, 7]) {
    expect(await collect(streamOf(text, size))).toEqual(NO_AGENT);
  }
});

test("the client reads CRLF line ends, even when a chunk ends between CR and LF", async () => {
  const text = (await recorded("ask-no-agent.sse")).replaceAll("\n", "\r\n");
  for (const size of [1, 2, 3, 7]) {
    expect(await collect(streamOf(text, size))).toEqual(NO_AGENT);
  }
});

test("the client skips the server's keep-alive comments", async () => {
  const text = ": keep-alive\n\n" + (await recorded("ask-no-agent.sse")).replace("\n\n", "\n\n: keep-alive\n\n");
  expect(await collect(streamOf(text, 5))).toEqual(NO_AGENT);
});
