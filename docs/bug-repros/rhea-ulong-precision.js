/**
 * Rhea Bug: 64-bit integer precision loss / RangeError
 *
 * JavaScript Number is IEEE 754 double (safe integer range: -(2^53-1) to 2^53-1).
 * Rhea uses Number for ulong and long, so values outside this range are silently
 * rounded or throw RangeError.
 *
 * The library should use BigInt for 64-bit integer types.
 *
 * Tested with: rhea 3.0.3
 * Requires: Artemis broker on localhost:5672 (user: artemis, pass: artemis)
 *
 * Run: node rhea-ulong-precision.js
 */

const rhea = require('rhea');
const container = rhea.create_container();

const ULONG_MAX = BigInt('18446744073709551615');
const SAFE_MAX = BigInt(Number.MAX_SAFE_INTEGER);

console.log(`Number.MAX_SAFE_INTEGER: ${SAFE_MAX}`);
console.log(`ULONG_MAX:              ${ULONG_MAX}`);
console.log(`Can Number hold ULONG_MAX? ${Number(ULONG_MAX) === Number(ULONG_MAX - 1n) ? 'NO (precision loss)' : 'yes'}`);

// Demonstrate precision loss with a value just above MAX_SAFE_INTEGER
const testValue = Number(SAFE_MAX) + 10;
const testValue2 = Number(SAFE_MAX) + 11;
console.log(`\n${SAFE_MAX + 10n} === ${SAFE_MAX + 11n}?`);
console.log(`In JS Number: ${testValue} === ${testValue2}? ${testValue === testValue2 ? 'YES — precision lost!' : 'no'}`);

// Demonstrate with actual AMQP send
container.on('sendable', function(context) {
    try {
        // This value exceeds safe integer range
        const val = 18446744073709551615;
        console.log(`\nAttempting to send ulong: 18446744073709551615`);
        console.log(`JS Number representation: ${val}`);
        console.log(`Already corrupted before send: ${val !== 18446744073709551615 ? 'YES' : 'no'}`);

        context.sender.send({ body: rhea.types.wrap_ulong(val) });
        console.log('Sent (but value was already corrupted by JS Number)');
    } catch(e) {
        console.log(`RangeError on send: ${e.message}`);
    }
    context.sender.close();
    context.connection.close();
});

container.connect({
    host: 'localhost',
    port: 5672,
    username: 'artemis',
    password: 'artemis'
}).open_sender('test.bug.rhea-precision');
