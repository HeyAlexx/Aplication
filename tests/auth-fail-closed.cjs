const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
(async()=>{
 const storage=new Map([
  ['altoidss_auth_users',JSON.stringify([{email:'fixture@example.invalid',password:'fixture-only-clear-password',role:'admin'}])],
  ['altoidss_auth_session',JSON.stringify({id:'legacy-preview',role:'admin',isAuthenticated:true})],
  ['altoidss_user_profiles','{"preserve":"fixture-profile"}']
 ]);
 const calls=[];
 const api={get:async()=>{throw new Error('Fixture offline');},post:async(route,body)=>{
  calls.push(route);throw new Error('Fixture offline');},isAvailable:()=>false};
 const window={dispatchEvent:()=>{}};
 const context=vm.createContext({window,AltoidssApi:api,
  localStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},
  CustomEvent:class{},console});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../js/auth.js'),'utf8'),context);
 const auth=window.AltoidssAuth;
 await auth.initialize();
 assert.equal(auth.getSession().isAuthenticated,false);
 assert.equal(auth.getSession().role,'visitante');
 assert.equal((await auth.login('fixture@example.invalid','fixture-only-clear-password')).ok,false);
 assert.equal((await auth.register({name:'Fixture',email:'new@example.invalid',password:'Only-for-the-offline-fixture'})).ok,false);
 assert.equal(storage.has('altoidss_auth_users'),false);
 assert.equal(storage.has('altoidss_auth_session'),false);
 assert.equal(storage.get('altoidss_user_profiles'),'{"preserve":"fixture-profile"}');
 assert.deepEqual(calls,['/auth/login','/auth/register']);
 console.log('OK: servidor ausente no concede una sesión local ni persiste contraseñas; perfiles preservados.');
})().catch(error=>{console.error(error);process.exitCode=1;});

