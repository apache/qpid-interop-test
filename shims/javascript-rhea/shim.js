#!/usr/bin/env node
/*
 * QIT JavaScript/Rhea AMQP Shim
 *
 * Uses Rhea library for AMQP 1.0 communication
 */

'use strict';

const rhea = require('rhea');
const { v4: uuidv4 } = require('uuid');

// Parse command line arguments
function parseArgs() {
    const args = process.argv.slice(2);

    if (args.length < 2) {
        console.error('Usage: shim.js <command> [options]');
        console.error('Commands: send, receive');
        process.exit(1);
    }

    const command = args[0];
    const options = {};
    const flags = [];

    for (let i = 1; i < args.length; i++) {
        if (args[i].startsWith('--')) {
            const key = args[i].replace('--', '');
            // Check if this is a flag (no value) or an option (has value)
            if (i + 1 < args.length && !args[i + 1].startsWith('--')) {
                options[key] = args[i + 1];
                i++; // Skip the value
            } else {
                // It's a flag
                flags.push(key);
            }
        }
    }

    // Add flags as boolean options
    flags.forEach(flag => {
        options[flag] = true;
    });

    return { command, options };
}

// JMS message type mapping
function getJmsMessageType(amqpType) {
    // JMS message type constants (from Qpid JMS Client)
    const JMS_MESSAGE = 0;        // Empty message
    const JMS_MAP_MESSAGE = 2;    // Map
    const JMS_BYTES_MESSAGE = 3;  // Binary data
    const JMS_STREAM_MESSAGE = 4; // List/stream
    const JMS_TEXT_MESSAGE = 5;   // String/text

    // Map AMQP types to JMS message types
    if (amqpType === 'string') {
        return JMS_TEXT_MESSAGE;
    } else if (amqpType === 'binary') {
        return JMS_BYTES_MESSAGE;
    } else if (amqpType === 'null') {
        return JMS_MESSAGE;
    } else if (amqpType === 'map') {
        return JMS_MAP_MESSAGE;
    } else if (amqpType === 'list') {
        return JMS_STREAM_MESSAGE;
    }

    return null;
}

// Decode JMS message based on message type annotation
function decodeJmsMessage(body, jmsMsgType) {
    // JMS message type constants
    const JMS_MESSAGE = 0;
    const JMS_TEXT_MESSAGE = 5;
    const JMS_BYTES_MESSAGE = 3;
    const JMS_MAP_MESSAGE = 2;
    const JMS_STREAM_MESSAGE = 4;

    if (jmsMsgType === JMS_TEXT_MESSAGE) {
        // TextMessage: body is string in AmqpValue section
        return {
            type: 'text',  // Use 'text' to match JMS shim output
            value: body !== null && body !== undefined ? String(body) : null
        };
    } else if (jmsMsgType === JMS_BYTES_MESSAGE) {
        // BytesMessage: body is binary in Data section
        // Rhea wraps Data sections in Section objects — extract content first
        const data = (body !== null && body !== undefined && body.content !== undefined) ? body.content : body;
        if (data === null || data === undefined) {
            return { type: 'bytes', value: '' };
        }
        const buf = Buffer.isBuffer(data) ? data : Buffer.from(data);
        return { type: 'bytes', value: buf.toString('hex') };
    } else if (jmsMsgType === JMS_MESSAGE) {
        // Empty message
        return { type: 'null', value: null };
    } else if (jmsMsgType === JMS_MAP_MESSAGE) {
        if (body && typeof body === 'object') {
            const keys = Object.keys(body);
            if (keys.length > 0) {
                return TypeDecoder.decode(body[keys[0]]);
            }
        }
        return { type: 'none', value: null };
    } else if (jmsMsgType === JMS_STREAM_MESSAGE) {
        if (Array.isArray(body) && body.length > 0) {
            return TypeDecoder.decode(body[0]);
        }
        return { type: 'none', value: null };
    } else {
        // Unknown JMS type, fall back to regular AMQP decoding
        return TypeDecoder.decode(body);
    }
}

