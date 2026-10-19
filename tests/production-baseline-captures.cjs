// Captura una copia respaldada de producción, nunca arranca la instalación real.
const fs=require('node:fs'), path=require('node:path'), net=require('node:net');
const {spawn}=require('node:child_process');
const {chromium}=require('playwright');
(async()=>{
  const snapshot=path.resolve(process.argv[2]||'');
  if(!snapshot.includes('preproduction-snapshots')||!fs.existsSync(path.join(snapshot,'production','server-router.php'))) throw Error('Indique un snapshot válido.');
  const root=path.join(snapshot,'production');
  const out=path.resolve('outputs/qa-production-baseline'); fs.mkdirSync(out,{recursive:true});
  const listener=net.createServer();await new Promise(r=>listener.listen(0,'127.0.0.1',r));
  const port=listener.address().port;await new Promise(r=>listener.close(r));
  const server=spawn('C:\\xampp\\php\\php.exe',['-S',`127.0.0.1:${port}`,'-t','.', 'server-router.php'],{cwd:root,windowsHide:true,stdio:'ignore'});
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const report={timestamp:new Date().toISOString(),source:'Copia local respaldada de producción; no sitio desplegado',snapshot,captures:[]};
  try {
    for(const [width,height] of [[412,924],[820,1180],[1920,1080]]) {
      const page=await browser.newPage({viewport:{width,height}});
      await page.route('**/api/index.php**',route=>route.request().method()==='GET'?route.continue():route.fulfill({status:403,body:'{"ok":false}'}));
      await page.goto(`http://127.0.0.1:${port}/Html/catalogo.html?category=anime`,{waitUntil:'networkidle'});
      await page.waitForTimeout(1000);
      const file=path.join(out,`anime-${width}.png`);await page.screenshot({path:file});
      report.captures.push({width,height,file}); await page.close();
    }
    fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));
    console.log('OK: tres capturas de la copia de producción, sin iniciar la instalación real.');
  } finally {await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
