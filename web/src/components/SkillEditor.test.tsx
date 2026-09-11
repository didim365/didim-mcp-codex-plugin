// 편집기 — Markdown 편집/미리보기 전환, 목록 입력 파싱, 권한 경고.

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SkillEditor, splitList, type EditorValue } from "./SkillEditor";

const BASE: EditorValue = {
  name: "이름",
  description: "설명",
  instructions: "# 제목\n본문",
  aliases: ["alias-a", "alias-b"],
  tools: ["didim-vault__list_my_resources"],
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("splitList", () => {
  it("쉼표로 나누고 공백·빈 값을 버린다", () => {
    expect(splitList("a, b ,, c ")).toEqual(["a", "b", "c"]);
    expect(splitList("")).toEqual([]);
  });
});

describe("SkillEditor", () => {
  it("신규 등록에서만 스킬 키를 보여준다", () => {
    const { rerender } = render(
      <SkillEditor value={BASE} onChange={() => {}} showIdentity={false} />,
    );
    expect(screen.queryByLabelText("스킬 키")).not.toBeInTheDocument();

    rerender(<SkillEditor value={BASE} onChange={() => {}} showIdentity />);
    expect(screen.getByLabelText("스킬 키")).toBeInTheDocument();
  });

  it("도구 목록이 권한이 아니라는 경고를 항상 보여준다", () => {
    render(<SkillEditor value={BASE} onChange={() => {}} showIdentity={false} />);
    expect(screen.getByText(/권한이 아닙니다/)).toBeInTheDocument();
  });

  it("미리보기로 전환하면 textarea 대신 본문을 그린다", async () => {
    render(<SkillEditor value={BASE} onChange={() => {}} showIdentity={false} />);
    expect(screen.getByLabelText("절차 본문")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "미리보기" }));

    expect(screen.queryByLabelText("절차 본문")).not.toBeInTheDocument();
    const preview = screen.getByLabelText("절차 본문 미리보기");
    expect(preview).toHaveTextContent("# 제목");
  });

  it("별칭을 쉼표로 입력하면 배열로 올려 준다", async () => {
    const onChange = vi.fn();
    render(
      <SkillEditor value={{ ...BASE, aliases: [] }} onChange={onChange} showIdentity={false} />,
    );
    await userEvent.type(screen.getByLabelText("별칭"), "x");
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ aliases: ["x"] }));
  });
});
