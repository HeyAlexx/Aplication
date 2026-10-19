const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const {spawn} = require('node:child_process');
const {request} = require('playwright');
const root = path.resolve(__dirname,'..');
const catalogDir=require('./catalog-fixture-path.cjs');
const fixture = path.join(root,'runtime','qa-fixtures',`http-${Date.now()}`);
const report = {timestamp:new Date().toISOString(),isolated:true,checks:[]};
const write = (name,value)=>fs.writeFileSync(path.join(fixture,'data',name),JSON.stringify(value));
(async()=>{
  fs.mkdirSync(path.join(fixture,'data'),{recursive:true});
  fs.cpSync(path.join(root,'api'),path.join(fixture,'api'),{recursive:true,
    filter:source=>!source.endsWith('secrets.local.php')&&!source.endsWith('mal-client-id.local.txt')});
  fs.copyFileSync(path.join(root,'server-router.php'),path.join(fixture,'server-router.php'));
  for(const file of ['anime.json','peliculas.json','series.json','noticias.json']) {
    fs.copyFileSync(path.join(catalogDir,file),path.join(fixture,'data',file));
  }
  for(const file of ['usuarios.json','perfiles.json','configuraciones.json','favoritos.json','historial.json','anime-sheet-writeback.json','anime-revisiones.json']) write(file,[]);
  const linked = JSON.parse(fs.readFileSync(path.join(fixture,'data','anime.json'),'utf8')).find(item=>item.sourceCode&&item.sourceRow>=2);
  assert.ok(linked,'La copia debe contener un anime vinculado real.');
  const listener = net.createServer();
  await new Promise(resolve=>listener.listen(0,'127.0.0.1',resolve));
  const port=listener.address().port;
  await new Promise(resolve=>listener.close(resolve));
  const fixtureEnv={...process.env}; delete fixtureEnv.ALTOIDSS_STORAGE_CONFIG;
  const server = spawn(process.env.PHP_BIN||'C:\\xampp\\php\\php.exe',['-S',`127.0.0.1:${port}`,'-t','.', 'server-router.php'],{cwd:fixture,env:fixtureEnv,windowsHide:true,stdio:'ignore'});
  let context;
  try {
    context=await request.newContext({baseURL:`http://127.0.0.1:${port}`});
    let csrf='';
    const api=async(method,route,data,status=200,token=csrf)=>{
      const response=await context.fetch(`/api/index.php?route=${encodeURIComponent(route)}`,{method,data,headers:{'X-CSRF-Token':token}});
      assert.equal(response.status(),status,`${method} ${route}`);
      const body=await response.json(); csrf=body.meta?.csrfToken||csrf;
      report.checks.push({name:`${method} ${route}`,status,passed:true}); return body.data;
    };
    let ready=false;
    for(let i=0;i<40;i++) {
      try {await api('GET','/health');ready=true;break;} catch {await new Promise(r=>setTimeout(r,100));}
    }
    assert.ok(ready,'Servidor aislado disponible');
    await api('POST',`/favorites/${linked.id}`,{},401);
    await api('PUT',`/content/${linked.id}`,{},419,'invalid');
    const password=require('node:crypto').randomBytes(18).toString('hex');
    const login={email:'qa@example.invalid',password};
    await api('POST','/auth/register',{...login,name:'QA',role:'admin'},201);
    await api('GET','/reviews/anime',undefined,403);
    await api('PUT',`/content/${linked.id}`,{},403);
    await api('POST',`/favorites/${linked.id}`,{});
    await api('POST',`/favorites/${linked.id}`,{});
    assert.equal((await api('GET','/favorites')).length,1);
    for(const state of ['planned','watching','paused','completed','dropped']) {
      await api('PUT',`/viewing/${linked.id}`,{state});
      assert.equal((await api('GET','/profile')).viewingStates[linked.id],state);
    }
    await api('PUT',`/viewing/${linked.id}`,{state:'invalid'},400);
    await api('POST','/auth/logout',{});
    await api('POST','/auth/login',login);
    assert.equal((await api('GET','/favorites')).length,1);
    // Promoción exclusivamente en la fixture, nunca en la instalación real.
    const users=JSON.parse(fs.readFileSync(path.join(fixture,'data','usuarios.json'),'utf8'));
    users[0].role='admin';write('usuarios.json',users);
    await api('POST','/auth/logout',{});await api('POST','/auth/login',login);
    const updated=await api('PUT',`/content/${linked.id}`,{chapters:Number(linked.chapters||0)+1});
    assert.equal(updated.sheetSyncStatus,'Pendiente');
    const queue=()=>JSON.parse(fs.readFileSync(path.join(fixture,'data','anime-sheet-writeback.json'),'utf8'));
    assert.equal(queue().length,1);
    const local=await api('POST','/content',{title:'QA local',type:'anime',genre:'Anime',emissionYear:2026,emissionSeason:'Fall',seasonsCount:1,sourceCode:'fake',sourceRow:900},201);
    assert.ok(!local.sourceCode&&!local.sourceRow); assert.equal(queue().length,1);
    await api('DELETE',`/content/${local.id}`,{});
    await api('GET',`/content/${local.id}`,undefined,404);
    for(const blocked of ['/data/usuarios.json','/data/anime-sheet-writeback.json','/api/config/app.php','/config/sheets.json','/.git/config','/backups/sessions/','/runtime/private','/tools/private','/outputs/providers-live-report.json']) {
      assert.equal((await context.get(blocked)).status(),404,blocked);
      report.checks.push({name:`Privado: ${blocked}`,passed:true});
    }
    report.passed=true;
  } finally {if(context)await context.dispose();server.kill();}
})().catch(error=>{report.passed=false;report.error=error.message;process.exitCode=1;}).finally(()=>{
  fs.mkdirSync(path.join(root,'outputs'),{recursive:true});
  fs.writeFileSync(path.join(root,'outputs','api-workflow-report.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
});
