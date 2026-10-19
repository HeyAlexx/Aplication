const fs = require('node:fs');
const { chromium } = require('playwright');
const base = process.env.ALTOIDSS_TEST_URL || 'http://127.0.0.1:8092';
const catalogDir=require('./catalog-fixture-path.cjs');
const sizes = [[320,740],[360,800],[412,924],[600,960],[768,1024],[820,1180],[1024,768],[1512,1000],[1920,1080]];
const report = {base, timestamp:new Date().toISOString(), discoveryMode:'503 controlado: búsqueda de respaldo en JSON real, sin llamar proveedores externos', cases:[], imageWarnings:[], networkFailures:[], blockedWrites:[], errors:[]};
const expectedCounts = Object.fromEntries([['anime','anime.json'],['movies','peliculas.json'],['series','series.json']]
  .map(([type,file])=>[type,JSON.parse(fs.readFileSync(require('node:path').join(catalogDir,file),'utf8')).filter(item=>item.status!=='Oculto').length]));
report.expectedCounts = expectedCounts;
fs.mkdirSync('outputs/qa-responsive', {recursive:true});
const check = (row, name, passed, detail='') => row.checks.push({name, passed:!!passed, detail});
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    for (const [width,height] of sizes) {
      const context = await browser.newContext({viewport:{width,height}});
      const traced = [412,820,1920].includes(width);
      if(traced) await context.tracing.start({screenshots:true,snapshots:true,sources:true});
      const page = await context.newPage();
      page.setDefaultTimeout(12000);
      page.on('pageerror', e=>report.errors.push({width,message:e.message}));
      page.on('requestfailed', r=>{if(!/\.(jpg|png|webp|jpeg)(\?|$)/i.test(r.url())) report.networkFailures.push({width,url:r.url(),error:r.failure()?.errorText});});
      await page.route('**/api/index.php**', async route=>{
        const request=route.request();
        if(new URL(request.url()).searchParams.get('route')?.startsWith('/discover/')) return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({ok:false,error:{message:'Prueba de respaldo local'}})});
        if(request.method()==='GET') return route.continue();
        report.blockedWrites.push({width,method:request.method(),url:request.url()});
        return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,data:request.postDataJSON()})});
      });
      try {
        await page.goto(`${base}/Html/catalogo.html?category=anime`,{waitUntil:'domcontentloaded'});
        await page.waitForFunction(()=>document.querySelectorAll('#catalog-anime .anime-card[data-content-id]').length>0);
        for (const [category,count] of Object.entries(expectedCounts)) {
          if(category!=='anime') {
            if(width<=768) await page.locator('#catalogFilterToggle').click();
            await page.locator(`[data-category-view="${category}"]`).click();
            if(width<=768) await page.locator('#closeCatalogSideMenu').click();
          }
          await page.evaluate(()=>window.scrollTo(0,0));
          await page.waitForTimeout(150);
          const row={width,height,category,checks:[]}; report.cases.push(row);
          const state=await page.evaluate(category=>{
            const h=document.querySelector('.topbar').getBoundingClientRect();
            const title=document.querySelector('.section-heading h1').getBoundingClientRect();
            const cards=[...document.querySelectorAll(`.catalog-panel.is-active .anime-card`)].map(c=>{const b=c.getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height,title:c.catalogItem?.title};});
            return {headerBottom:h.bottom,titleTop:title.top,overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,cards,
              total:AltoidssStore.read().filter(i=>i.type===category).length,
              sidebarPosition:getComputedStyle(document.querySelector('#catalogSideMenu')).position,
              bootstrap:!!window.bootstrap,
              summary:document.querySelector('.catalog-panel.is-active .pagination-summary')?.textContent};
          },category);
          check(row,'Datos completos',state.total===count,`${state.total}/${count}`);
          check(row,'Sin desbordamiento horizontal',state.overflow<=1,`${state.overflow}px`);
          check(row,'Título no tapado por encabezado',state.titleTop>=state.headerBottom-1,`título ${state.titleTop}; encabezado ${state.headerBottom}`);
          check(row,'Cantidad inicial visible',state.cards.length===Math.min(35,count),state.cards.length);
          check(row,'Bootstrap disponible',state.bootstrap);
          if(width<=768) check(row,'Dos tarjetas por fila',state.cards[0]?.y===state.cards[1]?.y&&state.cards[2]?.y>state.cards[0]?.y);
          else check(row,'Sidebar fijo',state.sidebarPosition==='fixed');
          try {
            await page.waitForFunction(()=>[...document.querySelectorAll('.catalog-panel.is-active .poster img')]
              .filter(img=>{const r=img.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0;})
              .every(img=>img.complete&&img.naturalWidth>0),null,{timeout:10000});
          } catch {report.imageWarnings.push({width,category,message:'Portadas visibles no terminaron de cargar en 10 segundos.'});}
          await page.screenshot({path:`outputs/qa-responsive/${category}-${width}.png`});
          const pickOrder = async value => {
            if (width <= 768) {
              await page.locator('#catalogTouchOrderToggle').click();
              await page.locator(`[data-touch-order="${value}"]`).click();
            } else await page.locator('#catalogDateOrder').selectOption(value);
          };
          await pickOrder('oldest');
          check(row,'Orden antiguo se conserva en URL',new URL(page.url()).searchParams.get('order')==='oldest');
          await pickOrder('newest');
          if(width<=768) await page.locator('#catalogFilterToggle').click();
          const sample=state.cards[0].title;
          await page.locator('#sidebar-search').fill(sample);
          await page.locator('#sidebar-search').press('Enter');
          await page.waitForFunction(sample=>new URL(location.href).searchParams.get('query')===sample,sample);
          check(row,'Búsqueda con título real',await page.locator('.catalog-panel.is-active .anime-card').count()>0);
          await page.locator('#sidebar-search').fill('zzzz-sin-coincidencias-qa-2026');
          await page.locator('#sidebar-search').press('Enter');
          await page.waitForFunction(()=>new URL(location.href).searchParams.get('query')==='zzzz-sin-coincidencias-qa-2026');
          await page.waitForTimeout(100);
          check(row,'Búsqueda sin resultados',await page.locator('.catalog-panel.is-active .anime-card').count()===0);
          await page.locator('#clearCatalogFilters').click();
          await page.waitForFunction(()=>!new URL(location.href).searchParams.get('query'));
          check(row,'Limpiar recupera datos',await page.locator('.catalog-panel.is-active .anime-card').count()===Math.min(35,count));
          await page.locator('[data-catalog-view="list"]').click();
          check(row,'Seleccionar lista',await page.locator('[data-catalog-view="list"]').getAttribute('aria-pressed')==='true');
          await page.locator('[data-catalog-view="cards"]').click();
          check(row,'Seleccionar tarjetas',await page.locator('[data-catalog-view="cards"]').getAttribute('aria-pressed')==='true');
          if(width>768){
            for(const density of ['3','5','7']){
              await page.locator('#catalogDensity').selectOption(density);
              check(row,`Densidad ${density}`,await page.locator('.catalog-panel.is-active .catalog-grid').evaluate((e,d)=>e.dataset.density===d,density));
            }
            await page.locator('#catalogDensity').selectOption('5');
          } else await page.locator('#closeCatalogSideMenu').click();
        }
      } catch(e){report.errors.push({width,message:e.message});}
      if(traced) await context.tracing.stop({path:`outputs/qa-responsive/trace-${width}.zip`});
      await context.close();
      console.log(`Completado: ${width}x${height}`);
    }
  } finally {await browser.close();}
  report.checkCount=report.cases.reduce((n,c)=>n+c.checks.length,0);
  report.failedChecks=report.cases.flatMap(c=>c.checks.filter(x=>!x.passed).map(x=>({width:c.width,category:c.category,...x})));
  fs.writeFileSync('outputs/qa-responsive/report.json',JSON.stringify(report,null,2));
  console.log(JSON.stringify({cases:report.cases.length,checks:report.checkCount,failed:report.failedChecks,errors:report.errors,networkFailures:report.networkFailures.length}));
  if(report.failedChecks.length||report.errors.length) process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
