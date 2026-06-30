import { describe, it, expect } from "vitest";
import { preprocessWikilinks } from "../src/lib/wikilink";

describe("preprocessWikilinks", () => {
    it("rewrites simple [[slug]] into a markdown link", () => {
        const out = preprocessWikilinks("see [[concepts/wiki]] please", "harumoa");
        expect(out).toBe(
            "see [concepts/wiki](/page/harumoa/concepts%2Fwiki) please"
        );
    });

    it("preserves ? placeholder intent (inside wikilink brackets)", () => {
        const out = preprocessWikilinks("see [[foo?]]", "harumoa");
        expect(out).toBe(
            "see [foo](/page/harumoa/foo?placeholder=true)"
        );
    });

    it("preserves ! broken intent (inside wikilink brackets)", () => {
        const out = preprocessWikilinks("see [[bar!]]", "harumoa");
        expect(out).toBe(
            "see [bar](/page/harumoa/bar?broken=true)"
        );
    });

    it("handles aliased [[slug|alias]] (alias dropped, slug as display)", () => {
        const out = preprocessWikilinks(
            "hello [[person/hermes|Hermes]]",
            "harumoa"
        );
        expect(out).toBe(
            "hello [person/hermes](/page/harumoa/person%2Fhermes)"
        );
    });

    it("handles anchor [[slug#heading]]", () => {
        const out = preprocessWikilinks(
            "see [[foo#section]]",
            "harumoa"
        );
        // #section은 v0.7.5+에서 제거 (URL 충돌 방지, anchor는 다음 단계 후보)
        expect(out).toBe("see [foo](/page/harumoa/foo)");
    });

    it("is a no-op when there are no wikilinks", () => {
        const out = preprocessWikilinks("no links here at all", "harumoa");
        expect(out).toBe("no links here at all");
    });

    it("URL-encodes vault and slug separately", () => {
        const out = preprocessWikilinks(
            "see [[concepts/wiki]] please",
            "raven-dev"
        );
        expect(out).toBe(
            "see [concepts/wiki](/page/raven-dev/concepts%2Fwiki) please"
        );
    });

    it("handles empty content", () => {
        expect(preprocessWikilinks("", "harumoa")).toBe("");
    });

    it("handles multiple wikilinks in one content", () => {
        const out = preprocessWikilinks(
            "[[a]] and [[b]] and [[c]]",
            "harumoa"
        );
        expect(out).toBe(
            "[a](/page/harumoa/a) and [b](/page/harumoa/b) and [c](/page/harumoa/c)"
        );
    });
});