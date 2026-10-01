import "@testing-library/jest-dom/vitest";
import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { CameraScanner } from "@/features/circulation/camera-scanner";
import { librarian as t } from "@/locales/librarian";
const original = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");
afterEach(() => {
  cleanup();
  if (original) Object.defineProperty(navigator, "mediaDevices", original);
  else Reflect.deleteProperty(navigator, "mediaDevices");
});
it("permission denial offers manual fallback and never emits a token", async () => {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi
        .fn()
        .mockRejectedValue(new DOMException("Denied", "NotAllowedError")),
    },
  });
  const decoded = vi.fn();
  render(<CameraScanner onDecoded={decoded} onStart={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: t.camera }));
  expect(await screen.findByRole("alert")).toHaveTextContent(t.denied);
  expect(decoded).not.toHaveBeenCalled();
});
it("unavailable camera has a recoverable error", async () => {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: undefined,
  });
  render(<CameraScanner onDecoded={() => {}} onStart={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: t.camera }));
  expect(await screen.findByRole("alert")).toHaveTextContent(t.unavailable);
  expect(screen.getByRole("button", { name: t.camera })).toBeEnabled();
});
it("permission resolving after unmount immediately releases all tracks", async () => {
  let resolve!: (stream: MediaStream) => void;
  const stop = vi.fn();
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: () =>
        new Promise<MediaStream>((done) => {
          resolve = done;
        }),
    },
  });
  const { unmount } = render(
    <CameraScanner onDecoded={() => {}} onStart={() => {}} />,
  );
  fireEvent.click(screen.getByRole("button", { name: t.camera }));
  unmount();
  resolve({ getTracks: () => [{ stop }] } as unknown as MediaStream);
  await waitFor(() => expect(stop).toHaveBeenCalledOnce());
});
