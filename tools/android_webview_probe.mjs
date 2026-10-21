// Inspect only the ALLMA WebView forwarded through an authorized ADB socket.
const port = Number(process.argv[2]);
const expression = process.argv[3];
if (!Number.isInteger(port) || !expression) throw new Error('port and expression required');
const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
const target = tabs.find(tab => tab.type === 'page' && (tab.url.includes('org.allma.allma_prime') || tab.url === 'https://app.allma/' || tab.url === 'about:blank'));
if (!target) throw new Error('No ALLMA page on the forwarded socket');
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, {once:true});
    socket.addEventListener('error', reject, {once:true});
});
const result = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('DevTools timeout')), 10000);
    socket.addEventListener('message', event => {
        const message = JSON.parse(event.data);
        if (message.id !== 1) return;
        clearTimeout(timer);
        if (message.error || message.result?.exceptionDetails) reject(new Error(JSON.stringify(message.error || message.result.exceptionDetails)));
        else resolve(message.result.result.value);
    });
    socket.send(JSON.stringify({id:1,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}));
});
console.log(JSON.stringify(result));
socket.close();
