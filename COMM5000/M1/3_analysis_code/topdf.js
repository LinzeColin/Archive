const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const b = await chromium.launch({executablePath: process.env.CHROME || undefined});
  const p = await b.newPage();
  await p.goto('file://' + process.cwd() + '/' + process.argv[2], {waitUntil: 'networkidle'});
  await p.evaluate(() => document.fonts.ready);
  await p.pdf({path: process.argv[3], format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<div></div>',
    footerTemplate: '<div style="width:100%;font-size:7px;font-family:Liberation Sans,Arial,sans-serif;color:#8a8984;padding:0 16mm;display:flex;justify-content:space-between"><span>COMM5000 Milestone 1 · Preliminary insight development</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>'});
  await b.close();
})();
