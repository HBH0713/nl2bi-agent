import { cn } from "../src/lib/utils";

describe("cn utility", () => {
  it("merges class names", () => {
    expect(cn("px-4", "py-2")).toBe("px-4 py-2");
    expect(cn("text-sm", false && "hidden")).toBe("text-sm");
  });
});
