const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const html=fs.readFileSync('app/web/index.html','utf8');
const source=fs.readFileSync('app/web/app.js','utf8');
const flush=async()=>{for(let i=0;i<12;i++)await new Promise(r=>setImmediate(r));};

function setup(){
 const dom=new JSDOM(html,{url:'http://localhost:8000',runScripts:'outside-only'}),w=dom.window,calls=[];
 w.setInterval=()=>0;w.HTMLElement.prototype.scrollIntoView=function(){};
 const snapshot={forecast:{balance:'1000.00',monthly_cash_flow:'200',runway_days:null,history_months:0,limited_history:true,projections:{30:'1200',60:'1400',90:'1600'},recommendations:[],assumptions:'Scheduled commitments are included.'},pyramid:{totals:{base:'100',middle:'60',peak:'40'},actual_percent:{base:'10',middle:'6',peak:'4'},target_percent:{base:50,middle:30,peak:20},deformity_score:120,inverted:false,recommendations:[]},inflation:{quarters:[],reference_month:null,requires_cpi:false},subscriptions:[],subscription_recommendations:[],fraud_alerts:[],notifications:[],shocks:[],offers:[],integration_status:{banking:'requires_configuration'}};
 const state={accounts:[],transactions:[],flows:[],budgets:[],vacations:[],chargebacks:[],privacy:{ai_consent:false,browsing_consent:false,geolocation_consent:false,radius_km:'50',latitude:null,longitude:null},summaries:[]};
 w.fetch=async(url,options={})=>{const path=url.replace('/api/v1/',''),body=options.body?JSON.parse(options.body):null;calls.push({path,method:options.method,body,headers:options.headers});let value;
  if(path.startsWith('auth/'))value={access_token:'test-token',email:'test@example.com'};
  else if(path==='finance/dashboard')value=snapshot;
  else if(path==='finance/banking/sync')return {ok:false,status:502,json:async()=>({error:{message:'Bank connection requires configuration.'}})};
  else if(path.startsWith('finance/offers/'))value={status:body.decision};
  else if(path==='finance/summaries'&&options.method==='POST'){value={id:'s1',text:'Verified financial summary',created_at:'2026-11-07'};state.summaries.push(value);}
  else if(path.includes('/audio'))return {ok:false,status:502,json:async()=>({error:{message:'Audio requires ELEVENLABS_API_KEY.'}})};
  else {const key=path.split('/')[1];if(options.method==='POST'){value={id:'new-'+key,...body};state[key].push(value);}else if(options.method==='PUT'){state[key]=body;value=body;}else value=state[key];}
  return {ok:true,status:200,json:async()=>value};};
 w.eval(source);
 return {dom,w,calls,state,snapshot,close:()=>w.close()};
}
async function login(ctx){const f=ctx.w.document.getElementById('login');f.elements.email.value='test@example.com';f.elements.password.value='test-password';f.dispatchEvent(new ctx.w.Event('submit',{bubbles:true,cancelable:true}));await flush();}
const findButton=(w,text)=>[...w.document.querySelectorAll('button')].find(b=>b.textContent===text);

test('login renders live dashboard and logout hides private workspace',async()=>{const c=setup();try{await login(c);assert.equal(c.w.document.getElementById('workspace').hidden,false);assert.match(c.w.document.getElementById('metrics').textContent,/1,000/);assert.ok(c.w.document.querySelector('#forecast svg'));assert.match(c.w.document.getElementById('status').textContent,/up to date/);c.w.document.getElementById('logout').click();assert.equal(c.w.document.getElementById('workspace').hidden,true);assert.equal(c.w.sessionStorage.length,0);}finally{c.close();}});

