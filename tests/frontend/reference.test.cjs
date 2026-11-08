const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const fixture=JSON.parse(fs.readFileSync('tests/fixtures/reference_20111.json','utf8'));
const flush=async()=>{for(let i=0;i<15;i++)await new Promise(resolve=>setImmediate(resolve));};
function setup(){
 const dom=new JSDOM(fs.readFileSync('app/web/index.html','utf8'),{url:'http://localhost',runScripts:'outside-only'}),w=dom.window,calls=[],state={briefing:structuredClone(fixture.briefing),pending:{},fail:null};
 w.URL.createObjectURL=()=> 'blob:generated-fixture';w.URL.revokeObjectURL=()=>{};
 w.HTMLMediaElement.prototype.pause=function(){this.wasPaused=true;};w.setInterval=()=>0;w.HTMLElement.prototype.scrollIntoView=function(){};
 w.fetch=async(url,options={})=>{
  const path=url.replace('/api/v1/','');const body=options.body?JSON.parse(options.body):null;calls.push({path,body});
  if(state.pending[path])await state.pending[path];if(state.fail&&path.endsWith(state.fail))return {ok:false,status:502,json:async()=>({error:{message:'External provider unavailable'}})};let result=structuredClone(fixture);result.account_id=Number(path.split('/')[1]);if(body?.scenario_id){const params={LAID_OFF_EI:[45,0,0,6],FURNACE_REPAIR:[0,0,fixture.metrics.typical_spending_S,1],LAID_OFF_AND_BILLS_UP:[45,15,0,6],INFLATION_STAGNATION:[10,25,0,12],CUSTOM:[body.income_reduction_pct*100,body.bills_increase_pct*100,body.one_off_costs,body.shock_duration_months]}[body.scenario_id];result.shock.scenario_id=body.scenario_id;if(params)result.shock.shock_parameters=Object.fromEntries(['income_reduction_pct','bills_increase_pct','one_off_costs','shock_duration_months'].map((k,i)=>[k,params[i]]));}
  if(state.omitAvailability)delete result.availability;if(state.legacyResponse)delete result.pyramid.actual_percent;
  if(path.endsWith('/fraud'))result={anomaly_score:.95,flag_threshold:.85,is_flagged:true,metrics:{z_score:4},vacation_mode_active:body.vacation_mode,assumptions:'Manual hypothetical inputs',scoring_breakdown:[{factor:'OUTSIDE_NORMAL_SPENDING_AREA',delta:.25,detail:'Hypothetical geography'}]};
  if(path.endsWith('/briefing'))result=state.briefing;
  return {ok:true,status:200,json:async()=>result};
 };
 w.eval(fs.readFileSync('app/web/finance-utils.js','utf8')+'\n'+fs.readFileSync('app/web/app.js','utf8')+'\n'+fs.readFileSync('app/web/reference.js','utf8'));
 return {w,dom,calls,state};
}
test('reference toolkit renders benchmark values and every engine with source/example labels',async()=>{
 const c=setup();try{
  await c.w.loadReferenceReview(20111);
  const d=c.w.document;
  assert.equal(d.getElementById('source-review').hidden,false);
  assert.match(d.getElementById('review-metrics').textContent,/6,339.39/);
  assert.match(d.getElementById('review-metrics').textContent,/17,611.86/);
  assert.match(d.getElementById('review-shock-cards').textContent,/3.4/);
  assert.match(d.getElementById('review-installments').textContent,/8.50/);
  assert.match(d.getElementById('review-pyramid-values').textContent,/Needs categorization/);
  assert.ok(d.querySelector('#review-trend-chart polyline'));
  assert.doesNotMatch(d.getElementById('review-subscriptions').textContent,/illustrative_reference_example/);
  assert.match(d.getElementById('review-inflation').textContent,/2025-Q4/);
  assert.match(d.getElementById('review-goal').textContent,/Currently Affordable/);
  assert.match(d.getElementById('review-context').textContent,/historical/);
  assert.equal(d.getElementById('dataset-admin-summaries').hidden,true);
 }finally{c.w.close();}
});
test('reference custom controls and manual fraud inputs reach their read-only endpoints',async()=>{
 const c=setup();try{
  await c.w.loadReferenceReview(20111);
  const d=c.w.document,f=d.getElementById('review-scenario');
  f.elements.income_reduction_pct.value='25';f.elements.bills_increase_pct.value='15';f.elements.one_off_costs.value='500';
  f.dispatchEvent(new c.w.Event('submit',{cancelable:true}));await flush();
  const request=c.calls.find(r=>r.body?.scenario_id==='CUSTOM');
  assert.equal(request.body.income_reduction_pct,.25);assert.equal(request.body.one_off_costs,500);
  const fraud=d.getElementById('review-fraud');fraud.elements.vacation_mode.checked=true;
  fraud.dispatchEvent(new c.w.Event('submit',{cancelable:true}));await flush();
  assert.equal(c.calls.find(r=>r.path.endsWith('/fraud')).body.vacation_mode,true);
  assert.match(d.getElementById('review-fraud-score').textContent,/Needs review/);
  assert.match(d.getElementById('review-fraud-factors').textContent,/Hypothetical geography/);
  d.getElementById('review-cloud-audio').click();await flush();
  assert.equal(c.calls.some(r=>r.path.endsWith('/audio')),false);
  assert.match(d.getElementById('status').textContent,/Enable external processing/);
  c.w.resetReferenceReview();assert.equal(d.getElementById('review-analysis').hidden,true);
  assert.equal(d.getElementById('review-external-consent').checked,false);
 }finally{c.w.close();}
});

