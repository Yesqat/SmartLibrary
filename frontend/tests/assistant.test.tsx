import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Chat } from "@/features/assistant/chat";
import { MessageView } from "@/features/assistant/messages";
import { assistantApi, type Message } from "@/features/assistant/api";
import { assistant as t } from "@/locales/assistant";
import { ApiError } from "@/services/api-client";
const conversation = {
  id: "chat",
  title: "Кітаптар",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
function mount() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <Chat id="chat" />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(assistantApi, "detail").mockResolvedValue({
    conversation,
    messages: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
  });
});
afterEach(cleanup);
it("shows pending tool processing and prevents duplicate sends", async () => {
  const send = vi
    .spyOn(assistantApi, "send")
    .mockImplementation(() => new Promise(() => {}));
  mount();
  await screen.findByText(t.empty);
  fireEvent.click(screen.getByRole("button", { name: "Менің кітаптарым" }));
  fireEvent.click(screen.getByRole("button", { name: t.send }));
  await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
  expect(screen.getByRole("status")).toHaveTextContent(t.processing);
  expect(screen.getByRole("textbox", { name: t.input })).toBeDisabled();
  expect(screen.getByRole("button", { name: t.processing })).toBeDisabled();
});
it("keeps the question editable after safe provider failure for an explicit retry", async () => {
  vi.spyOn(assistantApi, "send").mockRejectedValue(
    new ApiError(503, "AI_SERVICE_UNAVAILABLE"),
  );
  mount();
  await screen.findByText(t.empty);
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "Кітап ұсын" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.send }));
  expect(await screen.findByRole("alert")).toHaveTextContent(t.unavailable);
  expect(screen.getByRole("textbox")).toHaveValue("Кітап ұсын");
  expect(screen.getByRole("button", { name: t.send })).toBeEnabled();
});
it("renders untrusted text without executable HTML and never reserves automatically", () => {
  const message: Message = {
    id: "message",
    role: "ASSISTANT",
    content: "<script>alert(1)</script>",
    created_at: conversation.created_at,
    error_code: null,
    books: [],
  };
  const { container } = render(<MessageView message={message} />);
  expect(screen.getByText(message.content)).toBeInTheDocument();
  expect(container.querySelector("script")).toBeNull();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
