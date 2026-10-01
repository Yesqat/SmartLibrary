// Test-only TCP forwarding keeps the configured HTTPS origin inside Docker.
// TLS remains end-to-end between Chromium and Nginx; no certificate is replaced.
const net = require("node:net");
const { spawn } = require("node:child_process");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const server = net.createServer((socket) => {
  const upstream = net.connect(443, "nginx");
  socket.pipe(upstream).pipe(socket);
  socket.on("error", () => upstream.destroy());
  upstream.on("error", () => socket.destroy());
  socket.on("close", () => upstream.destroy());
});
server.listen(8443, "127.0.0.1", () => {
  const runner = spawn(process.execPath, [
    "node_modules/@playwright/test/cli.js", "test",
    "--config", "playwright.production.config.ts", "--workers=1",
  ], {
    cwd: path.join(root, "frontend"), stdio: "inherit",
    env: { ...process.env, PLAYWRIGHT_CHANNEL: "chromium" },
  });
  runner.on("exit", (code) => process.exit(code ?? 1));
});
