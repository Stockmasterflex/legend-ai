const fs = require('fs');
(async () => {
  const puppeteer = require('puppeteer');
  const browser = await puppeteer.launch({args:['--no-sandbox','--disable-setuid-sandbox']});
  const page = await browser.newPage();
  const html = fs.readFileSync('chart-template.html','utf-8');
  await page.setContent(html, {waitUntil:'networkidle0'});
  await page.screenshot({path:'reports/SMOKE.png'});
  await browser.close();
  console.log('Wrote reports/SMOKE.png');
})();
