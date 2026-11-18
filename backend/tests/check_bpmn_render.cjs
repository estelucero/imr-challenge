// Optional browser smoke test. Requires Playwright and the frontend bpmn-js bundle.
// Usage: node check_bpmn_render.cjs <bpmn-viewer.development.js> <diagram.bpmn>
const { chromium } = require('playwright');
const fs = require('fs');

async function main() {
  const [bundle, filename] = process.argv.slice(2);
  if (!bundle || !filename) throw new Error('Expected bpmn-js bundle and BPMN XML paths');
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent('<div id="canvas" style="width:1200px;height:800px"></div>');
    await page.addScriptTag({ path: bundle });
    const result = await page.evaluate(async xml => {
      const viewer = new window.BpmnJS({ container: '#canvas' });
      const { warnings } = await viewer.importXML(xml);
      return {
        warnings: warnings.map(warning => warning.message),
        hasSvg: !!document.querySelector('#canvas svg'),
        elementCount: viewer.get('elementRegistry').getAll().length,
      };
    }, fs.readFileSync(filename, 'utf8'));
    console.log(JSON.stringify(result));
    if (!result.hasSvg || result.warnings.length || !result.elementCount) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