// Type encoders - convert JSON test values to AMQP types
class TypeEncoder {
    static encode(amqpType, testValue) {
        const value = typeof testValue === 'object' && testValue !== null && testValue.value !== undefined
            ? testValue.value
            : testValue;

        switch (amqpType) {
            case 'null':
                return null;

            case 'boolean':
                return value === true || value === 'True';

            case 'ubyte':
                return rhea.types.wrap_ubyte(parseInt(value));

            case 'ushort':
                return rhea.types.wrap_ushort(parseInt(value));

            case 'uint':
                return rhea.types.wrap_uint(parseInt(value));

            case 'ulong':
                return rhea.types.wrap_ulong(parseInt(value));

            case 'byte':
                return rhea.types.wrap_byte(parseInt(value));

            case 'short':
                return rhea.types.wrap_short(parseInt(value));

            case 'int':
                return rhea.types.wrap_int(parseInt(value));

            case 'long':
                return rhea.types.wrap_long(parseInt(value));

            case 'float':
                // Handle hex representation
                if (typeof value === 'string' && value.startsWith('0x')) {
                    const intVal = parseInt(value, 16);
                    const buffer = Buffer.allocUnsafe(4);
                    buffer.writeUInt32BE(intVal, 0);
                    return rhea.types.wrap_float(buffer.readFloatBE(0));
                }
                return rhea.types.wrap_float(parseFloat(value));

            case 'double':
                // Handle hex representation
                if (typeof value === 'string' && value.startsWith('0x')) {
                    const bigintVal = BigInt(value);
                    const buffer = Buffer.allocUnsafe(8);
                    buffer.writeBigUInt64BE(bigintVal, 0);
                    return rhea.types.wrap_double(buffer.readDoubleBE(0));
                }
                return rhea.types.wrap_double(parseFloat(value));

            case 'char':
                const codePoint = parseInt(value);
                return new rhea.types.CharUTF32(String.fromCodePoint(codePoint));

            case 'timestamp':
                return rhea.types.wrap_timestamp(new Date(parseInt(value)));

            case 'uuid':
                return new rhea.types.Uuid(Buffer.from(value.replace(/-/g, ''), 'hex'));

            case 'binary':
                return rhea.types.wrap_binary(Buffer.from(value, 'hex'));

            case 'string':
                return rhea.types.wrap_string(String(value));

            case 'symbol':
                return rhea.types.wrap_symbol(String(value));

            default:
                throw new Error(`Unknown AMQP type: ${amqpType}`);
        }
    }
}

// Type decoders - convert AMQP types to JSON
class TypeDecoder {
    static decode(value) {
        if (value === null || value === undefined) {
            return { type: 'null', value: null };
        }

        // Extract the raw value if this is a Typed object
        const rawValue = (value && value.type && value.value !== undefined) ? value.value : value;

        // Get type descriptor
        const typeName = TypeDecoder.inferType(value);

        switch (typeName) {
            case 'boolean':
                return { type: 'boolean', value: Boolean(rawValue) };

            case 'ubyte':
            case 'ushort':
            case 'uint':
            case 'byte':
            case 'short':
            case 'int':
                return { type: typeName, value: Number(rawValue) };

            case 'ulong':
            case 'long':
                // Handle as number (may lose precision for very large values)
                return { type: typeName, value: Number(rawValue) };

            case 'float':
                // Return as hex for exact comparison
                const floatBuffer = Buffer.allocUnsafe(4);
                floatBuffer.writeFloatBE(rawValue, 0);
                return {
                    type: 'float',
                    value: '0x' + floatBuffer.readUInt32BE(0).toString(16).padStart(8, '0')
                };

            case 'double':
                // Return as hex for exact comparison
                const doubleBuffer = Buffer.allocUnsafe(8);
                doubleBuffer.writeDoubleBE(rawValue, 0);
                return {
                    type: 'double',
                    value: '0x' + doubleBuffer.readBigUInt64BE(0).toString(16).padStart(16, '0')
                };

            case 'char':
                return { type: 'char', value: rawValue.codePointAt ? rawValue.codePointAt(0) : rawValue };

            case 'timestamp':
                return { type: 'timestamp', value: rawValue.getTime ? rawValue.getTime() : rawValue };

            case 'uuid':
                // Convert Buffer to UUID string
                const hex = rawValue.toString('hex');
                const uuidStr = [
                    hex.slice(0, 8),
                    hex.slice(8, 12),
                    hex.slice(12, 16),
                    hex.slice(16, 20),
                    hex.slice(20, 32)
                ].join('-');
                return { type: 'uuid', value: uuidStr };

            case 'binary':
                return { type: 'binary', value: rawValue.toString('hex') };

            case 'string':
                return { type: 'string', value: String(rawValue) };

            case 'symbol':
                return { type: 'symbol', value: String(rawValue) };

            default:
                return { type: 'unknown', value: String(rawValue) };
        }
    }

