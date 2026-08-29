import { expect, test, type Page } from "@playwright/test";

async function startFromGoal(page: Page, goal: string, interest?: string) {
	await page.goto("/");
	await page.evaluate(
		({ goalValue, interestValue }: { goalValue: string; interestValue?: string }) => {
			window.localStorage.setItem("pathmind_onboarding", JSON.stringify({ goal: goalValue, createdAt: new Date().toISOString() }));
			if (interestValue) {
				window.localStorage.setItem("pathmind_profile", JSON.stringify({ interest: interestValue }));
			}
		},
		{ goalValue: goal, interestValue: interest },
	);
	await page.goto("/analysis");
	await expect(page).toHaveURL(/\/analysis/);
	await expect(page.getByText(/Understanding your goal|Destination found|More detail needed|We could not analyze that goal/i)).toBeVisible({ timeout: 15000 });
}

async function loadAssessment(page: Page) {
	await expect(page.getByText(/Assessment complete|Diagnostic complete|Show us what you know/i)).toBeVisible({ timeout: 15000 });
}

test("data analyst with cricket keeps goal, assessment, roadmap, and project aligned", async ({ page }) => {
	await startFromGoal(page, "I want to become a data analyst", "cricket");
	await expect(page.getByText(/Destination found/i)).toBeVisible({ timeout: 15000 });
	await expect(page.getByText(/Data Scientist|Data Analyst/i)).toBeVisible();
	await page.getByRole("link", { name: /Continue to diagnostic/i }).click({ force: true });
	await expect(page).toHaveURL(/\/assessment/);

	await loadAssessment(page);
	await page.getByRole("button", { name: /Begin diagnostic/i }).click();
	await expect(page.getByText(/Career diagnostic/i)).toBeVisible({ timeout: 15000 });
	const firstQuestion = page.locator("article").filter({ hasText: /question|What is|Which idea/i }).first();
	await expect(firstQuestion).toBeVisible();
	const firstOption = firstQuestion.getByRole("button").first();
	await firstOption.click();
	for (const question of await page.locator("article").filter({ hasText: /question|What is|Which idea/i }).all()) {
		const option = question.getByRole("button").first();
		await option.click();
	}
	await page.getByRole("button", { name: /Submit assessment/i }).click();
	await expect(page.getByText(/Diagnostic complete|Assessment complete/i)).toBeVisible({ timeout: 15000 });
	await page.getByRole("link", { name: /Continue to path preview/i }).click();
	await expect(page).toHaveURL(/\/path-preview/);
	await expect(page.getByText(/IPL Player Performance Analytics/i)).toBeVisible();
	await page.reload();
	await expect(page.getByText(/IPL Player Performance Analytics/i)).toBeVisible();
	await page.getByRole("link", { name: /Continue to Home/i }).click();
	await expect(page).toHaveURL(/\/home/);
	await page.reload();
	await expect(page.getByText(/Data Scientist|Data Analyst/i)).toBeVisible();
	await page.getByRole("link", { name: /Start now/i }).click();
	await expect(page).toHaveURL(/\/path/);
	await expect(page.getByText(/Learning GPS/i)).toBeVisible();
	await page.getByRole("link", { name: /Project/i }).click();
	await expect(page).toHaveURL(/\/project/);
	await expect(page.getByText(/IPL Player Performance Analytics/i)).toBeVisible();
	await expect(page.getByText(/Current milestone/i)).toBeVisible();
	await page.getByRole("button", { name: /Ask AI Mentor|Ask AI Coach/i }).click();
	await expect(page.getByText(/Project Mentor|Project Workspace/i)).toBeVisible({ timeout: 15000 });
});

test("cloud engineer flow selects cloud-relevant content", async ({ page }) => {
	await startFromGoal(page, "I want to become a cloud engineer");
	await expect(page.getByRole("link", { name: /Continue to diagnostic/i })).toBeVisible({ timeout: 15000 });
	await page.getByRole("link", { name: /Continue to diagnostic/i }).click({ force: true });
	await expect(page).toHaveURL(/\/assessment/);
	await expect(page.getByText(/Cloud Engineer/i)).toBeVisible({ timeout: 15000 });
	await page.getByRole("button", { name: /Begin diagnostic/i }).click();
	await expect(page.getByText(/Career diagnostic/i)).toBeVisible({ timeout: 15000 });
	for (const question of await page.locator("article").all()) {
		await question.getByRole("button").first().click();
	}
	await page.getByRole("button", { name: /Submit assessment/i }).click();
	await expect(page.getByText(/Diagnostic complete|Assessment complete/i)).toBeVisible({ timeout: 15000 });
});

test("cybersecurity engineer flow selects security-relevant content", async ({ page }) => {
	await startFromGoal(page, "I want to become a cybersecurity engineer");
	await expect(page.getByRole("link", { name: /Continue to diagnostic/i })).toBeVisible({ timeout: 15000 });
	await page.getByRole("link", { name: /Continue to diagnostic/i }).click({ force: true });
	await expect(page).toHaveURL(/\/assessment/);
	await expect(page.getByText(/Cybersecurity/i)).toBeVisible({ timeout: 15000 });
});

test("doctor remains outside scope", async ({ page }) => {
	await startFromGoal(page, "I want to become a doctor");
	await expect(page.getByText(/outside scope|More detail needed|cannot match|We could not analyze that goal/i)).toBeVisible({ timeout: 15000 });
	await expect(page.getByText(/Backend AI Developer/i)).not.toBeVisible();
});

test("analysis failure surfaces a usable error", async ({ page }) => {
	await page.route("**/api/analyze-goal", async (route) => {
		await route.abort();
	});
	await page.goto("/");
	await page.getByLabel("Your career goal").fill("I want to become a data analyst");
	await page.getByRole("button", { name: "Build my path" }).click();
	await page.goto("/analysis");
	await expect(page.getByText(/temporarily unavailable|could not analyze|We could not analyze that goal/i)).toBeVisible({ timeout: 15000 });
});

test("login details populate the learner profile", async ({ page }) => {
	await page.goto("/login");
	await page.getByLabel("Full name").fill("Alex Morgan");
	await page.getByLabel("Email address").fill("alex@example.com");
	await page.getByLabel("Password").fill("not-stored-password");
	await page.getByRole("button", { name: /Continue to profile/i }).click();
	await expect(page).toHaveURL(/\/profile/);
	await expect(page.getByRole("heading", { name: "Alex Morgan" })).toBeVisible();
	await expect(page.getByText("alex@example.com")).toBeVisible();
});
