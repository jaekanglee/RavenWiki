/* v0.6.26+ — <Modal> 공통 컴포넌트.
 *
 * 사용자 원칙 (2026-06-29 §13): "재사용 컴포넌트 우선". 4개 모달이 같은
 * backdrop/dim-click/dim-esc/z-index 패턴 반복 → <Modal> 추출.
 *
 * Contract:
 *  1. open=true면 body 직속 portal로 모달 렌더
 *  2. open=false면 null (트리에서 unmount)
 *  3. backdrop click 시 onClose 호출
 *  4. Escape 키로 onClose 호출
 *  5. width/maxWidth 커스터마이즈 가능
 *  6. position: fixed + inset:0 + z-index (기본 80)
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Modal } from "../src/components/ui/Modal";

describe("Modal contract (v0.6.26)", () => {
  it("renders nothing when closed", () => {
    render(<Modal open={false} onClose={() => {}}>body</Modal>);
    expect(screen.queryByText("body")).toBeNull();
  });

  it("renders in document.body (portal) when open", () => {
    render(<Modal open={true} onClose={() => {}}>body</Modal>);
    const modalText = screen.getByText("body");
    // modalText의 부모 div는 position:fixed
    const container = modalText.closest('div[style*="position: fixed"]');
    expect(container).toBeTruthy();
    expect(container!.parentElement).toBe(document.body);
  });

  it("backdrop click triggers onClose", () => {
    const onClose = vi.fn();
    render(<Modal open={true} onClose={onClose}>body</Modal>);
    const backdrop = screen.getByText("body").closest('div[style*="position: fixed"]')!;
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("click inside content does NOT trigger onClose (stopPropagation)", () => {
    const onClose = vi.fn();
    render(
      <Modal open={true} onClose={onClose}>
        <button>action</button>
      </Modal>
    );
    fireEvent.click(screen.getByRole("button", { name: /action/ }));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("Escape key triggers onClose", () => {
    const onClose = vi.fn();
    render(<Modal open={true} onClose={onClose}>body</Modal>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("accepts custom maxWidth", () => {
    render(
      <Modal open={true} onClose={() => {}} maxWidth={600}>
        <span>content</span>
      </Modal>
    );
    const card = screen.getByText("content").parentElement!;
    expect((card as HTMLElement).style.maxWidth).toBe("600px");
  });
});