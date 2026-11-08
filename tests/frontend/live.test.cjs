/* Real frontend JS + real FastAPI + isolated SQLite, without a browser renderer. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const net=require('node:net');
const {spawn,spawnSync}=require('node:child_process');
const {JSDOM}=require('jsdom');

test('frontend forms connect to FastAPI and persist real account, transaction and consent records',{timeout:45000},async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'fre-ui-test-'));
 const port=await new Promise(resolve=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
 const python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
 const serverEnv={...process.env,DATABASE_URL:'sqlite+aiosqlite:///'+path.join(directory,'ui.db').replaceAll('\\','/'),DEBUG:'false',ENABLE_BACKGROUND_JOBS:'false',ENABLE_REGISTRATION:'false'};
 const server=spawn(python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port',String(port)],{env:serverEnv,stdio:'ignore',windowsHide:true});
 let dom;
 const base='http://127.0.0.1:'+port;
 async function until(predicate){const deadline=Date.now()+15000;while(Date.now()<deadline){if(await predicate())return;if(dom?.window.document.querySelector('#status .error'))throw Error(dom.window.document.getElementById('status').textContent);await new Promise(r=>setTimeout(r,100));}throw Error('Timed out waiting for the live application');}
 try{
  await until(async()=>{try{return (await fetch(base+'/health')).ok;}catch{return false;}});
  dom=new JSDOM(fs.readFileSync('app/web/index.html','utf8'),{url:base,runScripts:'outside-only'});
  const w=dom.window;w.setInterval=()=>0;w.fetch=(url,options)=>fetch(base+url,options);w.HTMLElement.prototype.scrollIntoView=function(){};
  w.eval(fs.readFileSync('app/web/app.js','utf8'));
  const submit=f=>f.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
  assert.equal(w.document.getElementById('register'),null);
  const provision=spawnSync(python,['-m','scripts.create_admin','--email','ui-test@example.com'],{env:serverEnv,input:'TestOnlyPassword123!\n',encoding:'utf8',windowsHide:true});
  assert.equal(provision.status,0,provision.stderr);
  const login=w.document.getElementById('login');
  login.elements.email.value='ui-test@example.com';login.elements.password.value='TestOnlyPassword123!';
  submit(login);await until(()=>w.document.getElementById('status').textContent.includes('up to date'));
  assert.equal(w.document.getElementById('workspace').hidden,false);
  let form=w.document.querySelector('#account-form form');
  Object.entries({institution_name:'UI test snapshot',masked_account_number:'****5678',current_balance:'2500',available_balance:'2400'}).forEach(([k,v])=>form.elements[k].value=v);
  submit(form);await until(()=>w.document.getElementById('accounts').textContent.includes('UI test snapshot'));
  assert.match(w.document.getElementById('metrics').textContent,/2,400/);
  form=w.document.querySelector('#transaction-form form');
  Object.entries({external_id:'ui-tx-1',occurred_at:new Date(Date.now()-86400000).toISOString().slice(0,16),amount:'-25',merchant:'UI cafe',category:'entertainment'}).forEach(([k,v])=>form.elements[k].value=v);
  submit(form);await until(()=>w.document.getElementById('transactions').textContent.includes('ui cafe'));
  assert.match(w.document.getElementById('transactions').textContent,/0.500000/);
  form=w.document.querySelector('#privacy-form form');form.elements.ai_consent.checked=true;submit(form);
  await until(()=>w.document.querySelector('#privacy-form form')!==form);
  assert.equal(w.document.querySelector('#privacy-form input[name=ai_consent]').checked,true);
  w.document.getElementById('logout').click();assert.equal(w.document.getElementById('workspace').hidden,false);assert.equal(w.document.body.classList.contains('public-view'),true);
 }finally{if(dom)dom.window.close();server.kill();}
});