test('Gemini summary requests selected voice and renders automatically returned MP3',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);const d=c.w.document;d.getElementById('review-external-consent').checked=true;d.getElementById('review-auto-audio').checked=true;d.getElementById('review-voice-profile').value='empathetic';c.state.briefing={...fixture.briefing,audio_base64:Buffer.from('ID3-fixture').toString('base64'),audio_status:'generated'};d.getElementById('review-summary').click();await flush();const request=c.calls.find(r=>r.path.endsWith('/briefing'));assert.equal(request.body.generate_audio,true);assert.equal(request.body.profile,'empathetic');assert.equal(request.body.allow_external_processing,true);assert.ok(d.querySelector('#review-audio audio'));assert.equal(d.querySelector('#review-audio audio').src,'blob:generated-fixture');}finally{c.w.close();}});

test('rapid account switching ignores an older delayed response',async()=>{const c=setup();try{let release;c.state.pending['source-review/1/simulate']=new Promise(r=>release=r);const old=c.w.loadReferenceReview(1);await c.w.loadReferenceReview(2);release();await old;const d=c.w.document;assert.match(d.getElementById('review-context').textContent,/02/);assert.doesNotMatch(d.getElementById('review-context').textContent,/01 ?/);}finally{c.w.close();}});

test('all four preset buttons synchronize fields ranges and selected state',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);const d=c.w.document;const expected=[[45,0,0,6],[0,0,fixture.metrics.typical_spending_S,1],[45,15,0,6],[10,25,0,12]];for(const [i,b] of [...d.querySelectorAll('#review-presets button')].entries()){b.click();await flush();const form=d.getElementById('review-scenario');['income_reduction_pct','bills_increase_pct','one_off_costs','shock_duration_months'].forEach((key,n)=>{assert.equal(Number(form.elements[key].value),expected[i][n]);assert.equal(Number(form.querySelector('[data-field='+key+']').value),expected[i][n]);});assert.equal(b.getAttribute('aria-pressed'),'true');}const number=d.getElementById('review-scenario').elements.bills_increase_pct;number.value='31';number.dispatchEvent(new c.w.Event('input'));assert.equal(d.querySelector('[data-field=bills_increase_pct]').value,'31');}finally{c.w.close();}});

test('account notifications deduplicate and dismissal stays scoped to account',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);const d=c.w.document;const count=d.querySelectorAll('#account-notifications .notification').length;assert.ok(count>0);d.querySelector('#account-notifications button').click();await c.w.loadReferenceReview(20111);assert.equal(d.querySelectorAll('#account-notifications .notification').length,count-1);await c.w.loadReferenceReview(20133);assert.equal(d.querySelectorAll('#account-notifications .notification').length,count);}finally{c.w.close();}});

test('profile masks confidential identifiers and detailed sections collapse',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);const d=c.w.document,profile=d.getElementById('review-profile').textContent;assert.doesNotMatch(profile,new RegExp(fixture.profile.birth_date));assert.doesNotMatch(profile,/\{"/);assert.equal(d.getElementById('dataset-detail-panel').open,false);assert.equal(d.querySelectorAll('#review-pyramid polygon[data-allocation]').length,3);assert.doesNotMatch(d.getElementById('review-pyramid-values').textContent,/Invertedtrue|Invertedfalse/);const summary=[...d.querySelectorAll('h3')].find(n=>n.textContent.startsWith('Summary,')),pyramid=[...d.querySelectorAll('h3')].find(n=>n.textContent==='Expense allocation pyramid');assert.ok(summary.compareDocumentPosition(pyramid)&c.w.Node.DOCUMENT_POSITION_FOLLOWING);}finally{c.w.close();}});

test('external voice failure keeps local summary and re-enables controls',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);const d=c.w.document;d.getElementById('review-external-consent').checked=true;c.state.fail='/audio';d.getElementById('review-cloud-audio').click();await flush();assert.match(d.getElementById('status').textContent,/External provider unavailable/);assert.equal(d.getElementById('review-cloud-audio').disabled,false);assert.match(d.getElementById('review-summary-text').textContent,/typical monthly income/);}finally{c.w.close();}});

