// jsdom 에는 `<dialog>.showModal()` 이 없다. Publish/Rollback 확인 modal 이 네이티브
// dialog 를 쓰므로 stub 한다 — 화면 쪽에서 dialog 를 피하는 식으로 우회하지 않는다.
import "@testing-library/jest-dom/vitest";

if (typeof HTMLDialogElement !== "undefined") {
  HTMLDialogElement.prototype.showModal ??= function showModal(this: HTMLDialogElement) {
    this.open = true;
  };
  HTMLDialogElement.prototype.close ??= function close(this: HTMLDialogElement) {
    this.open = false;
  };
}
