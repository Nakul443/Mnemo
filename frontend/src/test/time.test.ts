// this file is responsible for testing the relativeTime function

import { describe, expect, it } from "vitest";
import { relativeTime } from "../lib/time";

describe("relativeTime", () => {
  const now = 1_000_000_000_000;

  it("formats seconds as just now", () => {
    expect(relativeTime(now - 10_000, now)).toBe("just now");
    expect(relativeTime(now - 59_000, now)).toBe("just now");
  });

  it("formats minutes", () => {
    expect(relativeTime(now - 60_000, now)).toBe("1 min ago");
    expect(relativeTime(now - 300_000, now)).toBe("5 min ago");
  });

  it("formats hours", () => {
    expect(relativeTime(now - 3_600_000, now)).toBe("1 h ago");
    expect(relativeTime(now - 7_200_000, now)).toBe("2 h ago");
  });

  it("formats days", () => {
    expect(relativeTime(now - 86_400_000, now)).toBe("1 days ago");
    expect(relativeTime(now - 259_200_000, now)).toBe("3 days ago");
  });

  it("formats weeks for >= 30 days", () => {
    expect(relativeTime(now - 3_024_000_000, now)).toBe("5 weeks ago");
  });
});
