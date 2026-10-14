export default async ({ page, expect, log }) => {
  await page.click('#inc');
  await page.click('#inc');
  await expect(page.locator('#count')).toHaveText('2');
  log('count after two clicks:', await page.textContent('#count'));
  await page.reload();
  await expect(page.locator('#count')).toHaveText('2'); // persisted
};
