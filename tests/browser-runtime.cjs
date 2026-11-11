// Project-local locked dependencies. No dependency on a Codex profile or global NODE_PATH.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const dependencies = process.env.ALTOIDSS_QA_NODE_MODULES || path.join(__dirname, '..', 'qa', 'node_modules');
const playwright = require(path.join(dependencies, 'playwright'));
const bootstrap = path.join(dependencies, 'bootstrap', 'dist');
const assets = new Map([
  ['/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css', {file:path.join(bootstrap,'css/bootstrap.min.css'),type:'text/css'}],
  ['/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js', {file:path.join(bootstrap,'js/bootstrap.bundle.min.js'),type:'text/javascript'}]
]);

async function offline(context, origin) {
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.origin === origin) return route.continue();
    const asset = url.hostname === 'cdn.jsdelivr.net' && assets.get(url.pathname);
    if (asset) return route.fulfill({status:200,contentType:asset.type,body:fs.readFileSync(asset.file)});
    return route.abort();
  });
}

const chromium = {
  async launch(options = {}) {
    const base = new URL(process.env.ALTOIDSS_TEST_URL || 'http://127.0.0.1:8092');
    if (base.protocol !== 'http:' || !['127.0.0.1','localhost','[::1]'].includes(base.hostname)) {
      throw Error('Browser QA requires an isolated local HTTP fixture.');
    }
    const browser = await playwright.chromium.launch({...options,
      channel:process.env.ALTOIDSS_BROWSER_CHANNEL || undefined,headless:true});
    const originalContext = browser.newContext.bind(browser);
    const originalPage = browser.newPage.bind(browser);
    browser.newContext = async options => {
      const context = await originalContext(options);
      await offline(context, base.origin);
      return context;
    };
    browser.newPage = async options => {
      const page = await originalPage(options);
      await offline(page.context(), base.origin);
      return page;
    };
    return browser;
  }
};

function verifyBootstrapSri(app) {
  for (const {file} of assets.values()) {
    const sri = 'sha384-' + crypto.createHash('sha384').update(fs.readFileSync(file)).digest('base64');
    if (!fs.readFileSync(path.join(app,'Html/index.html'),'utf8').includes(sri)) {
      throw Error('Locked Bootstrap content does not match the application SRI.');
    }
  }
  return true;
}

module.exports = {chromium,request:playwright.request,verifyBootstrapSri};
