// Rebuild the logical inventory from the preserved user function list.
const fs = require('node:fs');
const source = fs.readFileSync('docs/FUNCTION_LIST.md', 'utf8');
const areas = [
  ['Shock mediation', 'app/engines/service.py', 'create_shock, generate_offers, repayment_capacity, decide', 'tests/integration/test_financial_api.py'],
  ['Predictive planning', 'app/engines/calculations.py', 'forecast, regression, occurrences', 'tests/unit/test_financial_rules.py'],
  ['Behavioral fraud / vacation', 'app/engines/service.py', 'ingest, vacation_view, associate_trip; calculations.anomaly', 'tests/integration/test_financial_api.py'],
  ['Subscriptions', 'app/engines/calculations.py', 'detect_subscriptions, subscription_advice; service.refresh', 'tests/unit/test_financial_rules.py'],
  ['Inflation', 'app/engines/calculations.py', 'inflation; integrations.providers.fetch_cpi', 'tests/unit/test_financial_rules.py'],
  ['Expense pyramid', 'app/engines/calculations.py', 'pyramid, tier', 'tests/unit/test_financial_rules.py'],
  ['Gemini summaries', 'app/api/endpoints/finance.py', 'create_summary, shock_scenario; integrations/gemini/client.py', 'tests/integration/test_summary_workflow.py'],
  ['Voice', 'app/api/endpoints/finance.py', 'generate_audio, get_audio; integrations.providers.speech; web/app.js', 'tests/integration/test_summary_workflow.py'],
  ['Platform', 'app/engines/platform.py', 'core/dependencies.py, core/security.py, core/metrics.py, engines/jobs.py, api/middleware', 'tests/integration/test_platform.py'],
];
const notes = {
  checkCreditEligibility: 'Adapter implemented; real underwriting and eligibility require a configured provider.',
  routeCreditApplication: 'Provider routing implemented; real product access requires a configured provider.',
  retrieveBrowsingContext: 'Consent-gated adapter implemented; live browsing provider unverified.',
  triggerTransactionVerification: 'Local review notification; no bank transaction hold or challenge integration.',
  retrieveCPIData: 'Statistics Canada client implemented; this audit uses contract tests, not a live network probe.',
  generateContingencyPlan: 'SummaryInput.scenario adds verified hypothetical balances/runway and required contingency steps; Gemini selects verified facts. Live model success unverified.',
  generateShockScenarioAnalysis: 'POST /summaries accepts a scenario amount/due_date, preserves baseline and scenario metrics, and includes explicit hypothetical assumptions. Live model success unverified.',
  encryptSensitiveFinancialData: 'DEPLOYMENT GAP: financial database fields are plaintext at the application layer. Password hashing and signed JWTs do not encrypt financial records. Configure database/disk encryption and TLS before deployment.',
  manageDataRetention: 'Configurable summary/audio retention plus owner deletion implemented; ledger, consent, and audit retention remain operator policy.',
  publishFinancialEvent: 'Durable local audit-table outbox for transaction imports; no external message broker.',
  consumeFinancialEvent: 'Worker consumes local events atomically with forecast refresh; no independently deployed consumers.',
  generateSystemMetrics: 'Admin-only GET /api/v1/system/metrics; process-local request counters, durations, and uptime.',
  storeAudioAsset: 'Owner-scoped database storage; optional generated-summary retention includes audio.',
};
const external = new Set(['analyzeFinancialHealth','generateSpendingSummary','forwardSummaryToTTS','generateSpeechAudio','generateMP3File','sendUpcomingBillingAlert','sendShockNotification','manageNotificationDelivery','manageExternalAPIConnections']);
let index = -1;
const rows = [];
for (const line of source.split(/\r?\n/)) {
  if (/^## [1-9]\./.test(line)) index++;
  const match = line.match(/^\d+\. `([A-Za-z][A-Za-z0-9]+)\(\)`/);
  if (!match) continue;
  const name = match[1], area = areas[index];
  if (!area) throw new Error('Unrecognized inventory section');
  let note = notes[name] || (external.has(name) ? 'Local implementation and failure handling exist; credentialed external success remains unverified.' : 'Implemented within the grouped operations; see source and grouped behavioral tests.');
  let status = name === 'encryptSensitiveFinancialData' ? 'DEPLOYMENT GAP' : (notes[name] || external.has(name)) ? 'QUALIFIED' : 'LOCAL IMPLEMENTATION';
  rows.push(`| ${rows.length+1} | ${area[0]} | \`${name}()\` | ${status} | [source](../${area[1]}) — ${area[2]}; [tests](../${area[3]}) | ${note} |`);
}
if (rows.length !== 163) throw new Error(`Expected 163 functions, found ${rows.length}`);
fs.writeFileSync('docs/FUNCTION_COVERAGE.md', `# Function inventory review\n\nReviewed against [the supplied list](FUNCTION_LIST.md). There are **163 logical responsibilities**, implemented as grouped operations rather than separate camelCase functions or services. This mapping is a review index, not proof of 163 individually tested methods. Existing behavioral tests cover groups; see [the earlier detailed checklist](FINAL_CHECKLIST.md) for additional limitations.\n\nLOCAL IMPLEMENTATION means local behavior exists. QUALIFIED includes integration, scope, or live-verification limits. DEPLOYMENT GAP is explicitly incomplete. The project cannot be called fully production-complete while these gaps remain.\n\n| # | Area | Requested function | Review status | Implementation / grouped evidence | Scope or limitation |\n| --- | --- | --- | --- | --- | --- |\n${rows.join('\n')}\n`);
console.log(`Mapped ${rows.length} logical responsibilities to docs/FUNCTION_COVERAGE.md`);
