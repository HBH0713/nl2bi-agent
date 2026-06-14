import { render, screen } from "@testing-library/react";
import DashboardPage from "../src/app/dashboard/page";

describe("DashboardPage", () => {
  it("renders overview and stat cards", () => {
    render(<DashboardPage />);
    expect(screen.getByText("概览")).toBeTruthy();
    expect(screen.getByText("已分析简历")).toBeTruthy();
    expect(screen.getByText("平均评分")).toBeTruthy();
    expect(screen.getByText("面试题库")).toBeTruthy();
  });
});
