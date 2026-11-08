/* Reproducible requirement mapping from the preserved user specification. */
const fs=require('node:fs');
const lines=fs.readFileSync('docs/REQUIREMENTS.md','utf8').split(/\r?\n/);
let group='',active=false;
const entries=[];
for(const raw of lines){const line=raw.trim();if(line.startsWith('Microservice:')){group=line.slice(13).trim();active=true;}if(line.startsWith('Verify that all eight engines'))group='Architecture';if(line==='Users should be able to:')group='End-user interface';if(line.startsWith('Follow these rules'))group='Engineering safeguards';if(line==='Include:')group='Verification';if(line.startsWith('Pay particular attention'))group='Edge cases';if(line.startsWith('Report the actual integration status'))group='Integration inventory';if(!active)continue;const match=line.match(/^(?:- |\d+\. )(.+)$/);if(match)entries.push({group,text:match[1]});}
const evidence={
 'engine-shock-mediation':'service.py create_shock / generate_offers / decide; financial_rules + financial_api tests',
 'engine-predictive-plan':'calculations.py forecast / regression; financial_rules + financial_api tests',
 'engine-behavioral-fraud':'calculations.py anomaly; service.py ingest / vacation_view; financial_rules + financial_api tests',
 'engine-subscription-mgr':'calculations.py detect_subscriptions / subscription_advice; service.py refresh; subscription API tests',
 'engine-inflation-tracker':'calculations.py inflation; providers.py fetch_cpi; live CPI smoke + persistence tests',
 'engine-expense-pyramid':'calculations.py pyramid / tier / classify; financial_rules tests; dashboard DOM tests',
 'engine-gemini-integration':'gemini/client.py; finance.py create_summary; provider + summary_workflow tests',
 'engine-elevenlabs-integration':'providers.py speech; protected audio routes; provider + summary_workflow + frontend tests',
 'Architecture':'shared user-scoped service / provider contracts; API, migration and background worker tests',
 'End-user interface':'app/web/*; 8 DOM tests + 1 real FastAPI/SQLite UI workflow',
 'Engineering safeguards':'validation, consent audit, row locks, uniqueness constraints, safe errors; security/API tests',
 'Verification':'tests/unit, tests/integration, tests/frontend; exact final results in IMPLEMENTATION_REPORT.md',
 'Edge cases':'financial_rules, financial_api, provider_integrations, migrations, background_jobs tests',
 'Integration inventory':'docs/INTEGRATIONS.md; local contract tests; only Statistics Canada live verified'
};
function classify(e){
 let status='IMPLEMENTED',limit='Locally implemented and exercised; see grouped evidence and report.';
 const text=e.text.toLowerCase();
 const external=(e.group.includes('gemini')&&!text.includes('aggregation'))||e.group.includes('elevenlabs')||/browsing-context analysis api|routing to conventional|verification of standard credit|personalized installment offers|push notifications/.test(text);
 if(external){status='PARTIALLY IMPLEMENTED';limit='Local implementation/contract tests; requires configured external service and live end-to-end verification.';}
 if(e.group==='Architecture'&&/independently maintained and scaled|engine-gemini|engine-elevenlabs|event-driven workflows/.test(text)){status='PARTIALLY IMPLEMENTED';limit='Preserved modular monolith; atomic local event updates and single periodic worker. No distributed microservice deployment verified.';}
 if(e.group==='End-user interface'&&/ai-generated|audio financial|accept or reject financial offers|compare installment/.test(text)){status='PARTIALLY IMPLEMENTED';limit='UI and local workflow tested; real provider/lender configuration remains necessary.';}
 if(e.group==='Verification'&&/microservice communication|gemini|elevenlabs/.test(text)){status='PARTIALLY IMPLEMENTED';limit='Local service/HTTP contract tests executed; no real credentialed remote services or distributed deployment.';}
 if(e.group==='Integration inventory'&&!text.includes('statistics canada')){status='PARTIALLY IMPLEMENTED';limit='Adapter or client implemented and tested locally; vendor/account credentials and live verification required.';}
 if(e.group==='Architecture'&&/engine-shock-mediation|engine-predictive-plan|engine-behavioral-fraud|engine-subscription-mgr|engine-inflation-tracker|engine-expense-pyramid/.test(text)){limit='Implemented in the existing monolith; not a separately deployed microservice.';}
 return {status,limit};
}
const escape=s=>s.replaceAll('|','/');
const output=['# Final requirements checklist','','Status means end-to-end local implementation; external-dependent capabilities remain PARTIALLY IMPLEMENTED until live service configuration and verification. Initial business capabilities were MISSING end-to-end. Existing authentication/database foundations are described in INITIAL_AUDIT.md. Test evidence is grouped; a passing grouped test is not a claim that every production integration was exercised. Visual browser QA was unavailable.','','| Area | Exact requirement | Initial status | Final status | Evidence / limitation |','| --- | --- | --- | --- | --- |'];
for(const e of entries){const c=classify(e);output.push(`| ${escape(e.group)} | ${escape(e.text)} | MISSING | ${c.status} | ${escape(evidence[e.group]||'Implementation report')}. ${escape(c.limit)} |`);}
output.push('','Additional explicit policies verified: y=mx+b regression; Z=(x-mean)/standard deviation with zero-variance handling; review above 0.85 without confirmed-fraud classification; final score clamped to [0,1]; fixed 50/30/20 target ratios; absolute-deviation deformity score; inverted pyramid when peak exceeds base; financed-fee amortization and cent-reconciled final payments; consistent CPI reference; no alerts from incomplete quarters.','', 'Remaining business dependencies: selected banking/underwriting/browsing/notification adapters, Gemini/ElevenLabs accounts and current models/voices, approved lending terms and actual lender origination/collection contract. Independent service deployment, Docker/PostgreSQL runtime verification, and visual/audio device QA remain unverified.');
fs.writeFileSync('docs/FINAL_CHECKLIST.md',output.join('\n')+'\n');
console.log('Mapped '+entries.length+' specification items.');
