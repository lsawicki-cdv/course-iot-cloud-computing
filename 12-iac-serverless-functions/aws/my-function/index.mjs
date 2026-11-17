// The AWS Lambda version of the "HTTP trigger" function that `func new` creates in the Azure version
export const handler = async (event) => {
    console.log(`Http function processed request for url "${event.rawPath}"`);

    // The request body arrives base64-encoded when it isn't text
    const body = event.body && event.isBase64Encoded
        ? Buffer.from(event.body, 'base64').toString()
        : event.body;
    const name = event.queryStringParameters?.name || body || 'world';

    return {
        statusCode: 200,
        headers: { 'Content-Type': 'text/plain' },
        body: `Hello, ${name}!`
    };
};