    static inferType(value) {
        if (value === null || value === undefined) return 'null';

        // Check if this is a Rhea Typed object (captured before unwrapping)
        if (value && value.type && value.type.name) {
            const typeName = value.type.name;
            // Map Rhea type names to AMQP type names
            const nameMap = {
                'Ubyte': 'ubyte',
                'SmallUbyte': 'ubyte',
                'Ushort': 'ushort',
                'SmallUshort': 'ushort',
                'Uint': 'uint',
                'SmallUint': 'uint',
                'Uint0': 'uint',
                'Ulong': 'ulong',
                'SmallUlong': 'ulong',
                'Ulong0': 'ulong',
                'Byte': 'byte',
                'SmallByte': 'byte',
                'Short': 'short',
                'SmallShort': 'short',
                'Int': 'int',
                'SmallInt': 'int',
                'Long': 'long',
                'SmallLong': 'long',
                'Float': 'float',
                'Double': 'double',
                'CharUTF32': 'char',
                'Timestamp': 'timestamp',
                'Uuid': 'uuid',
                'Binary': 'binary',
                'Bin8': 'binary',
                'Bin32': 'binary',
                'String': 'string',
                'Str8': 'string',  // Small string encoding
                'Str32': 'string', // Large string encoding
                'Symbol': 'symbol',
                'Sym8': 'symbol',  // Small symbol encoding
                'Sym32': 'symbol', // Large symbol encoding
                'Boolean': 'boolean',
                'True': 'boolean',
                'False': 'boolean',
                'Null': 'null'
            };
            return nameMap[typeName] || typeName.toLowerCase();
        }

        // Check Rhea wrapped types FIRST before checking JavaScript primitives
        // Rhea types have a valueOf() method and specific type markers
        if (value && typeof value === 'object') {
            // Check for Rhea type descriptor
            if (value.type !== undefined) {
                // Map Rhea type codes to AMQP type names
                const typeMap = {
                    0x56: 'boolean',
                    0x50: 'ubyte',
                    0x60: 'ushort',
                    0x70: 'uint',
                    0x80: 'ulong',
                    0x51: 'byte',
                    0x61: 'short',
                    0x71: 'int',
                    0x81: 'long',
                    0x72: 'float',
                    0x82: 'double',
                    0x73: 'char',
                    0x83: 'timestamp',
                    0x98: 'uuid',
                    0xa0: 'binary',
                    0xb0: 'binary',
                    0xa1: 'string',
                    0xb1: 'string',
                    0xa3: 'symbol',
                    0xb3: 'symbol'
                };
                if (typeMap[value.type]) {
                    return typeMap[value.type];
                }
            }

            // Check constructor name as fallback
            if (value.constructor && value.constructor.name) {
                const name = value.constructor.name.toLowerCase();
                if (name.includes('ubyte')) return 'ubyte';
                if (name.includes('ushort')) return 'ushort';
                if (name.includes('uint')) return 'uint';
                if (name.includes('ulong')) return 'ulong';
                if (name.includes('byte') && !name.includes('ubyte')) return 'byte';
                if (name.includes('short') && !name.includes('ushort')) return 'short';
                if (name.includes('int') && !name.includes('uint')) return 'int';
                if (name.includes('long') && !name.includes('ulong')) return 'long';
                if (name.includes('float')) return 'float';
                if (name.includes('double')) return 'double';
                if (name.includes('char')) return 'char';
                if (name.includes('uuid')) return 'uuid';
                if (name.includes('symbol')) return 'symbol';
            }

            if (value instanceof Date) return 'timestamp';
            if (Buffer.isBuffer(value)) return 'binary';
        }

        // JavaScript primitives (only after checking wrapped types)
        if (typeof value === 'boolean') return 'boolean';
        if (typeof value === 'string') return 'string';
        if (typeof value === 'number') return 'long';  // Default for unwrapped numbers

        return 'unknown';
    }
}

