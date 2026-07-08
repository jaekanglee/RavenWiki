import { describe, expect, it } from "vitest";
import {
  findClosestNodeHit,
  isStationaryClickGesture,
} from "../src/components/GraphCanvas";

describe("GraphCanvas direct click hit detection", () => {
  it("picks the closest node within the padded hit radius", () => {
    const hit = findClosestNodeHit(
      [
        { id: "a", x: 100, y: 100, weight: 1 },
        { id: "b", x: 140, y: 100, weight: 8 },
      ],
      { x: 132, y: 100 },
      "normal"
    );

    expect(hit?.id).toBe("b");
  });

  it("returns null when the pointer lands outside every node radius", () => {
    const hit = findClosestNodeHit(
      [{ id: "solo", x: 100, y: 100, weight: 1 }],
      { x: 180, y: 180 },
      "normal"
    );

    expect(hit).toBeNull();
  });

  it("uses a looser movement tolerance for touch than mouse", () => {
    expect(
      isStationaryClickGesture(
        { x: 100, y: 100 },
        { x: 108, y: 108 },
        "mouse"
      )
    ).toBe(false);

    expect(
      isStationaryClickGesture(
        { x: 100, y: 100 },
        { x: 108, y: 108 },
        "touch"
      )
    ).toBe(true);
  });
});
