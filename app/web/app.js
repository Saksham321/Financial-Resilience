/* Same-origin frontend. Tokens stay in memory; all financial content uses textContent. */
'use strict';
let isAdmin = false;
let token = '', email = '', data = null, accountList = [], vacationList = [], summaryList = [], audioUrl = null;
const $ = id => document.getElementById(id);
function el(tag, text, cls) { const node = document.createElement(tag); if(text !== undefined) node.textContent = text; if(cls) node.className = cls; return node; }
function message(text, error=false) { $('status').replaceChildren(el('div',text,'notice'+(error?' error':''))); }
function fmt(value) { return value === null || value === undefined ? 'Unavailable' : new Intl.NumberFormat('en-CA',{style:'currency',currency:'CAD'}).format(Number(value)); }
async function api(path, method='GET', body, binary=false) {
  const response = await fetch('/api/v1/'+path,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
  if(!response.ok) { let detail; try { const error=await response.json(); detail=error.error?.message || error.detail; if(error.error?.details?.validation_errors) detail += ': '+error.error.details.validation_errors.map(e=>e.msg).join('; '); } catch {} if(response.status===401 && token) signout(); throw Error(detail || 'Request failed ('+response.status+')'); }
  return binary ? response.blob() : response.json();
}
async function action(button, fn) { button.disabled=true; try { await fn(); } catch(error) { message(error.message,true); } finally { button.disabled=false; } }
function button(label, fn, cls='secondary') { const b=el('button',label,cls); b.type='button'; b.onclick=()=>action(b,fn); return b; }
function textList(id, lines) { $(id).replaceChildren(...(lines.length ? lines.map(t=>el('p',t)) : [el('p','No findings yet.','empty')])); }
function table(id, records, columns, controls) {
  const wrapper=el('div',undefined,'table-wrap'); if(!records.length) { $(id).replaceChildren(el('p','No records yet. Add your data to get started.','empty')); return; }
  const t=el('table'), head=el('tr'); columns.forEach(([title])=>head.append(el('th',title))); if(controls) head.append(el('th','Actions')); const th=el('thead'); th.append(head); t.append(th); const body=el('tbody');
  for(const row of records) { const tr=el('tr'); for(const [,key] of columns) { let value=typeof key==='function'?key(row):row[key]; if(value && typeof value==='object') value=JSON.stringify(value); tr.append(el('td',value===null || value===undefined?'—':String(value))); } if(controls) { const cell=el('td'); controls(row).forEach(c=>cell.append(c)); tr.append(cell); } body.append(tr); } t.append(body); wrapper.append(t); $(id).replaceChildren(wrapper);
}
const field=(name,label,type='text',options={})=>({name,label,type,...options});
function makeForm(id,title,fields,onSubmit,values={},expanded=false) {
  const details=el('details'); details.open=expanded; details.append(el('summary',title)); const form=el('form'), grid=el('div',undefined,'fields');
  fields.forEach(f=>{const label=el('label',f.label); let input=el(f.type==='select'?'select':'input'); input.name=f.name; if(f.type==='select') f.choices.forEach(v=>{const o=el('option',v); o.value=v; input.append(o);}); else input.type=f.type; if(f.type==='checkbox') input.checked=Boolean(values[f.name]); else input.value=values[f.name]??f.value??f.choices?.[0]??''; input.required=f.required!==false&&f.type!=='checkbox'; for(const key of ['min','max','step','maxLength']) if(f[key]!==undefined) input[key]=f[key]; label.append(input); grid.append(label);});
  form.append(grid); const submit=el('button','Save'); form.append(submit); form.onsubmit=e=>{e.preventDefault();action(submit,async()=>{ const body={}; fields.forEach(f=>{const input=form.elements[f.name]; if(f.type==='checkbox')body[f.name]=input.checked; else if(input.value!=='')body[f.name]=f.numeric?Number(input.value):input.value; else if(f.nullable)body[f.name]=null; }); await onSubmit(body);message('Saved.');await load();});};details.append(form);$(id).replaceChildren(details); return form;
}
const moneyField=(name,label)=>field(name,label,'number',{step:'.01',required:true});
const coords=[field('latitude','Latitude','number',{min:-90,max:90,step:'any',required:false,nullable:true}),field('longitude','Longitude','number',{min:-180,max:180,step:'any',required:false,nullable:true})];
const accountFields=[field('institution_name','Institution'),field('account_type','Type','select',{choices:['CHECKING','SAVINGS','CREDIT','LOAN']}),field('masked_account_number','Masked number (e.g. ****1234)'),moneyField('current_balance','Current balance'),moneyField('available_balance','Available balance')];
const vacationFields=[field('destination','Destination'),field('start_date','Start date','date'),field('end_date','End date','date'),moneyField('budget','Trip budget'),...coords.map(c=>({...c,required:true})),field('radius_km','Expected travel radius (km)','number',{value:100,min:1,step:'any'}),field('enabled','Vacation enabled','checkbox')];
function forms(privacy) {
 makeForm('account-form','Add an account snapshot',accountFields,b=>api('finance/accounts','POST',b));
 makeForm('transaction-form','Record or import a transaction',[field('external_id','Unique transaction reference'),field('account_id','Account','select',{choices:accountList.map(a=>a.id)}),field('occurred_at','Time (local)','datetime-local'),moneyField('amount','Signed amount (expense negative)'),field('merchant','Merchant'),field('category','Category'),field('cart_size','Cart items','number',{required:false,min:0,numeric:true}),...coords],b=>{b.occurred_at=new Date(b.occurred_at).toISOString();return api('finance/transactions','POST',b);});
 makeForm('flow-form','Add or update an income / obligation schedule',[field('external_id','Unique schedule reference (reuse to update)'),field('name','Name'),field('category','Category'),moneyField('amount','Signed amount (income positive)'),field('due_date','Next / first date','date'),field('recurrence','Repeats','select',{choices:['once','monthly','annual']}),field('end_date','End date (optional)','date',{required:false,nullable:true}),field('active','Active','checkbox')],b=>api('finance/flows','PUT',b),{active:true});
 makeForm('budget-form','Set a monthly category budget',[field('category','Category'),moneyField('monthly_amount','Monthly budget')],b=>api('finance/budgets','PUT',b));
 makeForm('scenario-form','Compare a hypothetical shock',[moneyField('amount','Hypothetical expense'),field('due_date','Due date','date')],async b=>{const r=await api('finance/scenarios','POST',b);table('scenario-result',['30','60','90'].map(days=>({days,baseline:fmt(r.baseline.projections[days]),scenario:fmt(r.scenario.projections[days])})),[['Days ahead','days'],['Baseline balance','baseline'],['With hypothetical expense','scenario']]);});
 makeForm('shock-form','Assess an upcoming financial shock',[field('external_id','Unique shock reference'),field('name','Description'),moneyField('amount','Required amount'),field('due_date','Due date','date')],b=>api('finance/shocks','POST',b));
 makeForm('vacation-form','Add a vacation',vacationFields,b=>api('finance/vacations','POST',b),{enabled:true});
 makeForm('chargeback-form','Record a historical chargeback',[field('external_id','Unique chargeback reference'),field('reported_on','Report date','date'),field('merchant','Merchant')],b=>api('finance/chargebacks','POST',b));
 makeForm('privacy-form','Manage processing consent',[field('ai_consent','Allow AI and voice processing','checkbox'),field('browsing_consent','Allow browsing context retrieval','checkbox'),field('geolocation_consent','Allow location processing','checkbox'),...coords,field('radius_km','Normal spending radius (km)','number',{min:1,step:'any'})],b=>api('finance/privacy','PUT',b),privacy,true);
}
function graph(forecast=data.forecast) {
 const host=$('forecast');host.replaceChildren();host.append(el('p',forecast.limited_history?'Limited history: fewer than six complete months. Estimates may be unreliable.':'Forecast uses up to twelve months of completed monthly history.',forecast.limited_history?'warning':'muted'));
 const values=[Number(forecast.balance),...['30','60','90'].map(d=>Number(forecast.projections[d]))], min=Math.min(0,...values),max=Math.max(1,...values),range=max-min;
 const ns='http://www.w3.org/2000/svg', svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 440 180');svg.setAttribute('role','img');svg.setAttribute('aria-label','Balance projection for today, thirty, sixty and ninety days');
 const line=document.createElementNS(ns,'polyline');line.setAttribute('points',values.map((v,i)=>(30+i*125)+','+(135-(v-min)/range*110)).join(' '));line.setAttribute('stroke','#c2410c');line.setAttribute('stroke-width','3');line.setAttribute('fill','none');svg.append(line);
 values.forEach((v,i)=>{const t=document.createElementNS(ns,'text');t.setAttribute('x',String(15+i*125));t.setAttribute('y','164');t.setAttribute('font-size','11');t.textContent=['Now','30 days','60 days','90 days'][i];svg.append(t);});host.append(svg);
 host.append(el('p',forecast.assumptions,'muted'));
}
function renderPyramid(p=data.pyramid, format=fmt) {
 const host=$('pyramid');host.replaceChildren();
 host.append(el('p','Green: more than 5 percentage points below target. Yellow: at or within 5 points below target. Red: over target.','muted'));
 for(const key of ['peak','middle','base']) {
  const actual=p.actual_percent[key], targetPercent=Number(p.target_percent[key]);
  const status=actual===null||actual===undefined?'unknown':Number(actual)>targetPercent?'over':targetPercent-Number(actual)<=5?'near':'below';
  const statusLabel={over:'Red ? Over target',near:'Yellow ? Near target',below:'Green ? Below target',unknown:'Unavailable'}[status];
  const label=el('div',key.toUpperCase()+': '+format(p.totals[key])+' ? '+(actual===null||actual===undefined?'income unavailable':actual+'%')+' / target '+p.target_percent[key]+'%');
  host.append(label);
  const bar=el('div',undefined,'bar'),fill=el('div',undefined,'fill '+status),target=el('div',undefined,'target');
  bar.dataset.status=status;bar.setAttribute('role','img');bar.setAttribute('aria-label',key+': '+statusLabel+(actual===null||actual===undefined?'':', '+actual+' percent; target '+targetPercent+' percent'));
  fill.style.width=Math.min(100,Math.max(0,Number(actual||0)))+'%';target.style.left=targetPercent+'%';bar.append(fill,target);host.append(bar);
 }
 host.append(el('p','Deformity score: '+(p.deformity_score??'unavailable with incomplete classification or income')+(p.inverted?' ? Inverted pyramid: discretionary spending exceeds fixed essentials.':''),p.inverted?'warning':'muted'));
 if(p.warning)host.append(el('p',p.warning,'warning'));
}
function renderOffers() { const host=$('offers');host.replaceChildren();for(const offer of data.offers){const card=el('article',undefined,'card'),t=offer.terms;card.append(el('h3',offer.months+' month plan'),el('strong',fmt(t.payment)+' / month'),el('p','Principal '+fmt(t.principal)+' · Fee '+fmt(t.fee)+' · Annual rate '+t.annual_rate_percent+'%'),el('p','Total interest '+fmt(t.total_interest)+' · Total repayment '+fmt(t.total_repayment)),el('p','Affordability: '+(t.affordable?'within projected capacity':'exceeds projected capacity')),el('p','Status: '+offer.status+' · Expires '+offer.expires_on));if(offer.status==='proposed'){const label=el('label','I understand and accept the local repayment schedule. This does not secure lender funding.'),confirm=el('input');confirm.type='checkbox';label.append(confirm);card.append(label,button('Accept plan',async()=>{await api('finance/offers/'+offer.id+'/decision','POST',{decision:'accepted',confirm_obligation:confirm.checked});await load();}),button('Reject',async()=>{await api('finance/offers/'+offer.id+'/decision','POST',{decision:'rejected'});await load();}));}host.append(card);}if(!data.offers.length)host.append(el('p','No installment offers. Offers require verified credit ineligibility and configured rate and fee.','empty'));}
function map(v,container) {const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 720 360');svg.setAttribute('class','map');svg.setAttribute('role','img');svg.setAttribute('aria-label','Vacation transaction locations on a longitude and latitude grid');for(let x=0;x<=720;x+=60){const l=document.createElementNS(ns,'path');l.setAttribute('d',`M${x} 0V360`);l.setAttribute('stroke','#e8cdb5');svg.append(l);}for(let y=0;y<=360;y+=60){const l=document.createElementNS(ns,'path');l.setAttribute('d',`M0 ${y}H720`);l.setAttribute('stroke','#e8cdb5');svg.append(l);}for(const t of v.transactions.filter(t=>t.latitude!==null&&t.longitude!==null)){const c=document.createElementNS(ns,'circle');c.setAttribute('cx',String((Number(t.longitude)+180)*2));c.setAttribute('cy',String((90-Number(t.latitude))*2));c.setAttribute('r','5');c.setAttribute('fill','#c2410c');const title=document.createElementNS(ns,'title');title.textContent=t.merchant+' · '+t.category+' · '+fmt(t.amount)+' · '+t.latitude+', '+t.longitude;c.append(title);svg.append(c);}container.append(svg,el('p','Coordinate grid: longitude −180° to 180°, latitude 90° to −90°. Each point is a recorded merchant location.','muted'));}
async function load() {
 if(!token){await loadDataset();return;}
 const activeToken=token;
 const [d,accounts,txs,flows,budgets,vacations,chargebacks,privacy,summaries]=await Promise.all([api('finance/dashboard'),api('finance/accounts'),api('finance/transactions'),api('finance/flows'),api('finance/budgets'),api('finance/vacations'),api('finance/chargebacks'),api('finance/privacy'),api('finance/summaries')]);
 if(token!==activeToken)return;
 data=d;accountList=accounts;vacationList=vacations;summaryList=summaries;forms(privacy);
 renderFinancialOverview(d);renderOffers();
 table('accounts',accounts,[['Institution','institution_name'],['Type','account_type'],['Number','masked_account_number'],['Available',a=>fmt(a.available_balance)]],a=>[button('Update snapshot',()=>{makeForm('account-form','Update account snapshot',accountFields,b=>api('finance/accounts/'+a.id,'PUT',b),a,true);$('account-form').scrollIntoView();})]);
 table('transactions',txs,[['Time','occurred_at'],['Merchant','merchant'],['Category','category'],['Amount',t=>fmt(t.amount)],['Anomaly score',t=>t.fraud.score],['Location',t=>t.latitude===null?'Not provided':t.latitude+', '+t.longitude]]);
 table('flows',flows,[['Name','name'],['Reference','external_id'],['Amount',f=>fmt(f.amount)],['First / next due','due_date'],['Repeats','recurrence'],['Active','active']]);table('budgets',budgets,[['Category','category'],['Monthly amount',b=>fmt(b.monthly_amount)]]);
 table('shocks',d.shocks,[['Shock','name'],['Due','due_date'],['Amount',s=>fmt(s.amount)],['Shortfall',s=>fmt(s.shortfall)],['Credit route','routing']],s=>[button('Recheck eligibility',async()=>{await api('finance/shocks/'+s.id+'/reassess','POST');await load();})]);
 table('fraud',d.fraud_alerts,[['Merchant','merchant'],['Amount',t=>fmt(t.amount)],['Score',t=>t.fraud.score],['Reasons',t=>t.fraud],['Review status',()=> 'Needs review; not confirmed fraud']]);
 $('vacations').replaceChildren();for(const v of vacations){const panel=el('article');panel.append(el('h3',v.destination),el('p',v.start_date+' to '+v.end_date+' · '+(v.enabled?'Enabled':'Disabled')),el('p','Spent '+fmt(v.total_spent)+' · Remaining '+fmt(v.remaining_budget)),button('Edit / disable',()=>{makeForm('vacation-form','Edit vacation',vacationFields,b=>api('finance/vacations/'+v.id,'PUT',b),v,true);$('vacation-form').scrollIntoView();}));map(v,panel);for(const t of v.transactions)panel.append(el('p',t.merchant+' · '+t.category+' · '+fmt(t.amount)+' · '+(t.latitude===null?'Location unavailable':t.latitude+', '+t.longitude)));$('vacations').append(panel);}
 table('chargebacks',chargebacks,[['Merchant','merchant'],['Report date','reported_on'],['Reference','external_id']]);
 table('subscriptions',d.subscriptions,[['Merchant','merchant'],['Category','category'],['Billing amount',s=>fmt(s.amount)],['Cadence','cadence'],['Next billing','next_billing'],['Status','status']],s=>['active','cancellation_requested','cancelled'].filter(status=>status!==s.status).map(status=>button(status.replaceAll('_',' '),async()=>{await api('finance/subscriptions/'+s.id,'PATCH',{status});await load();})));textList('subscription-advice',d.subscription_recommendations);
 const inf=d.inflation;table('inflation',inf.quarters,[['Quarter','quarter'],['Nominal income',q=>fmt(q.nominal_income)],['Nominal expenses',q=>fmt(q.nominal_expenses)],['Real income',q=>fmt(q.real_income)],['Real expenses',q=>fmt(q.real_expenses)],['Income growth %','real_income_growth_percent'],['Expense growth %','real_expense_growth_percent'],['Insights',q=>q.alerts.join(' ')||'No alert'],['Coverage',q=>q.incomplete_transactions?'Incomplete transaction history':'Transactions span three months']]);$('inflation').prepend(el('p','CPI reference: '+(inf.reference_month||'not downloaded')+(inf.requires_cpi?' · Some quarters require CPI observations.':'')));
 table('notifications',d.notifications,[['Title','title'],['Message','message'],['Delivery','delivery_status'],['Read','read']],n=>n.read?[]:[button('Mark read',async()=>{await api('finance/notifications/'+n.id+'/read','POST');await load();})]);
 $('summaries').replaceChildren();for(const s of summaries){const panel=el('article');panel.append(el('p',s.created_at,'muted'),el('pre',s.text));for(const profile of ['professional','empathetic'])panel.append(button('Listen · '+profile,async()=>{message('Generating audio…');await api('finance/summaries/'+s.id+'/audio','POST',{profile});const blob=await api('finance/summaries/'+s.id+'/audio','GET',null,true);const audio=el('audio');audio.controls=true;if(audioUrl)URL.revokeObjectURL(audioUrl);audioUrl=URL.createObjectURL(blob);audio.src=audioUrl;panel.querySelector('audio')?.remove();panel.append(audio);message('Audio ready. Use the player to play, pause or replay.');}));$('summaries').append(panel);}
 table('integrations',Object.entries(d.integration_status).map(([name,status])=>({name,status})),[['Integration','name'],['Status','status']]);
 await loadDataset();
}
function signout(){isAdmin=false;updateDatasetAdminView();resetDataset();token='';email='';data=null;accountList=[];vacationList=[];summaryList=[];$('workspace').hidden=false;$('overview').hidden=true;document.body.classList.add('public-view');$('auth').hidden=false;$('logout').hidden=true;$('identity').textContent='';for(const id of ['metrics','forecast','pyramid','recommendations','notifications','accounts','transactions','flows','budgets','shocks','offers','projected-shocks','fraud','vacations','chargebacks','subscriptions','subscription-advice','inflation','summaries','scenario-result','integrations','account-form','transaction-form','flow-form','budget-form','shock-form','vacation-form','chargeback-form','privacy-form','scenario-form'])$(id).replaceChildren();$('summary-form').reset();if(audioUrl)URL.revokeObjectURL(audioUrl);audioUrl=null;delivered.clear();}
for(const type of ['login'])$(type).onsubmit=e=>{e.preventDefault();const form=e.currentTarget;action(form.querySelector('button'),async()=>{const body=Object.fromEntries(new FormData(form));const result=await api('auth/'+type,'POST',body);resetDataset();token=result.access_token;email=result.email;isAdmin=result.role==='admin';updateDatasetAdminView();document.body.classList.remove('public-view');form.reset();$('identity').textContent=email;$('auth').hidden=true;$('workspace').hidden=false;$('logout').hidden=false;message('Loading your financial picture…');await load();message('Your data is up to date.');});};
$('logout').onclick=signout;$('refresh').onclick=()=>action($('refresh'),async()=>{await load();message('Updated.');});$('bank-sync').onclick=()=>action($('bank-sync'),async()=>{await api('finance/banking/sync','POST');await load();message('Bank snapshots synchronized.');});$('cpi-refresh').onclick=()=>action($('cpi-refresh'),async()=>{await api('finance/inflation/refresh','POST');await load();message('Statistics Canada CPI retrieved.');});
$('summary-form').onsubmit=e=>{e.preventDefault();action(e.currentTarget.querySelector('button'),async()=>{message('Generating verified summary…');await api('finance/summaries','POST',Object.fromEntries(new FormData($('summary-form'))));await load();message('Summary ready.');});};
const delivered=new Set();$('push').onclick=()=>action($('push'),async()=>{if(!('Notification' in window))throw Error('This browser does not support device alerts. In-app alerts remain available.');const permission=await Notification.requestPermission();message(permission==='granted'?'Device alerts enabled while this dashboard is open.':'Device alerts were not enabled. In-app alerts remain available.');});
setInterval(async()=>{if(!token)return;const activeToken=token;try{const fresh=await api('finance/dashboard');if(token!==activeToken)return;if('Notification' in window&&Notification.permission==='granted')for(const n of fresh.notifications)if(!n.read&&!delivered.has(n.id)){new Notification(n.title,{body:n.message});delivered.add(n.id);}}catch(error){message(error.message,true);}},60000);

let datasetVersion=0, datasetDetailVersion=0, datasetOffset=0, datasetFilter='', datasetSelected=null, datasetUseOverview=false;
const sourceNumber=value=>value===null||value===undefined?'Unavailable':new Intl.NumberFormat('en-CA',{maximumFractionDigits:2}).format(Number(value));
function datasetCards(id, pairs) {
 $(id).replaceChildren(...pairs.map(([title,value])=>{const c=el('div',undefined,'card');c.append(el('span',title,'muted'),el('strong',value));return c;}));
}
function renderFinancialOverview(view, analysis=null) {
 const f=view.forecast,p=view.pyramid,format=analysis?(value=>sourceNumber(value)+' source units'):fmt;
 $('overview-context').textContent=analysis?`Viewing source account ${analysis.account_id} as of ${analysis.as_of}; projections start ${analysis.projection_reference}. Currency unspecified. This is a historical, read-only view. Plans, offers, and other personal tools still use your own records.`:'Viewing your personal finances in CAD.';
 $('financial-context-label').textContent=analysis?'SOURCE ACCOUNT '+analysis.account_id+' · HISTORICAL SOURCE UNITS':'YOUR FINANCIAL PICTURE · CAD';
 $('overview').hidden=false;$('overview-personal').hidden=!analysis||!token;
 $('pyramid-caption').textContent=analysis?'Classified source spending as a share of income for '+p.period+'. Unknown spending is disclosed below.':'Actual spending as a share of this month’s income.';
 datasetCards('metrics',[['Available liquidity',format(f.balance)],['Monthly cash flow',format(f.monthly_cash_flow)],['Financial runway',f.runway_days===null?'Beyond 365 days':f.runway_days+' days'],['90-day projection',format(f.projections['90'])]]);
 graph(f);renderPyramid(p,format);
 textList('recommendations',analysis?analysis.recommendations:[...p.recommendations,...f.recommendations.map(r=>r.action+' in '+r.category+': save '+fmt(r.monthly_saving)+' monthly; runway gain '+(r.runway_gain_days===null?'not reached within horizon':r.runway_gain_days+' days')+'.')]);
 table('projected-shocks',f.projected_shocks||[],[['Due date','due_date'],['Scheduled net outflow',s=>format(s.scheduled_net_outflow)],['Projected shortfall',s=>format(s.projected_shortfall)]]);
}
$('overview-personal').onclick=()=>{datasetUseOverview=false;if(data)renderFinancialOverview(data);};
function resetDataset() {
 datasetVersion++;datasetDetailVersion++;datasetOffset=0;datasetFilter='';datasetSelected=null;datasetUseOverview=false;
 $('financial-context-label').textContent='SEARCH BY SOURCE ACCOUNT ID';$('overview-personal').hidden=true;
 for(const id of ['dataset-status','dataset-metrics','dataset-archetypes','dataset-regions','dataset-accounts','dataset-pagination','dataset-account-metrics','dataset-account-fields','dataset-history','dataset-source-files','dataset-transactions','dataset-transaction-pagination'])$(id).replaceChildren();
 $('dataset-detail-panel').hidden=true;$('dataset-search').reset();
}
async function showDatasetAccount(id, updateOverview=datasetUseOverview) {
 const activeToken=token, version=++datasetDetailVersion;datasetSelected=id;
 $('dataset-detail-panel').hidden=false;$('dataset-detail-title').textContent='Loading account '+id+'…';
 $('dataset-transactions').replaceChildren();$('dataset-transaction-pagination').replaceChildren();
 $('dataset-account-metrics').replaceChildren();$('dataset-account-fields').replaceChildren();$('dataset-history').replaceChildren();
 try {
  const detail=await api('datasets/accounts/'+id);
  if(token!==activeToken||version!==datasetDetailVersion)return;
  const a=detail.account;
  if(updateOverview){
   if(!detail.analysis)throw Error('This source account has no monthly history to calculate its financial overview.');
   datasetUseOverview=true;renderFinancialOverview(detail.analysis,detail.analysis);
  }
  $('dataset-detail-title').textContent='Source account '+a.account_id+' · '+a.region;
  datasetCards('dataset-account-metrics', [['Profile',a.archetype],['Source buffer (B)',sourceNumber(a.B)],['Source income (I)',sourceNumber(a.I)],['Source spending (S)',sourceNumber(a.S)]]);
  table('dataset-account-fields',Object.entries(a).map(([name,value])=>({name:name.replaceAll('_',' '),value})),[['Source field','name'],['Value','value']]);
  table('dataset-history',detail.months,[['Month','month'],['Money in',r=>sourceNumber(r.money_in)],['Money out',r=>sourceNumber(r.money_out)],['Household bills',r=>sourceNumber(r.household_bills)],['Insurance',r=>sourceNumber(r.insurance)],['Loan payments',r=>sourceNumber(r.loan_payments)],['Average daily balance',r=>sourceNumber(r.avg_daily_balance)],['Month-end balance',r=>sourceNumber(r.month_end_balance)]]);
  await loadDatasetTransactions(id);
 } catch(error) {if(token===activeToken&&version===datasetDetailVersion){$('dataset-history').replaceChildren(el('p',error.message,'notice error'));if(updateOverview&&data){datasetUseOverview=false;renderFinancialOverview(data);}}}
}
function updateDatasetAdminView() {
 for(const id of ['dataset-clear','dataset-admin-summaries','dataset-admin-accounts'])$(id).hidden=!isAdmin;
}
async function loadDataset(offset=datasetOffset) {
 updateDatasetAdminView();
 if(!isAdmin&&!datasetFilter){$('dataset-status').textContent='Enter a source account ID to view its financial outlook and history.';return;}
 const activeToken=token,version=++datasetVersion;datasetOffset=offset;
 $('dataset-status').textContent='Loading imported records…';
 try {
  const [overview,page]=await Promise.all([isAdmin?api('datasets/overview'):Promise.resolve({available:true}),api('datasets/accounts?offset='+offset+'&limit=25'+(datasetFilter?'&account_id='+encodeURIComponent(datasetFilter):''))]);
  if(token!==activeToken||version!==datasetVersion)return;
  if(!overview.available){$('dataset-status').textContent='No imported dataset was found in the running server’s database. Import the files into that database, then reload.';return;}
  if(isAdmin){datasetCards('dataset-metrics', [['Imported accounts',sourceNumber(overview.accounts)],['Monthly records',sourceNumber(overview.monthly_records)],['History',overview.period.first+' to '+overview.period.last],['Currency',overview.currency]]);
  const insights=overview.insights;
  table('dataset-source-files',overview.source_files||[],[['Imported source','source'],['Records',r=>sourceNumber(r.rows)]]);
  table('dataset-archetypes',Object.entries(insights.archetypes||{}).map(([profile,count])=>({profile,count})),[['Profile','profile'],['Accounts','count']]);
  table('dataset-regions',insights.regional_breakdown||[],[['Region','region'],['Accounts','accounts'],['Average source buffer',r=>sourceNumber(r.avg_buffer)]]);
  }
  table('dataset-accounts',page.items,[['Source account','account_id'],['Region','region'],['Profile','archetype'],['Source buffer (B)',r=>sourceNumber(r.B)],['Net cash flow',r=>sourceNumber(r.net_cash_flow)]],a=>[button('View history',()=>showDatasetAccount(a.account_id,true))]);
  const previous=button('Previous',()=>loadDataset(Math.max(0,offset-25))),next=button('Next',()=>loadDataset(offset+25));previous.disabled=offset===0;next.disabled=offset+page.items.length>=page.total;
  $('dataset-pagination').replaceChildren(previous,el('span',page.total?`${offset+1}–${offset+page.items.length} of ${sourceNumber(page.total)} accounts`:'No matching source account'),next);
  $('dataset-status').textContent=page.items.length?(isAdmin?'Imported records loaded. Select an account to inspect its original snapshot and monthly history.':'Source account found. Its financial outlook and history are shown below.'):'No source account matches that ID.';
  if(page.items.length)await showDatasetAccount(page.items.some(a=>a.account_id===datasetSelected)?datasetSelected:page.items[0].account_id,datasetUseOverview);
  else {$('dataset-detail-panel').hidden=true;datasetDetailVersion++;datasetUseOverview=false;if(data)renderFinancialOverview(data);else $('overview').hidden=true;}
 } catch(error) {if(token===activeToken&&version===datasetVersion)$('dataset-status').replaceChildren(el('p','Imported data could not load: '+error.message,'notice error'));}
}
$('dataset-refresh').onclick=()=>action($('dataset-refresh'),()=>loadDataset());
$('dataset-search').onsubmit=e=>{e.preventDefault();datasetFilter=$('dataset-search').elements.account_id.value;datasetUseOverview=Boolean(datasetFilter);if(!datasetUseOverview&&data)renderFinancialOverview(data);action(e.currentTarget.querySelector('button'),()=>loadDataset(0));};
$('dataset-clear').onclick=()=>{if(!isAdmin)return;datasetFilter='';$('dataset-search').reset();action($('dataset-clear'),()=>loadDataset(0));};

let datasetTransactionVersion=0;
async function loadDatasetTransactions(id, offset=0) {
 const activeToken=token, version=++datasetTransactionVersion,detailVersion=datasetDetailVersion;
 $('dataset-transactions').textContent='Loading source transactions…';$('dataset-transaction-pagination').replaceChildren();
 try {
  const page=await api('datasets/accounts/'+id+'/transactions?offset='+offset+'&limit=50');
  if(token!==activeToken||version!==datasetTransactionVersion||detailVersion!==datasetDetailVersion)return;
  table('dataset-transactions',page.items,[['Reference','transaction_id'],['Date','date'],['Direction','direction'],['Operation','operation'],['Purpose','purpose'],['Signed amount',r=>sourceNumber(r.signed_amount)],['Balance',r=>sourceNumber(r.balance)]]);
  if(!page.total)$('dataset-transactions').textContent='No source transactions imported for this account.';
  const previous=button('Earlier page',()=>loadDatasetTransactions(id,Math.max(0,offset-50))),next=button('More transactions',()=>loadDatasetTransactions(id,offset+50));
  previous.disabled=offset===0;next.disabled=offset+page.items.length>=page.total;
  $('dataset-transaction-pagination').replaceChildren(previous,el('span',page.total?`${offset+1}–${offset+page.items.length} of ${sourceNumber(page.total)} source transactions`:'0 transactions'),next);
 } catch(error){if(token===activeToken&&version===datasetTransactionVersion&&detailVersion===datasetDetailVersion)$('dataset-transactions').replaceChildren(el('p',error.message,'notice error'));}
}


// Source-account lookup is available immediately; personal APIs still require JWT.
loadDataset();
