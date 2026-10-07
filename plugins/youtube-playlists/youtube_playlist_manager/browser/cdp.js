// Optional CDP serialization. No browser identity or YouTube policy.
module.exports = function makeBoundedSender({rawSend, owned, gzip, sha256, randomId, event,
  now = () => performance.now()}) {
  // Serialization only. Never repeat evaluation after a failed/uncertain send.
  const inputLimit = 131072;
  const outputLimit = 65536;
  const digestExpression = `async(text)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,'0')).join('')`;
  function guard() {
    const {token, url} = owned();
    return `if(!(()=>{const expected=new URL(${JSON.stringify(url)}), actual=new URL(location.href);return actual.origin===expected.origin&&actual.pathname===expected.pathname&&[...new Set(expected.searchParams.keys())].every(k=>JSON.stringify(actual.searchParams.getAll(k))===JSON.stringify(expected.searchParams.getAll(k)));})()||window.__ytpmPageIdentity!==${JSON.stringify(token)})throw Error('Owned page changed');`;
  }
  function capture(body, key) {
    return `(async()=>{${guard()} const value=await (${body});
      if(typeof value!=='string'||value.length<=${outputLimit})return {inline:true,value};
      if(Object.hasOwn(window,${JSON.stringify(key)}))throw Error('Output buffer collision');
      Object.defineProperty(window,${JSON.stringify(key)},{value:{kind:'output',text:value},configurable:true});
      return {inline:false,length:value.length,sha256:await (${digestExpression})(value)};
    })()`;
  }
  return async function sendBounded(expression, timeoutSeconds=60, ensureActive = async () => {}) {
    if (!Number.isFinite(timeoutSeconds) || timeoutSeconds <= 0) throw Error('Invalid CDP evaluation timeout');
    const deadline = now() + timeoutSeconds * 1000;
    const remaining = () => {
      const milliseconds = deadline - now();
      if (milliseconds <= 0) throw Error('CDP evaluation deadline exceeded');
      return milliseconds / 1000;
    };
    const send = async source => {
      await ensureActive();
      const result = await rawSend(source, remaining());
      await ensureActive();
      remaining();
      return result;
    };
    const key = '__ytpmPageTransfer_' + randomId().replaceAll('-', '');
    const sourceHash = sha256(expression);
    const started = Date.now();
    let inputChunks = 0;
    let body = expression;
    if (Buffer.byteLength(expression, 'utf8') > inputLimit) {
      const base64 = gzip(Buffer.from(expression, 'utf8')).toString('base64');
      const created = await send(`(()=>{${guard()}if(Object.hasOwn(window,${JSON.stringify(key)}))throw Error('Input buffer collision');Object.defineProperty(window,${JSON.stringify(key)},{value:{kind:'input',chunks:[],length:0},configurable:true});return {created:true};})()`);
      if (created.created !== true) throw Error('Input buffer not created');
      for (let offset = 0; offset < base64.length; offset += inputLimit) {
        const chunk = base64.slice(offset, offset + inputLimit);
        const ack = await send(`(()=>{${guard()}const b=window[${JSON.stringify(key)}];if(b?.kind!=='input'||b.length!==${offset})throw Error('Input offset mismatch');b.chunks.push(${JSON.stringify(chunk)});b.length+=${chunk.length};return {length:b.length};})()`);
        if (ack.length !== offset + chunk.length) throw Error('Input chunk acknowledgement mismatch');
        inputChunks++;
      }
      const prepared = await send(`(async()=>{${guard()}const b=window[${JSON.stringify(key)}];
        if(b?.kind!=='input'||b.length!==${base64.length})throw Error('Input length mismatch');
        const bytes=Uint8Array.from(atob(b.chunks.join('')),c=>c.charCodeAt(0));
        const source=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
        if(await (${digestExpression})(source)!==${JSON.stringify(sourceHash)})throw Error('Source digest mismatch');
        b.kind='prepared';b.text=source;delete b.chunks;
        return {prepared:true,sha256:${JSON.stringify(sourceHash)}};
      })()`);
      if (prepared.prepared !== true || prepared.sha256 !== sourceHash) throw Error('Source preparation failed');
      // Execute in a fresh synchronous inspector call after async preparation.
      body = `(()=>{${guard()}const b=window[${JSON.stringify(key)}];
        if(b?.kind!=='prepared')throw Error('Prepared source missing');
        const source=b.text;delete window[${JSON.stringify(key)}];return (0,eval)(source);
      })()`;
    }
    // This call is the one and only execution of the original source.
    const envelope = await send(capture(body, key));
    let value;
    let outputChunks = 0;
    if (envelope.inline === true) {
      value = envelope.value;
    } else {
      if (envelope.inline !== false || !Number.isInteger(envelope.length) || envelope.length < 1 || !/^[a-f0-9]{64}$/.test(envelope.sha256)) throw Error('Invalid output envelope');
      const chunks = [];
      for (let offset = 0; offset < envelope.length; offset += outputLimit) {
        const response = await send(`(()=>{${guard()}const b=window[${JSON.stringify(key)}];if(b?.kind!=='output'||b.text.length!==${envelope.length})throw Error('Output buffer changed');return {offset:${offset},text:b.text.slice(${offset},${offset + outputLimit})};})()`);
        if (response.offset !== offset || typeof response.text !== 'string' || response.text.length !== Math.min(outputLimit, envelope.length - offset)) throw Error('Output chunk mismatch');
        chunks.push(response.text);
        outputChunks++;
      }
      value = chunks.join('');
      if (value.length !== envelope.length || sha256(value) !== envelope.sha256) throw Error('Output digest mismatch');
      const released = await send(`(()=>{${guard()}delete window[${JSON.stringify(key)}];return {absent:!Object.hasOwn(window,${JSON.stringify(key)})};})()`);
      if (released.absent !== true) throw Error('Output buffer cleanup failed');
    }
    if (inputChunks || outputChunks) await event({kind:'bounded_transfer',source_bytes:Buffer.byteLength(expression,'utf8'),source_sha256:sourceHash,input_chunks:inputChunks,output_chunks:outputChunks,output_characters:typeof value==='string'?value.length:null,duration_ms:Date.now()-started,digests_verified:true});
    return value;
  };
};
