import { test, expect } from "@playwright/test";
test("loads a real scenario, edits, validates, executes, charts, exports and reopens history", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Research overview" }),
  ).toBeVisible();
  await expect(page.locator(".stat-card strong").first()).toHaveText(
    /^[0-9,]+$/,
  );
  await expect(
    page
      .locator(".stat-card")
      .filter({ hasText: "Available scenarios" })
      .locator("strong"),
  ).toHaveText(/^[1-9][0-9,]*$/);
  await page.screenshot({
    path: "test-results/screenshots/overview.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Scenarios", exact: true }).click();
  await page.getByRole("button", { name: "Configure →" }).first().click();
  await expect(
    page.getByLabel("Population profile").getByRole("option"),
  ).not.toHaveCount(1);
  await page.getByLabel("Population profile").selectOption({ index: 1 });
  await expect(page.getByText(/Population profile loaded:/)).toBeVisible();
  await page
    .getByLabel("Run name", { exact: true })
    .fill("Playwright small research run");
  await page
    .locator("summary")
    .filter({ hasText: /^Population$/ })
    .click();
  await page.getByLabel("Size", { exact: true }).first().fill("20");
  await page.getByLabel("Duration Months", { exact: true }).first().fill("1");
  await page.screenshot({
    path: "test-results/screenshots/builder.png",
    fullPage: true,
  });
  const editorButton = page.getByRole("button", {
    name: "Advanced JSON / YAML",
  });
  await editorButton.click();
  const editor = page.getByLabel("Configuration editor");
  const config = JSON.parse(await editor.inputValue());
  config.experiment.trials = 1;
  config.experiment.grid = {};
  config.experiment.variants = ["control", "unprotected", "defended"];
  config.simulation.voting.strategies = ["equal"];
  config.attacks = [];
  config.defenses = [];
  config.elections.interval_months = 1;
  await editor.fill(JSON.stringify(config, null, 2));
  await page.getByRole("button", { name: "Validate configuration" }).click();
  await expect(page.getByText(/Configuration valid/)).toBeVisible();
  await page
    .getByRole("button", { name: "Save configuration", exact: true })
    .click();
  await expect(
    page.getByText("Configuration saved.", { exact: true }),
  ).toBeVisible();
  await expect(
    page
      .getByLabel("Saved configurations")
      .getByRole("option", { name: "Playwright small research run" })
      .first(),
  ).toBeAttached();
  await page.getByRole("button", { name: "Run simulation →" }).click();
  await expect(page).toHaveURL(/results\//);
  await expect(page.getByText("completed", { exact: true })).toBeVisible({
    timeout: 120000,
  });
  await expect(page.getByRole("img", { name: /chart/ })).toBeVisible();
  await page.locator(".plot .main-svg").first().waitFor();
  await page.getByRole("button", { name: "Governance", exact: true }).click();
  const metricSelect = page.getByLabel("Metric / Y axis");
  const gini = await metricSelect
    .locator("option")
    .evaluateAll((options) =>
      options
        .map((option) => (option as HTMLOptionElement).value)
        .find((value) => /gini/i.test(value)),
    );
  if (gini) await metricSelect.selectOption(gini);
  await page.screenshot({
    path: "test-results/screenshots/results.png",
    fullPage: true,
  });
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "CSV ↓" }).click();
  await expect((await download).suggestedFilename()).toMatch(/\.csv$/);
  await page.getByRole("link", { name: "Run History", exact: true }).click();
  await page
    .getByRole("link", { name: "Playwright small research run", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Results Explorer" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Run History", exact: true }).click();
  const row = page
    .getByRole("row")
    .filter({
      has: page.getByRole("link", {
        name: "Playwright small research run",
        exact: true,
      }),
    })
    .first();
  await row.getByRole("button", { name: "Rerun", exact: true }).click();
  await expect(page).toHaveURL(/results\//);
  await expect(page.locator(".status.completed")).toBeVisible({
    timeout: 120000,
  });
  await page.getByRole("link", { name: "Compare", exact: true }).click();
  await page
    .getByRole("checkbox", { name: /^Playwright small research run [0-9a-f]{8}/ })
    .first()
    .check();
  await page
    .getByRole("checkbox", { name: /^Playwright small research run rerun / })
    .first()
    .check();
  await page
    .getByRole("button", { name: "Compare selected runs", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Matched-trial differences" }),
  ).toBeVisible();
});
test("cancels real queued or running computation from run monitor", async ({
  page,
  request,
}) => {
  const capabilities = await (await request.get("/api/v1/capabilities")).json();
  const config = capabilities.defaults;
  config.simulation.population.size = 3000;
  config.timeline.duration_months = 24;
  config.experiment.trials = 20;
  const response = await request.post("/api/v1/runs", {
    data: {
      name: "Playwright cancellation",
      description: "",
      kind: "experiment",
      configuration: config,
    },
  });
  expect(response.ok()).toBeTruthy();
  const run = await response.json();
  await page.goto(`/results/${run.id}`);
  await page.getByRole("button", { name: "Cancel run", exact: true }).click();
  await expect(page.getByText("cancelled", { exact: true })).toBeVisible();
  await expect(page.getByRole("progressbar")).toHaveCount(0);
});
