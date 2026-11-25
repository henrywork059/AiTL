const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');

// Compile the actual source in memory using the project's TypeScript dependency.
const previousLoader = Module._extensions['.ts'];
Module._extensions['.ts'] = (module, filename) => {
  const result = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2021 },
  });
  module._compile(result.outputText, filename);
};
const { createPollingScope, runScopedSerialTask } = require('../src/lib/pollingScope.ts');
const { requestJson, requestJsonStrict, ApiRequestError } = require('../src/lib/apiClient.ts');
if (previousLoader) Module._extensions['.ts'] = previousLoader;
else delete Module._extensions['.ts'];

async function main() {
  const inFlight = { current: null };
  const old = createPollingScope();
  const latest = createPollingScope();
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const published = [];
  const errors = [];
  let starts = 0;
  const slow = runScopedSerialTask(inFlight, old, async context => {
    starts++;
    await gate;
    if (context.isCurrent()) published.push('old');
    throw new Error('retired failure');
  }, error => errors.push(error));
  await Promise.resolve();
  assert.equal(starts, 1);
  old.retire();
  assert.equal(old.signal.aborted, true);
  assert.equal(runScopedSerialTask(inFlight, latest, async () => { starts++; }, () => {}), slow);
  release();
  await slow;
  assert.deepEqual(published, []);
  assert.deepEqual(errors, []);
  await runScopedSerialTask(inFlight, latest, async context => {
    starts++;
    if (context.isCurrent()) published.push('latest');
  }, error => errors.push(error));
  assert.equal(starts, 2);
  assert.deepEqual(published, ['latest']);
  assert.equal(inFlight.current, null);
  await runScopedSerialTask(inFlight, latest, async () => { throw new Error('current'); }, error => errors.push(error.message));
  assert.deepEqual(errors, ['current']);
  const unmounted = createPollingScope();
  unmounted.retire();
  await runScopedSerialTask(inFlight, unmounted, async () => { throw new Error('must not start'); }, error => errors.push(error));
  assert.deepEqual(errors, ['current']);

  const originalFetch = global.fetch;
  const originalError = console.error;
  const originalInfo = console.info;
  const logs = [];
  console.error = (...args) => logs.push(args);
  console.info = () => {};
  try {
    global.fetch = async () => new Response(JSON.stringify({ ok: true, data: { value: 7 }, meta: { request_id: 'r1' } }));
    assert.deepEqual(await requestJsonStrict('/success'), { value: 7 });
    global.fetch = async () => new Response(JSON.stringify({ ok: false, error: { code: 'X', message: 'failed' }, meta: { request_id: 'r2' } }), { status: 409 });
    await assert.rejects(requestJsonStrict('/error'), error => error instanceof ApiRequestError && error.code === 'X' && error.requestId === 'r2');
    assert.equal(await requestJson('/fallback', 99), 99);
    global.fetch = async () => new Response('not json', { status: 502 });
    await assert.rejects(requestJsonStrict('/invalid'), /without a JSON response/);
    const baselineLogs = logs.length;
    const controller = new AbortController();
    let bodyStarted;
    const bodyGate = new Promise(resolve => { bodyStarted = resolve; });
    global.fetch = async (_url, options) => {
      assert.equal(options.signal, controller.signal);
      return { ok: true, status: 200, json: () => new Promise((_resolve, reject) => {
        options.signal.addEventListener('abort', () => reject(options.signal.reason), { once: true });
        bodyStarted();
      }) };
    };
    const pending = requestJson('/abort-body', 99, { signal: controller.signal });
    await bodyGate;
    controller.abort();
    await assert.rejects(pending, { name: 'AbortError' });
    await assert.rejects(requestJson('/pre-aborted', 99, { signal: controller.signal }), { name: 'AbortError' });
    assert.equal(logs.length, baselineLogs);
    const late = new AbortController();
    global.fetch = async () => ({ ok: true, status: 200, json: async () => { late.abort(); return { ok: true, data: 3 }; } });
    await assert.rejects(requestJsonStrict('/late', { signal: late.signal }), { name: 'AbortError' });
    assert.equal(logs.length, baselineLogs);
  } finally {
    global.fetch = originalFetch;
    console.error = originalError;
    console.info = originalInfo;
  }
  console.log('[PASS] scoped single-flight, retirement, stale errors, API envelopes, fallback and abort semantics');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