// Sender
function send(options) {
    const { broker, queue, type: amqpType, data, 'jms-mode': jmsMode } = options;
    const testData = JSON.parse(data);

    let sentCount = 0;
    let confirmedCount = 0;
    const total = testData.length;

    // Parse broker URL (e.g., "amqp://localhost:5672" or "localhost:5672")
    const brokerUrl = broker.replace(/^amqp:\/\//, '');
    const [host, port] = brokerUrl.split(':');

    const connection = rhea.connect({
        host: host || 'localhost',
        port: parseInt(port) || 5672,
        reconnect: false
    });

    connection.on('connection_open', (context) => {
        context.connection.open_sender({ target: queue });
    });

    connection.on('sendable', (context) => {
        while (context.sender.sendable() && sentCount < total) {
            const msgData = testData[sentCount];
            let body;

            if (amqpType === 'map') {
                const subType = msgData.type || 'string';
                const key = `${subType}_${String(msgData.index).padStart(3, '0')}`;
                const encodedValue = TypeEncoder.encode(subType, msgData.value);
                const mapObj = {};
                mapObj[key] = encodedValue;
                body = rhea.types.wrap_map(mapObj);
            } else if (amqpType === 'list') {
                const subType = msgData.type || 'string';
                const encodedValue = TypeEncoder.encode(subType, msgData.value);
                body = rhea.types.wrap_list([encodedValue]);
            } else {
                body = TypeEncoder.encode(amqpType, msgData.value);
            }

            if (process.env.QIT_DEBUG) {
                console.error('Sending:', amqpType, msgData.value);
                console.error('Encoded body:', body);
                console.error('Body type:', body && body.constructor && body.constructor.name);
                console.error('Body.type:', body && body.type);
            }

            const message = {
                message_id: msgData.index,
            };
            if (body !== null && body !== undefined) {
                message.body = body;
            }

            // Add JMS annotations if in JMS mode
            if (jmsMode) {
                const jmsType = getJmsMessageType(amqpType);
                if (jmsType !== null) {
                    // NOTE: Key MUST be Symbol, value MUST be byte (not ubyte)
                    // This matches Qpid JMS Client wire format
                    message.message_annotations = {
                        [Symbol.for('x-opt-jms-msg-type')]: rhea.types.wrap_byte(jmsType)
                    };
                }
            }

            context.sender.send(message);

            sentCount++;
        }
    });

    connection.on('accepted', (context) => {
        confirmedCount++;
        if (confirmedCount === total) {
            // Output result
            const result = {
                messages: testData,
                stats: { sent: sentCount }
            };
            console.log(JSON.stringify(result, null, 2));

            context.connection.close();
            setTimeout(() => process.exit(0), 100);
        }
    });

    connection.on('error', (error) => {
        console.error('Connection error:', error);
        process.exit(1);
    });

    // Timeout
    setTimeout(() => {
        if (confirmedCount < total) {
            console.error(`Timeout: only ${confirmedCount}/${total} messages confirmed`);
            process.exit(1);
        }
    }, 30000);
}

// Receiver
function receive(options) {
    const { broker, queue, count, timeout = 30 } = options;
    const expectedCount = parseInt(count);
    const messages = [];

    // Parse broker URL (e.g., "amqp://localhost:5672" or "localhost:5672")
    const brokerUrl = broker.replace(/^amqp:\/\//, '');
    const [host, port] = brokerUrl.split(':');

    // HACK: Monkey-patch types.unwrap to preserve Typed objects for message bodies
    const originalUnwrap = rhea.types.unwrap;
    let capturedTypedBodies = [];

    rhea.types.unwrap = function(o, leave_described) {
        // If this is a Typed object being unwrapped, capture it
        // We'll get multiple unwraps per message (headers, properties, body, etc.)
        // So we capture ALL of them and let the message handler pick the right one
        if (o && o.type && o.type.name) {
            capturedTypedBodies.push({
                typeName: o.type.name,
                typeCode: o.type.typecode,
                value: o.value,
                typed: o
            });
        }
        // Call original unwrap
        return originalUnwrap.call(this, o, leave_described);
    };

    const connection = rhea.connect({
        host: host || 'localhost',
        port: parseInt(port) || 5672,
        reconnect: false
    });

    connection.on('connection_open', (context) => {
        context.connection.open_receiver({ source: queue });
    });

    connection.on('message', (context) => {
        // Check if we captured Typed objects during unwrap
        const capturedList = [...capturedTypedBodies];
        capturedTypedBodies = [];  // Reset for next message

        const body = context.message.body;

        // Check for JMS message type annotation
        // NOTE: Qpid JMS Client uses Symbol as key
        let jmsMsgType = null;
        if (context.message.message_annotations) {
            const annotations = context.message.message_annotations;
            // Try to find the annotation (Symbol key might be represented different ways)
            const jmsTypeKey = Object.keys(annotations).find(key =>
                key === 'x-opt-jms-msg-type' ||
                key.toString() === 'Symbol(x-opt-jms-msg-type)' ||
                (typeof key === 'symbol' && key.toString().includes('x-opt-jms-msg-type'))
            );
            if (jmsTypeKey) {
                const annotationValue = annotations[jmsTypeKey];
                jmsMsgType = typeof annotationValue === 'object' && annotationValue.value !== undefined
                    ? annotationValue.value
                    : annotationValue;
            }
        }

        if (process.env.QIT_DEBUG) {
            console.error('Captured', capturedList.length, 'Typed objects during decode');
            capturedList.forEach((cap, i) => {
                console.error(`  [${i}] Type: ${cap.typeName}, Value: ${JSON.stringify(cap.value)}`);
            });
            console.error('Final body:', body);
            console.error('JMS message type:', jmsMsgType);
        }

        let decoded;
        if (jmsMsgType !== null) {
            // Decode as JMS message
            decoded = decodeJmsMessage(body, jmsMsgType);
        } else {
            // Decode as regular AMQP message
            // Find the Typed object that matches the body value
            let typedBody = null;
            for (let i = capturedList.length - 1; i >= 0; i--) {
                const cap = capturedList[i];
                if (cap.value === body || JSON.stringify(cap.value) === JSON.stringify(body)) {
                    typedBody = cap.typed;
                    break;
                }
            }
            decoded = typedBody ? TypeDecoder.decode(typedBody) : TypeDecoder.decode(body);
        }

        messages.push({
            index: messages.length,
            type: decoded.type,
            value: decoded.value
        });

        if (messages.length >= expectedCount) {
            // Output result
            const result = {
                messages: messages,
                stats: { received: messages.length }
            };
            console.log(JSON.stringify(result, null, 2));

            context.connection.close();
            setTimeout(() => process.exit(0), 100);
        }
    });

    connection.on('error', (error) => {
        console.error('Connection error:', error);
        process.exit(1);
    });

    // Timeout
    setTimeout(() => {
        if (messages.length < expectedCount) {
            // Output what we got
            const result = {
                messages: messages,
                stats: { received: messages.length }
            };
            console.log(JSON.stringify(result, null, 2));
        }
        process.exit(messages.length >= expectedCount ? 0 : 1);
    }, parseInt(timeout) * 1000);
}

// Main
const { command, options } = parseArgs();

switch (command) {
    case 'send':
        send(options);
        break;

    case 'receive':
        receive(options);
        break;

    default:
        console.error(`Unknown command: ${command}`);
        process.exit(1);
}
