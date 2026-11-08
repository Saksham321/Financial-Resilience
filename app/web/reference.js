/* Read-only source-account toolkit. All strings render through textContent. */
'use strict';
let reviewAccount=null,reviewVersion=0,reviewData=null,reviewScenario={scenario_id:'LAID_OFF_EI'},reviewAudioUrl=null;
const reviewValue=v=>v===null||v===undefined?'Unavailable':typeof v==='number'?sourceNumber(v):String(v);
function reviewFields(id,object){table(id,Object.entries(object||{}).map(([name,value])=>({name:name.replaceAll('_',' '),value})),[['Metric','name'],['Value','value']]);}
function resetReferenceReview(){
 reviewVersion++;reviewAccount=null;reviewData=null;reviewScenario={scenario_id:'LAID_OFF_EI'};
 $('source-review').hidden=true;$('review-external-consent').checked=false;
 for(const id of ['review-profile','review-metrics','review-all-metrics','review-orders','review-shock-cards','review-comparison','review-mediation','review-credit','review-installments','review-pyramid','review-pyramid-values','review-trend','review-trend-chart','review-projections','review-actions','review-subscription-metrics','review-subscription-alerts','review-subscriptions','review-inflation-summary','review-inflation-alerts','review-inflation','review-fraud-score','review-fraud-factors','review-summary-text','review-goal','review-backup','review-audio','review-error'])$(id).replaceChildren();
 stopReviewSpeech();if(reviewAudioUrl)URL.revokeObjectURL(reviewAudioUrl);reviewAudioUrl=null;
}
window.resetReferenceReview=resetReferenceReview;
async function loadReferenceReview(id,scenario={scenario_id:'LAID_OFF_EI'}){
 const version=++reviewVersion,activeToken=token;reviewAccount=id;reviewScenario=scenario;
 $('source-review').hidden=false;$('review-context').textContent='Loading reference analysis for source account '+id+'…';
 $('review-error').replaceChildren();
 try{
  const value=await api('source-review/'+id+'/simulate','POST',scenario);
  if(version!==reviewVersion||token!==activeToken)return;
  reviewData=value;renderReferenceReview(value);
 }catch(error){if(version===reviewVersion)$('review-error').replaceChildren(el('p',error.message,'notice error'));}
}
window.loadReferenceReview=loadReferenceReview;
function renderReviewBriefing(value){
 $('review-briefing-source').textContent='Summary source: '+value.source+(value.external_error?' · External service unavailable: '+value.external_error:'');
 $('review-summary-text').replaceChildren(el('p',value.summary_text));
 reviewFields('review-goal',Object.fromEntries(Object.entries(value.goal_plan).filter(([k])=>k!=='action_steps')));
 for(const step of value.goal_plan.action_steps)$('review-goal').append(el('p',step));
 reviewFields('review-backup',Object.fromEntries(Object.entries(value.backup_plan).filter(([k])=>k!=='immediate_actions')));
 for(const step of value.backup_plan.immediate_actions)$('review-backup').append(el('p',step));
}
function renderReferenceReview(r){
 const m=r.metrics,s=r.shock,p=r.pyramid,pred=r.predictive;
 $('review-context').textContent=`Source account ${r.account_id} · historical data through ${r.as_of} · source units, currency unspecified. Reference examples are simulations and do not change your accounts.`;
 reviewFields('review-profile',r.profile);
 datasetCards('review-metrics',[['Monthly money in (I)',reviewValue(m.typical_income_I)],['Fixed costs (F)',reviewValue(m.typical_fixed_costs_F)],['Monthly spending (S)',reviewValue(m.typical_spending_S)],['Savings buffer (B)',reviewValue(m.savings_buffer_B)],['Baseline runway (months)',reviewValue(m.baseline_runway_months)],['Net monthly cash flow',reviewValue(m.net_monthly_cashflow)],['Savings rate',m.savings_rate_pct+'%']]);
 reviewFields('review-all-metrics',m);table('review-orders',r.standing_orders,[['Order','order_id'],['Bank','to_bank'],['Amount','amount'],['Purpose','purpose']]);
 $('review-shock-title').textContent=s.scenario_title+' · '+s.scenario_description;
 datasetCards('review-shock-cards',[['Post-shock runway (months)',reviewValue(s.post_shock.runway_months)],['Resilience tier',s.post_shock.resilience_tier],['Monthly shortfall',reviewValue(s.post_shock.monthly_gap)],['Remaining buffer',reviewValue(s.post_shock.buffer_left)]]);
 table('review-comparison',[
  {metric:'Monthly income',baseline:s.baseline.income,shock:s.post_shock.income},
  {metric:'Monthly spending',baseline:s.baseline.spending,shock:s.post_shock.spending},
  {metric:'Buffer',baseline:s.baseline.buffer,shock:s.post_shock.buffer_left},
  {metric:'Monthly gap',baseline:-s.baseline.net_monthly,shock:s.post_shock.monthly_gap},
  {metric:'Runway (months)',baseline:s.baseline.runway,shock:s.post_shock.runway_months},
  ...Object.entries(s.shock_parameters).map(([metric,value])=>({metric:metric.replaceAll('_',' '),baseline:'—',shock:value}))
 ],[['Metric','metric'],['Baseline','baseline'],['With shock','shock'],['Change',r=>typeof r.baseline==='number'&&typeof r.shock==='number'?sourceNumber(r.shock-r.baseline):'—']]);
 const parameters=s.shock_parameters,form=$('review-scenario');
 for(const key of ['income_reduction_pct','bills_increase_pct','one_off_costs','shock_duration_months'])form.elements[key].value=parameters[key];
 for(const slider of form.querySelectorAll('input[type=range]'))slider.value=form.elements[slider.dataset.field].value;
 $('review-mediation').replaceChildren(el('p',r.mediation.status+' · modeled shock '+r.mediation.shock_amount+'; buffer '+r.mediation.liquid_buffer+'; shortfall '+r.mediation.shortfall_amount));
 reviewFields('review-credit',r.mediation.credit_evaluation);
 if(r.mediation.line_of_credit_proposal){$('review-credit').append(el('h4','Modeled line of credit'));const host=el('pre',JSON.stringify(r.mediation.line_of_credit_proposal,null,2));$('review-credit').append(host);}
 table('review-installments',r.mediation.installment_proposal?.plans||[],[['Term (months)','term_months'],['Monthly installment','monthly_installment'],['Total repayment','total_repayable'],['Example revenue','projected_bank_revenue'],['APR %','apr'],['Fee structure','fee_structure'],['Description','description']]);
 $('review-pyramid').replaceChildren();
 for(const key of ['peak','middle','base']){
  const actual=p.user_pyramid_ratios[key+'_pct'],target=p.ideal_pyramid_ratios[key+'_pct'];
  $('review-pyramid').append(el('p',key.toUpperCase()+': '+reviewValue(p.user_pyramid_amounts[key+'_cad'])+' source units · '+actual+'% / target '+target+'%'));
  const bar=el('div',undefined,'bar'),fill=el('div',undefined,'fill'),marker=el('div',undefined,'target');
  fill.style.width=Math.min(100,Math.max(0,actual))+'%';fill.style.background=actual>target?'#dc2626':target-actual<=5?'#eab308':'#16a34a';marker.style.left=target+'%';bar.append(fill,marker);$('review-pyramid').append(bar);
 }
 reviewFields('review-pyramid-values',{status:p.visual_status,deformity_score:p.deformity_score,inverted:p.is_inverted,total_monthly_spending:p.total_monthly_spending,typical_monthly_income:p.typical_monthly_income,reallocation:p.proposed_rearrangement,reallocation_amount:p.rearrangement_amount_cad});
 reviewFields('review-trend',{...pred.forecast,projections_30_60_90:undefined,...pred.spending_breakdown});
 const monthly=reviewData?pred.forecast.projections_30_60_90:[];
 drawReferenceTrend(monthly,m.latest_balance);
 table('review-projections',monthly,[['Days','horizon_days'],['Date','target_date'],['Projected monthly outflow','projected_monthly_outflow'],['Projected balance','projected_balance']]);
 table('review-actions',pred.action_plan,[['Action','message'],['Category','category'],['Reduction',v=>(v.target_reduction_pct*100)+'%'],['Monthly saving','monthly_savings_cad'],['Reference runway gain (days)','projected_runway_extension_days']]);
 const subs=r.subscriptions;
 datasetCards('review-subscription-metrics',[['Recurring entries',subs.total_active_subscriptions],['Monthly recurring spend',reviewValue(subs.total_monthly_recurring_spend)],['Illustrative annual savings',reviewValue(subs.total_potential_annual_savings)]]);
 table('review-subscription-alerts',subs.overlap_alerts,[['Category','category'],['Severity','severity'],['Services','services'],['Monthly spend','total_monthly_spend'],['Potential monthly savings','potential_monthly_savings'],['Potential annual savings','potential_annual_savings'],['Trigger','action_trigger'],['Recommendation','message']]);
 table('review-subscriptions',subs.subscriptions,[['Entry','merchant_name'],['Origin','data_origin'],['Category','category'],['Amount','amount'],['Cadence','cadence'],['Example next bill','next_billing_date'],['Example reminder','notification_scheduled_for'],['Overlap','overlap_detected']]);
 const inf=r.inflation;reviewFields('review-inflation-summary',{...inf.summary,benchmark_cpi_period:inf.benchmark_cpi_period,period_cpi_increase_pct:inf.period_cpi_increase_pct});
 table('review-inflation-alerts',inf.active_alerts,[['Alert','title'],['Severity','severity'],['Details','message']]);
 table('review-inflation',inf.trailing_quarters,[['Quarter','quarter'],['Nominal income','nominal_money_in'],['Nominal expenses','nominal_money_out'],['Real income','real_money_in'],['Real expenses','real_money_out'],['CPI','cpi_index'],['Real income growth %','real_income_qoq_pct'],['Real expense growth %','real_expenses_qoq_pct']]);
 renderReviewBriefing(r.briefing);$('review-assumptions').replaceChildren(...r.assumptions.map(t=>el('p',t)));
}
function drawReferenceTrend(projections,balance){
 const host=$('review-trend-chart');host.replaceChildren();const values=[Number(balance),...projections.map(p=>p.projected_balance)];
 const min=Math.min(0,...values),max=Math.max(1,...values),ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 440 180');svg.setAttribute('role','img');svg.setAttribute('aria-label','Reference balance projection: latest balance, 30, 60 and 90 days');
 const line=document.createElementNS(ns,'polyline');line.setAttribute('points',values.map((v,i)=>(30+i*125)+','+(135-(v-min)/(max-min)*110)).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke','#c2410c');line.setAttribute('stroke-width','3');svg.append(line);
 values.forEach((v,i)=>{const label=document.createElementNS(ns,'text');label.setAttribute('x',String(15+i*125));label.setAttribute('y','164');label.setAttribute('font-size','11');label.textContent=['Latest','30 days','60 days','90 days'][i];svg.append(label);});host.append(svg);
}
const presets=[['LAID_OFF_EI','Job loss: EI 55%'],['FURNACE_REPAIR','Emergency repair: one month of spending'],['LAID_OFF_AND_BILLS_UP','Double shock: EI 55% + bills 15%'],['INFLATION_STAGNATION','Cost of living: income −10%, bills +25%']];
for(const [id,title] of presets)$('review-presets').append(button(title,async()=>{if(reviewAccount===null)throw Error('Find a source account first.');await loadReferenceReview(reviewAccount,{scenario_id:id});}));
$('review-scenario').onsubmit=e=>{e.preventDefault();action(e.currentTarget.querySelector('button'),async()=>{
 const values=Object.fromEntries(new FormData($('review-scenario')));await loadReferenceReview(reviewAccount,{scenario_id:'CUSTOM',income_reduction_pct:Number(values.income_reduction_pct)/100,bills_increase_pct:Number(values.bills_increase_pct)/100,one_off_costs:Number(values.one_off_costs),shock_duration_months:Number(values.shock_duration_months)});
});};
for(const slider of $('review-scenario').querySelectorAll('input[type=range]')){
 slider.oninput=()=>{$('review-scenario').elements[slider.dataset.field].value=slider.value;};
 slider.onchange=()=>{$('review-scenario').requestSubmit();};
}
$('review-fraud').onsubmit=e=>{e.preventDefault();action(e.currentTarget.querySelector('button'),async()=>{
 const f=$('review-fraud').elements,id=reviewAccount,version=reviewVersion;
 const body={amount:Number(f.amount.value),merchant_name:f.merchant_name.value,category:f.category.value,
  is_new_store:f.is_new_store.checked,is_outside_normal_location:f.is_outside_normal_location.checked,is_outside_budget:f.is_outside_budget.checked,vacation_mode:f.vacation_mode.checked,vacation_location:f.vacation_location.value||null,
  recent_browsing_category:f.browsing_match.checked?f.category.value:null,chargebacks_count:f.chargebacks_count.value===''?null:Number(f.chargebacks_count.value)};
 const result=await api('source-review/'+id+'/fraud','POST',body);if(version!==reviewVersion||id!==reviewAccount)return;
 reviewFields('review-fraud-score',{anomaly_score:result.anomaly_score,threshold:result.flag_threshold,simulation_result:result.is_flagged?'Needs review':'Below review threshold',...result.metrics,vacation_mode:result.vacation_mode_active,assumptions:result.assumptions});
 table('review-fraud-factors',result.scoring_breakdown,[['Factor','factor'],['Adjustment','delta'],['Reason','detail']]);
});};
$('review-summary').onclick=()=>action($('review-summary'),async()=>{
 const id=reviewAccount,version=reviewVersion,result=await api('source-review/'+id+'/briefing','POST',{...reviewScenario,allow_external_processing:$('review-external-consent').checked});
 if(id===reviewAccount&&version===reviewVersion){reviewData.briefing=result;renderReviewBriefing(result);}
});
function stopReviewSpeech(){if('speechSynthesis' in window)window.speechSynthesis.cancel();$('review-audio').querySelectorAll('audio').forEach(a=>a.pause());}
$('review-speak').onclick=()=>action($('review-speak'),async()=>{if(!reviewData)throw Error('Select an account first.');if(!('speechSynthesis' in window))throw Error('This browser does not support speech. Use ElevenLabs audio if configured.');stopReviewSpeech();const speech=new SpeechSynthesisUtterance(reviewData.briefing.summary_text);speech.rate=1;speech.pitch=1;window.speechSynthesis.speak(speech);});
$('review-stop').onclick=stopReviewSpeech;
$('review-cloud-audio').onclick=()=>action($('review-cloud-audio'),async()=>{
 if(!$('review-external-consent').checked)throw Error('Enable external processing before requesting ElevenLabs audio.');
 const id=reviewAccount,version=reviewVersion,blob=await api('source-review/'+id+'/audio','POST',{...reviewScenario,allow_external_processing:true,profile:'professional',summary_text:reviewData.briefing.summary_text},true);
 if(id!==reviewAccount||version!==reviewVersion)return;
 if(reviewAudioUrl)URL.revokeObjectURL(reviewAudioUrl);reviewAudioUrl=URL.createObjectURL(blob);const audio=el('audio');audio.controls=true;audio.src=reviewAudioUrl;$('review-audio').replaceChildren(audio);
});
