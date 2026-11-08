const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const fixture=JSON.parse(fs.readFileSync('tests/fixtures/reference_20111.json','utf8'));
const flush=async()=>{for(let i=0;i<15;i++)await new Promise(resolve=>setImmediate(resolve));};
function setup(){
 const dom=new JSDOM(fs.readFileSync('app/web/index.html','utf8'),{url:'http://localhost',runScripts:'outside-only'}),w=dom.window,calls=[];
 w.setInterval=()=>0;w.HTMLElement.prototype.scrollIntoView=function(){};
 w.fetch=async(url,options={})=>{
  const path=url.replace('/api/v1/','');const body=options.body?JSON.parse(options.body):null;calls.push({path,body});
  let result=structuredClone(fixture);
  if(path.endsWith('/fraud'))result={anomaly_score:.95,flag_threshold:.85,is_flagged:true,metrics:{z_score:4},vacation_mode_active:body.vacation_mode,assumptions:'Manual hypothetical inputs',scoring_breakdown:[{factor:'OUTSIDE_NORMAL_SPENDING_AREA',delta:.25,detail:'Hypothetical geography'}]};
  if(path.endsWith('/briefing'))result=fixture.briefing;
  return {ok:true,status:200,json:async()=>result};
 };
 w.eval(fs.readFileSync('app/web/app.js','utf8')+'\n'+fs.readFileSync('app/web/reference.js','utf8'));
 return {w,dom,calls};
}
test('reference toolkit renders benchmark values and every engine with source/example labels',async()=>{
 const c=setup();try{
  await c.w.loadReferenceReview(20111);
  const d=c.w.document;
  assert.equal(d.getElementById('source-review').hidden,false);
  assert.match(d.getElementById('review-metrics').textContent,/6,339.39/);
  assert.match(d.getElementById('review-metrics').textContent,/17,611.86/);
  assert.match(d.getElementById('review-shock-cards').textContent,/3.4/);
  assert.match(d.getElementById('review-installments').textContent,/8.5/);
  assert.match(d.getElementById('review-pyramid-values').textContent,/55.1/);
  assert.ok(d.querySelector('#review-trend-chart polyline'));
  assert.match(d.getElementById('review-subscriptions').textContent,/illustrative_reference_example/);
  assert.match(d.getElementById('review-inflation').textContent,/2025-Q4/);
  assert.match(d.getElementById('review-goal').textContent,/Four-month/);
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
  c.w.resetReferenceReview();assert.equal(d.getElementById('source-review').hidden,true);
  assert.equal(d.getElementById('review-external-consent').checked,false);
 }finally{c.w.close();}
});
