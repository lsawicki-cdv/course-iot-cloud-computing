// Calls the handler with a function URL event, like Lambda does (run: node test-locally.mjs)
import { handler } from './index.mjs';

const event = { rawPath: '/', queryStringParameters: { name: 'AWS' } };
console.log(await handler(event));
