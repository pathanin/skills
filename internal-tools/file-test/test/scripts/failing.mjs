export default async ({ page, expect }) => {
  await expect(page.locator('#count')).toHaveText('99', { timeout: 1000 });
};