test('account form sends the entered snapshot with authorization and updates table',async()=>{const c=setup();try{await login(c);const f=c.w.document.querySelector('#account-form form');f.elements.institution_name.value='My Bank';f.elements.masked_account_number.value='****1234';f.elements.current_balance.value='1200';f.elements.available_balance.value='1100';f.dispatchEvent(new c.w.Event('submit',{cancelable:true}));await flush();const sent=c.calls.find(r=>r.path==='finance/accounts'&&r.method==='POST');assert.equal(sent.body.available_balance,'1100');assert.equal(sent.headers.Authorization,'Bearer test-token');assert.match(c.w.document.getElementById('accounts').textContent,/My Bank/);}finally{c.close();}});

test('privacy starts unchecked and saves explicit choices',async()=>{const c=setup();try{await login(c);const f=c.w.document.querySelector('#privacy-form form');assert.equal(f.elements.ai_consent.checked,false);f.elements.browsing_consent.checked=true;f.dispatchEvent(new c.w.Event('submit',{cancelable:true}));await flush();const sent=c.calls.find(r=>r.path==='finance/privacy'&&r.method==='PUT');assert.equal(sent.body.browsing_consent,true);assert.equal(sent.body.geolocation_consent,false);assert.equal(sent.body.latitude,null);}finally{c.close();}});

test('offer acceptance transmits the actual confirmation checkbox',async()=>{const c=setup();try{c.snapshot.offers=[{id:'o1',months:3,status:'proposed',expires_on:'2026-12-01',terms:{principal:300,fee:5,annual_rate_percent:12,payment:104,total_interest:7,total_repayment:312,affordable:true}}];await login(c);findButton(c.w,'Accept plan').click();await flush();let sent=c.calls.filter(r=>r.path==='finance/offers/o1/decision').at(-1);assert.equal(sent.body.confirm_obligation,false);c.w.document.querySelector('#offers input[type=checkbox]').checked=true;findButton(c.w,'Accept plan').click();await flush();sent=c.calls.filter(r=>r.path==='finance/offers/o1/decision').at(-1);assert.equal(sent.body.confirm_obligation,true);}finally{c.close();}});

test('provider failures are visible and controls recover',async()=>{const c=setup();try{await login(c);const b=c.w.document.getElementById('bank-sync');b.click();await flush();assert.match(c.w.document.getElementById('status').textContent,/requires configuration/);assert.equal(b.disabled,false);}finally{c.close();}});

test('merchant text is rendered as text and cannot inject HTML',async()=>{const c=setup();try{c.state.transactions=[{occurred_at:'2026-11-07',merchant:'<img src=x onerror=alert(1)>',category:'entertainment',amount:-10,fraud:{score:'.5'},latitude:null,longitude:null}];await login(c);assert.equal(c.w.document.querySelector('#transactions img'),null);assert.match(c.w.document.getElementById('transactions').textContent,/<img/);}finally{c.close();}});

test('vacation summary draws locations and includes merchant detail',async()=>{const c=setup();try{c.state.vacations=[{id:'v1',destination:'Test destination',start_date:'2026-11-01',end_date:'2026-11-10',enabled:true,total_spent:'20',remaining_budget:'80',transactions:[{merchant:'Cafe',category:'dining',amount:-20,latitude:48.85,longitude:2.35}]}];await login(c);assert.ok(c.w.document.querySelector('#vacations circle'));assert.match(c.w.document.getElementById('vacations').textContent,/Cafe/);assert.match(c.w.document.getElementById('vacations').textContent,/80/);}finally{c.close();}});

test('summary submission renders text and voice error does not pretend to play',async()=>{const c=setup();try{await login(c);const f=c.w.document.getElementById('summary-form');f.dispatchEvent(new c.w.Event('submit',{cancelable:true}));await flush();assert.match(c.w.document.getElementById('summaries').textContent,/Verified financial summary/);findButton(c.w,'Listen · professional').click();await flush();assert.match(c.w.document.getElementById('status').textContent,/ELEVENLABS_API_KEY/);assert.equal(c.w.document.querySelector('#summaries audio'),null);}finally{c.close();}});
