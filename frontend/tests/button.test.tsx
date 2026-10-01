import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Button } from "@/components/ui/button";
afterEach(cleanup);
it("a disabled submit control does not trigger the action", () => {
  const click = vi.fn();
  render(
    <Button disabled onClick={click}>
      Растау
    </Button>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Растау" }));
  expect(click).not.toHaveBeenCalled();
});
