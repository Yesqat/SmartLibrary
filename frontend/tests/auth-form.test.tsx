import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { AuthForm } from "@/features/auth/auth-form";
import { kk } from "@/locales/kk";
import { ApiError } from "@/services/api-client";

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
  replace: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
}));
vi.mock("@/services/api-client", async (original) => ({
  ...(await original<typeof import("@/services/api-client")>()),
  login: mocks.login,
  register: mocks.register,
}));
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

function input(name: string, value: string) {
  fireEvent.change(screen.getByLabelText(name, { exact: false }), {
    target: { value },
  });
}
it("requires a valid login email and a password", () => {
  render(<AuthForm mode="login" />);
  input(kk.auth.email, "invalid");
  fireEvent.submit(
    screen.getByRole("button", { name: kk.auth.login }).closest("form")!,
  );
  expect(mocks.login).not.toHaveBeenCalled();
  expect(screen.getByRole("alert").textContent).toContain(kk.auth.required);
});
it("rejects mismatching registration passwords before a request", () => {
  render(<AuthForm mode="register" />);
  input(kk.auth.firstName + " *", "Айдана");
  input(kk.auth.lastName + " *", "Оқырман");
  input(kk.auth.email, "reader@example.com");
  fireEvent.change(document.querySelector('[name="password"]')!, {
    target: { value: "Secure reader password!" },
  });
  input(kk.auth.confirm, "Different password!");
  fireEvent.submit(
    screen.getByRole("button", { name: kk.auth.register }).closest("form")!,
  );
  expect(mocks.register).not.toHaveBeenCalled();
  expect(screen.getByRole("alert").textContent).toContain(kk.auth.mismatch);
});
it("submits only public reader fields and shows registration success", async () => {
  mocks.register.mockResolvedValue({ role: "READER" });
  render(<AuthForm mode="register" />);
  input(kk.auth.firstName + " *", "Айдана");
  input(kk.auth.lastName + " *", "Оқырман");
  input(kk.auth.email, "reader@example.com");
  fireEvent.change(document.querySelector('[name="password"]')!, {
    target: { value: "Secure reader password!" },
  });
  input(kk.auth.confirm, "Secure reader password!");
  fireEvent.submit(
    screen.getByRole("button", { name: kk.auth.register }).closest("form")!,
  );
  await waitFor(() =>
    expect(screen.getByRole("status").textContent).toContain(
      kk.auth.registered,
    ),
  );
  expect(mocks.register).toHaveBeenCalledWith({
    email: "reader@example.com",
    password: "Secure reader password!",
    first_name: "Айдана",
    last_name: "Оқырман",
    phone: null,
  });
});
it("shows a safe login error and releases the busy state", async () => {
  mocks.login.mockRejectedValue(new ApiError(401, "INVALID_CREDENTIALS"));
  render(<AuthForm mode="login" />);
  input(kk.auth.email, "reader@example.com");
  input(kk.auth.password, "wrong");
  fireEvent.submit(
    screen.getByRole("button", { name: kk.auth.login }).closest("form")!,
  );
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain(
      kk.auth.errors.INVALID_CREDENTIALS,
    ),
  );
  expect(
    (screen.getByRole("button", { name: kk.auth.login }) as HTMLButtonElement)
      .disabled,
  ).toBe(false);
});
it("prevents a duplicate login while waiting", async () => {
  mocks.login.mockReturnValue(new Promise(() => {}));
  render(<AuthForm mode="login" />);
  input(kk.auth.email, "reader@example.com");
  input(kk.auth.password, "password");
  const form = screen
    .getByRole("button", { name: kk.auth.login })
    .closest("form")!;
  fireEvent.submit(form);
  fireEvent.submit(form);
  expect(mocks.login).toHaveBeenCalledTimes(1);
  expect(
    (screen.getByRole("button", { name: kk.auth.pending }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
});