test('every fraud control is transmitted without approving a transaction',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);const d=c.w.document,f=d.getElementById('review-fraud');Object.entries({amount:'123.45',merchant_name:'Example test',category:'TRAVEL',chargebacks_count:'2',vacation_location:'Example destination'}).forEach(([k,v])=>f.elements[k].value=v);for(const k of ['is_new_store','browsing_match','is_outside_normal_location','is_outside_budget','vacation_mode'])f.elements[k].checked=true;f.dispatchEvent(new c.w.Event('submit',{cancelable:true}));await flush();const b=c.calls.find(r=>r.path.endsWith('/fraud')).body;assert.equal(b.amount,123.45);assert.equal(b.category,'TRAVEL');assert.equal(b.recent_browsing_category,'TRAVEL');assert.equal(b.chargebacks_count,2);assert.equal(b.vacation_location,'Example destination');assert.equal(b.is_outside_budget,true);assert.equal(b.is_new_store,true);assert.doesNotMatch(d.getElementById('review-fraud-score').textContent,/Approved/);}finally{c.w.close();}});

test('stop speech stops all players and cancels browser speech',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);let cancelled=0;c.w.speechSynthesis={cancel:()=>cancelled++};const audio=c.w.document.createElement('audio');c.w.document.getElementById('review-audio').append(audio);c.w.document.getElementById('review-stop').click();assert.equal(cancelled,1);assert.equal(audio.wasPaused,true);c.w.resetReferenceReview();assert.equal(c.w.document.querySelector('#review-audio audio'),null);}finally{c.w.close();}});


test('missing optional history metadata does not crash a valid account response',async()=>{const c=setup();try{c.state.omitAvailability=true;await c.w.loadReferenceReview(20111);const d=c.w.document;assert.match(d.getElementById('review-metrics').textContent,/6,339.39/);assert.equal(d.getElementById('review-error').textContent,'');assert.ok(d.querySelector('#review-trend-chart svg'));}finally{c.w.close();}});

test('older server payload explains a restart instead of throwing a property error',async()=>{const c=setup();try{c.state.omitAvailability=true;c.state.legacyResponse=true;await c.w.loadReferenceReview(20111);const d=c.w.document;assert.match(d.getElementById('review-error').textContent,/server is out of date.*Restart/);assert.doesNotMatch(d.getElementById('review-error').textContent,/Cannot read properties/);assert.equal(d.getElementById('source-review').getAttribute('aria-busy'),'false');}finally{c.w.close();}});

test('custom goals save, update, persist by account, and cannot be deleted',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);const d=c.w.document,form=d.getElementById('custom-goal-form'),host=d.getElementById('custom-goals');
const submit=()=>form.dispatchEvent(new c.w.Event('submit',{cancelable:true}));
for(const [key,value] of Object.entries({name:'Holiday',target:1200,saved:200,monthly:100}))form.elements[key].value=value;submit();assert.match(host.textContent,/10 months/);assert.match(host.textContent,/Holiday/);
[...host.querySelectorAll('button')].find(b=>b.textContent==='Edit goal').click();form.elements.saved.value=1200;submit();assert.match(host.textContent,/Savings target achieved/);assert.equal(host.querySelectorAll('.card').length,1);
await c.w.loadReferenceReview(20133);assert.doesNotMatch(host.textContent,/Holiday/);await c.w.loadReferenceReview(20111);assert.match(host.textContent,/Holiday/);
assert.equal([...host.querySelectorAll('button')].some(b=>b.textContent==='Delete goal'),false);assert.equal(host.querySelectorAll('.card').length,1);
}finally{c.w.close();}});

test('loan status meanings render and goals reject fractional cents',async()=>{const c=setup();try{await c.w.loadReferenceReview(20111);const d=c.w.document,form=d.getElementById('custom-goal-form');assert.match(d.getElementById('review-loan').textContent,/Status D: Loan is active with overdue/);
for(const [key,value] of Object.entries({name:'Reserve',target:'100.001',saved:'0',monthly:'10'}))form.elements[key].value=value;
form.dispatchEvent(new c.w.Event('submit',{cancelable:true}));assert.equal(d.querySelectorAll('#custom-goals .card').length,0);assert.match(form.elements.target.validationMessage,/two decimal places/);
form.elements.target.value='100.01';form.dispatchEvent(new c.w.Event('submit',{cancelable:true}));assert.equal(d.querySelectorAll('#custom-goals .card').length,1);
}finally{c.w.close();}});
