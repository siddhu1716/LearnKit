#!/usr/bin/env node

import { appendFileSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";

function logError(message) {
  try {
    const path = join(homedir(), ".learnkit", "plugin", "hook-errors.log");
    mkdirSync(dirname(path), { recursive: true });
    appendFileSync(path, `${new Date().toISOString()} ${message}\n`, "utf8");
  } catch {
    // Hook failures must never break the host agent.
  }
}

async function main() {
  const event = process.argv[2];
  if (!event) return;

  let input = "";
  for await (const chunk of process.stdin) input += chunk;
  if (!input.trim()) input = "{}";

  const command = process.env.LEARNKIT_COMMAND || "learnkit";
  const result = spawnSync(command, ["plugin", "hook", event], {
    input,
    encoding: "utf8",
    windowsHide: true,
    timeout: 10_000,
  });

  if (result.error) {
    logError(`${event}: ${result.error.message}`);
    return;
  }
  if (result.status !== 0) {
    logError(`${event}: learnkit exited ${result.status}: ${(result.stderr || "").slice(0, 1000)}`);
    return;
  }
  if (result.stdout) process.stdout.write(result.stdout);
}

main().catch((error) => logError(error?.stack || String(error)));