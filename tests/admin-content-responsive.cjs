const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const base=process.env.ALTOIDSS_TEST_URL||'http://127.0.0.1:8092';
const catalogDir=require('./catalog-fixture-path.cjs');
const load=file=>JSON.parse(fs.readFileSync(path.join(catalogDir,file),'utf8')).filter(item=>item.status!=='Oculto');
const content=[...load('anime.json'),...load('peliculas.json'),...load('series.json')];
const template={type:'anime',genre:'Anime',emissionYear:2026,emissionSeason:'Fall',seasonsCount:1,chapters:12,format:'Serie',productionStatus:'Finalizado',status:'Activo'};
content.push({...template,id:'qa-dated',title:'QA fecha corta',createdAt:'2026-10-08T12:00:00Z'},
  {...template,id:'qa-unknown',title:'QA sin referencia'},
  {...template,id:'qa-long',title:'QA-'+ 'TituloLargoSinEspacios'.repeat(12)});
const news=load('noticias.json');
const session={id:'qa-admin',name:'QA',role:'admin',profileMode:'admin',isAuthenticated:true,email:'qa@example.invalid'};
const profile={...session,displayName:'QA',seenIds:[],viewingStates:{},favoriteIds:[],favoriteItems:{},settings:{cardsPerRow:5,preferredView:'cards'}};
const summary={profile,totalContent:content.length,seenTotal:0,favoriteTotal:0,moviesSeen:0,seriesSeen:0,animeSeen:0,topGenre:'Sin datos',lastVisit:'Hoy',watchTimeMinutes:0};
const report={timestamp:new Date().toISOString(),base,mockedAdmin:true,realCatalogCount:content.length-3,cases:[],errors:[],mutations:[]};
const output=path.join(root,'outputs','qa-admin');fs.mkdirSync(output,{recursive:true});
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try {
    for(const width of [320,360,412,480,600,768,820,1024,1920]) {
      const context=await browser.newContext({viewport:{width,height:1000},isMobile:width<=768,hasTouch:width<=768});
      const page=await context.newPage();
      page.on('pageerror',error=>{report.errors.push({width,message:error.message});console.error(error.message);});
      page.on('requestfailed',request=>console.error('Recurso no disponible:',request.url(),request.failure()?.errorText));
      await page.route('**/api/index.php**',async route=>{
        const request=route.request(),endpoint=new URL(request.url()).searchParams.get('route');
        if(request.method()!=='GET') {report.mutations.push(endpoint);return route.fulfill({status:403,contentType:'application/json',body:'{"ok":false}'});}
        const routes={'/health':{status:'ok'},'/auth/session':session,'/profile':profile,'/dashboard':summary,
          '/content/anime':content.filter(i=>i.type==='anime'),'/content/movies':content.filter(i=>i.type==='movies'),
          '/content/series':content.filter(i=>i.type==='series'),'/news':news,'/reviews/anime':[]};
        if(!(endpoint in routes))throw Error(`GET inesperado: ${endpoint}`);
        await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,data:routes[endpoint],meta:{}})});
      });
      try {
        await page.goto(`${base}/Html/dashboard.html?tab=table`,{waitUntil:'networkidle'});
        await page.waitForSelector('body.is-admin-profile',{timeout:10000});
        await page.waitForFunction(count=>document.querySelectorAll('#contentTableBody tr').length===count,content.length);
        await page.waitForTimeout(500);
        for(const mode of ['content','news']) {
          if(mode==='news')await page.locator('[data-table-mode="news"]').click();
          const row=page.locator('#contentTableBody tr').first();await row.scrollIntoViewIfNeeded();
          const layout=await row.evaluate(tr=>{
            const table=tr.closest('.admin-table'),r=table.getBoundingClientRect();
            const buttons=[...tr.querySelectorAll('button')].map(b=>({rect:b.getBoundingClientRect().toJSON(),display:getComputedStyle(b).display}));
            return {viewport:innerWidth,overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
              table:{width:r.width,scroll:table.scrollWidth-table.clientWidth},cells:tr.querySelectorAll('td').length,
              rowDisplay:getComputedStyle(tr).display,buttons};
          });
          assert.ok(layout.overflow<=1,`Página desbordada a ${width}: ${layout.overflow}`);
          assert.equal(layout.cells,6);
          assert.equal(layout.buttons.length,2);
          if(width<=768) {
            assert.equal(layout.rowDisplay,'grid');assert.ok(layout.table.scroll<=1);
            for(const button of layout.buttons){assert.ok(button.rect.height>=48);assert.ok(button.rect.left>=-1&&button.rect.right<=width+1);}
            assert.ok(Math.abs(layout.buttons[1].rect.top-layout.buttons[0].rect.top)<=1,'Acciones lado a lado');
            assert.ok(layout.buttons[1].rect.left>=layout.buttons[0].rect.right,'Acciones sin superposición');
            const card=await row.evaluate(tr=>{
              const cells=[...tr.cells].map(td=>({rect:td.getBoundingClientRect().toJSON(),area:getComputedStyle(td).gridArea}));
              const title=tr.querySelector('.admin-record-title'),date=tr.querySelector('.admin-mobile-date');
              const yearRange=document.createRange();yearRange.selectNodeContents(tr.cells[2]);
              return {cells,tracks:getComputedStyle(tr).gridTemplateColumns.split(' ').map(parseFloat),category:!!tr.querySelector('.admin-category-badge'),titleSize:parseFloat(getComputedStyle(title).fontSize),title:title.getBoundingClientRect().toJSON(),yearText:yearRange.getBoundingClientRect().toJSON(),date:date.getBoundingClientRect().toJSON()};
            });
            assert.ok(card.category,'Categoría visible como insignia');
            const expectedTitleSize=Math.min(Math.max(18,width*.05),28)*.7;
            assert.ok(Math.abs(card.titleSize-expectedTitleSize)<.05,'Título reducido exactamente un 30 %');
            assert.ok(Math.abs(card.tracks[0]-card.tracks[1]*3)<1&&Math.abs(card.tracks[1]-card.tracks[2])<1,'Grid 3–1–1');
            const yearCell=card.cells[2].rect;
            assert.ok(Math.abs((card.yearText.left+card.yearText.right)-(yearCell.left+yearCell.right))<2,'Año centrado horizontalmente');
            assert.ok(Math.abs((card.yearText.top+card.yearText.bottom)-(yearCell.top+yearCell.bottom))<2,'Año centrado verticalmente');
            assert.ok(yearCell.left>=card.cells[0].rect.right&&yearCell.right<=card.cells[4].rect.left,'Año en columna independiente entre información e insignias');
            assert.ok(card.date.top>=card.title.bottom-1,'Fecha debajo del título');
            assert.ok(Math.abs(card.date.left-card.title.left)<=1,'Fecha alineada al inicio');
            assert.ok(card.cells[4].rect.left>card.cells[0].rect.left,'Estado a la derecha');
            assert.ok(card.cells[3].rect.left>card.cells[0].rect.left,'Categoría a la derecha');
            assert.ok(card.cells[5].rect.top>=Math.max(...[0,2,3,4].map(index=>card.cells[index].rect.bottom))-1,'Franja de acciones debajo del contenido');
            for(const button of await row.locator('button').all()) {
              const green='rgba(111, 148, 135, 0.4)';
              await button.hover();await page.waitForTimeout(200);
              assert.equal(await button.evaluate(b=>getComputedStyle(b).backgroundColor),green,'Hover verde al 40 %');
              await button.focus();await page.mouse.move(0,0);await page.waitForTimeout(200);
              assert.equal(await button.evaluate(b=>getComputedStyle(b).backgroundColor),green,'Foco verde al 40 %');
              await button.evaluate(b=>{b.blur();b.classList.add('active');});await page.waitForTimeout(200);
              assert.equal(await button.evaluate(b=>getComputedStyle(b).backgroundColor),green,'Estado activo verde al 40 %');
              await button.evaluate(b=>b.classList.remove('active'));
              await button.hover();await page.mouse.down();await page.waitForTimeout(200);
              assert.equal(await button.evaluate(b=>getComputedStyle(b).backgroundColor),green,'Pulsación verde al 40 %');
              assert.equal(await button.evaluate(b=>getComputedStyle(b).opacity),'1','Texto y borde sin transparencia');
              await page.mouse.move(0,0);await page.mouse.up();
              await button.evaluate(b=>b.blur());
            }
          } else {
            assert.equal(layout.rowDisplay,'table-row');
            assert.ok(layout.table.scroll<=1,'Tabla de escritorio sin columnas fuera de vista');
            for(const button of layout.buttons)assert.ok(button.rect.left>=-1&&button.rect.right<=width+1,'Acciones de escritorio accesibles');
          }
          await page.screenshot({path:path.join(output,`${mode}-${width}.png`)});
          if(mode==='content'&&width===412) {
            const mechanic=page.locator('#contentTableBody tr').filter({hasText:'Mechanic: Resurrection'}).first();
            await mechanic.screenshot({path:path.join(output,'mechanic-412.png')});
            const edit=mechanic.locator('[data-edit-id]');
            await edit.hover();await page.mouse.down();await page.waitForTimeout(200);
            await mechanic.screenshot({path:path.join(output,'mechanic-pressed-412.png')});
            await page.mouse.move(0,0);await page.mouse.up();await edit.evaluate(b=>b.blur());
          }
          report.cases.push({width,mode,passed:true,layout});
        }
        await page.locator('[data-table-mode="content"]').click();
        const dated=page.locator('[data-edit-id="qa-dated"]').locator('xpath=ancestor::tr');
        assert.match(await dated.locator('td[data-label="Agregado"] .incorporation-date').innerText(),/^\d{2}\/\d{2}\/\d{2}$/);
        assert.ok((await dated.locator('td[data-label="Agregado"] .incorporation-date').getAttribute('title')).length>10);
        const unknown=page.locator('[data-edit-id="qa-unknown"]').locator('xpath=ancestor::tr');
        assert.equal(await unknown.locator('td[data-label="Agregado"] .incorporation-date').innerText(),'N/A');
        const historical=content.find(i=>i.sourceRow>=2&&!i.incorporatedAt&&!i.createdAt&&!i.importedAt);
        assert.ok(historical);
        assert.equal(await page.locator(`[data-edit-id="${historical.id}"]`).locator('xpath=ancestor::tr').locator('td[data-label="Agregado"] .incorporation-date').innerText(),`Fila ${historical.sourceRow}`);
        const initialized=content.find(i=>String(i.incorporationDateBasis||'').startsWith('historical-'));
        if(initialized) {
          const date=page.locator(`[data-edit-id="${initialized.id}"]`).locator('xpath=ancestor::tr').locator('td[data-label="Agregado"] .incorporation-date');
          assert.match(await date.innerText(),/^≈ \d{2}\/\d{2}\/\d{2}$/);
          assert.ok((await date.getAttribute('title')).includes('No es una fecha de alta real'));
        }
        if(width<=768) {
          const long=page.locator('[data-edit-id="qa-long"]').locator('xpath=ancestor::tr');
          assert.ok(await long.evaluate(tr=>tr.scrollWidth<=tr.clientWidth+1),'Título largo no desborda');
        }
        await page.locator('[data-edit-id="qa-dated"]').click();
        assert.equal(await page.locator('#contentTitle').inputValue(),'QA fecha corta');
        assert.ok(await page.locator('#saveContentButton').isVisible());
        await page.locator('#cancelEditButton').click();
        await page.locator('[data-dashboard-tab="table"]').click();
        let dialogSeen=false;page.once('dialog',async dialog=>{dialogSeen=true;await dialog.dismiss();});
        await page.locator('[data-delete-id="qa-dated"]').click();assert.ok(dialogSeen);
        assert.equal(await page.locator('[data-edit-id="qa-dated"]').count(),1);
        await page.locator('[data-table-mode="news"]').click();
        await page.locator('[data-edit-news-id]').first().click();
        assert.ok(await page.locator('#newsTitle').isVisible());
        await page.locator('#cancelNewsEditButton').click();
        await page.locator('[data-dashboard-tab="table"]').click();
        await page.evaluate(()=>renderContentTable([]));
        assert.equal(await page.locator('#contentTableBody td').getAttribute('colspan'),'6');
      } catch(error){report.errors.push({width,message:error.message});console.error(`Fallo ${width}px: ${error.message}`);await page.screenshot({path:path.join(output,`failure-${width}.png`)});}
      await context.close();
      console.log(`Admin: ${width}px completado`);
    }
  } finally {await browser.close();}
  assert.deepEqual(report.mutations,[],'Las pruebas no deben escribir en datos reales.');
  report.passed=report.errors.length===0&&report.cases.length===18;
  fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({cases:report.cases.length,errors:report.errors,mutations:report.mutations}));
  if(!report.passed)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
