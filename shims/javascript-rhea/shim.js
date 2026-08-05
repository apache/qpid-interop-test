#!/usr/bin/env node
/*
 * QIT JavaScript/Rhea AMQP Shim
 *
 * Uses Rhea library for AMQP 1.0 communication
 */

'use strict';

const rhea = require('rhea');
const rhea_message = require('rhea/lib/message');
const { v4: uuidv4 } = require('uuid');

// Monkey-patch Writer to support:
// 1. Nested described types (AmqpValue wrapping custom described types)
// 2. Nested array elements (array of arrays, array of lists)
const _rheaTypes = require('rhea/lib/types');

const _origWriterWrite = _rheaTypes.Writer.prototype.write;
_rheaTypes.Writer.prototype.write = function(o) {
    if (o && o._nestedDescribed && o.descriptor && o.value && o.value.descriptor) {
        this.write_typecode(0x00);
        _origWriterWrite.call(this, o.descriptor);
        _origWriterWrite.call(this, o.value);
    } else {
        _origWriterWrite.call(this, o);
    }
};

const _origWriteArray = _rheaTypes.Writer.prototype.write_array;
_rheaTypes.Writer.prototype.write_array = function(type, value, constructor) {
    if (constructor && value.length > 0 && value[0] && value[0].type &&
        (value[0].type.category === 4 || value[0].type.category === 3)) {
        var saved = this.position;
        this.position += type.width;
        this.write_uint(value.length, type.width);
        this.write_constructor(constructor.typecode, constructor.descriptor);
        for (var i = 0; i < value.length; i++) {
            var elem = value[i];
            if (elem.type.category === 4) {
                this.write_array(elem.type, elem.value, elem.array_constructor);
            } else {
                this.write_value(elem.type, elem.value);
            }
        }
        this.backfill_size(type.width, saved);
    } else {
        _origWriteArray.call(this, type, value, constructor);
    }
};

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
        const listData = (body && body.content !== undefined) ? body.content : body;
        if (Array.isArray(listData) && listData.length > 0) {
            return TypeDecoder.decode(listData[0]);
        }
        return { type: 'none', value: null };
    } else {
        // Unknown JMS type, fall back to regular AMQP decoding
        return TypeDecoder.decode(body);
    }
}

// AMQP type name to Rhea typecode map
const AMQP_TYPE_TO_TYPECODE = {
    'null': 0x40, 'boolean': 0x56,
    'ubyte': 0x50, 'ushort': 0x60, 'uint': 0x70, 'ulong': 0x80,
    'byte': 0x51, 'short': 0x61, 'int': 0x71, 'long': 0x81,
    'float': 0x72, 'double': 0x82,
    'char': 0x73, 'timestamp': 0x83, 'uuid': 0x98,
    'binary': 0xa0, 'string': 0xa1, 'symbol': 0xa3,
    'list': 0xd0, 'map': 0xd1, 'array': 0xf0,
};

// Encode a typed element ["type", value] for complex type structures
function encodeTypedElement(elemType, elemValue) {
    if (elemType === 'array') return encodeArray(elemValue);
    if (elemType === 'list') return encodeList(elemValue);
    if (elemType === 'map') return encodeMapComplex(elemValue);
    if (elemType === 'described') return encodeDescribed(elemValue);
    const types_mod = require('rhea/lib/types');
    if (elemType === 'null') return types_mod.Null();
    if (elemType === 'boolean') return types_mod.wrap_boolean(elemValue === true || elemValue === 'True');
    return TypeEncoder.encode(elemType, elemValue);
}

function encodeArray(value) {
    const elemType = value.element_type;
    const elements = value.elements || [];
    const typecode = AMQP_TYPE_TO_TYPECODE[elemType];
    if (!typecode) throw new Error(`Unknown array element type: ${elemType}`);
    if (elemType === 'array' || elemType === 'list' || elemType === 'map') {
        const encoded = elements.map(e => encodeTypedElement(elemType, e));
        return rhea.types.wrap_array(encoded, typecode);
    }
    const encoded = elements.map(e => {
        const typed = encodeTypedElement(elemType, e);
        return (typed && typed.value !== undefined) ? typed.value : typed;
    });
    return rhea.types.wrap_array(encoded, typecode);
}

function encodeList(value) {
    const types_mod = require('rhea/lib/types');
    if (!value || value.length === 0) return types_mod.List0();
    const encoded = value.map(e => encodeTypedElement(e[0], e[1]));
    return types_mod.List32(encoded);
}

function encodeMapComplex(value) {
    const types_mod = require('rhea/lib/types');
    if (!value || value.length === 0) return types_mod.Map32([]);
    const items = [];
    for (const pair of value) {
        items.push(encodeTypedElement(pair[0][0], pair[0][1]));
        items.push(encodeTypedElement(pair[1][0], pair[1][1]));
    }
    return types_mod.Map32(items);
}

function encodeDescribed(value) {
    const types_mod = require('rhea/lib/types');
    const desc = encodeTypedElement(value.descriptor[0], value.descriptor[1]);
    const inner = encodeTypedElement(value.value[0], value.value[1]);
    types_mod.described_nc(desc, inner);
    return inner;
}

function wrapDescribedAsBody(describedTyped) {
    const types_mod = require('rhea/lib/types');
    return {
        collect_sections: function(sections) {
            var Typed = describedTyped.constructor;
            var outer = new Typed(describedTyped.type, describedTyped);
            outer.descriptor = types_mod.wrap_ulong(0x77);
            outer._nestedDescribed = true;
            sections.push(outer);
        }
    };
}

// Decode a Typed object (pre-unwrap) to ["type", decoded_value] recursively
function decodeTypedRecursive(typed) {
    if (typed === null || typed === undefined) {
        return ['null', null];
    }

    // Not a Typed object — decode as primitive
    if (!typed || !typed.type || !typed.type.name) {
        return decodePrimitiveToTyped(typed);
    }

    const typeName = typed.type.name;

    // Described — must check BEFORE array/list/map since described types wrapping
    // complex values have the inner value's type name but also have .descriptor set
    if (typed.descriptor) {
        const desc = decodeTypedRecursive(typed.descriptor);
        let val;
        if (typed.value && typed.value.type && typed.value.type.name) {
            val = decodeTypedRecursive(typed.value);
        } else {
            const innerTypeName = typed.type ? typed.type.name : null;
            if (innerTypeName === 'List0' || innerTypeName === 'List8' || innerTypeName === 'List32') {
                const rawElements = Array.isArray(typed.value) ? typed.value : [];
                const decoded = rawElements.map(e => decodePrimitiveToTyped(e));
                val = ['list', decoded];
            } else if (innerTypeName === 'Map8' || innerTypeName === 'Map32') {
                const rawItems = Array.isArray(typed.value) ? typed.value : [];
                const pairs = [];
                for (let i = 0; i < rawItems.length; i += 2) {
                    pairs.push([decodePrimitiveToTyped(rawItems[i]), decodePrimitiveToTyped(rawItems[i + 1])]);
                }
                val = ['map', pairs];
            } else if (innerTypeName === 'Array8' || innerTypeName === 'Array32') {
                const rawElements = Array.isArray(typed.value) ? typed.value : [];
                const elemType = rawElements.length > 0 ? decodePrimitiveToTyped(rawElements[0])[0] : 'unknown';
                const decoded = rawElements.map(e => decodePrimitiveToTyped(e)[1]);
                val = ['array', { element_type: elemType, elements: decoded }];
            } else {
                val = decodePrimitiveToTyped(typed.value);
            }
        }
        return ['described', { descriptor: desc, value: val }];
    }

    // Array
    if (typeName === 'Array32' || typeName === 'Array8') {
        const elemTypecode = typed.array_constructor ? typed.array_constructor.typecode : null;
        const elemTypeName = elemTypecode ? typecodeToAmqpType(elemTypecode) : 'unknown';
        const rawElements = Array.isArray(typed.value) ? typed.value : [];
        const decoded = rawElements.map(e =>
            (e && e.type && e.type.name) ? decodeTypedRecursive(e)[1] : decodePrimitiveToTyped(e)[1]
        );
        return ['array', { element_type: elemTypeName, elements: decoded }];
    }

    // List
    if (typeName === 'List0' || typeName === 'List8' || typeName === 'List32') {
        const rawElements = Array.isArray(typed.value) ? typed.value : [];
        const decoded = rawElements.map(e => decodeTypedRecursive(e));
        return ['list', decoded];
    }

    // Map
    if (typeName === 'Map8' || typeName === 'Map32') {
        const rawItems = Array.isArray(typed.value) ? typed.value : [];
        const pairs = [];
        for (let i = 0; i < rawItems.length; i += 2) {
            const k = decodeTypedRecursive(rawItems[i]);
            const v = decodeTypedRecursive(rawItems[i + 1]);
            pairs.push([k, v]);
        }
        return ['map', pairs];
    }

    // Primitive Typed object
    return decodePrimitiveToTyped(typed);
}

function typecodeToAmqpType(tc) {
    const map = {};
    for (const [name, code] of Object.entries(AMQP_TYPE_TO_TYPECODE)) {
        map[code] = name;
    }
    // Handle small encoding variants
    map[0x41] = 'boolean';  // True
    map[0x42] = 'boolean';  // False
    map[0x43] = 'uint';     // Uint0
    map[0x44] = 'ulong';    // Ulong0
    map[0x52] = 'uint';     // SmallUint
    map[0x53] = 'ulong';    // SmallUlong
    map[0x54] = 'int';      // SmallInt
    map[0x55] = 'long';     // SmallLong
    map[0xb0] = 'binary';   // Bin32
    map[0xb1] = 'string';   // Str32
    map[0xb3] = 'symbol';   // Sym32
    map[0xc0] = 'list';     // List8
    map[0xc1] = 'map';      // Map8
    map[0xe0] = 'array';    // Array8
    return map[tc] || 'unknown';
}

function decodePrimitiveToTyped(value) {
    if (value === null || value === undefined) return ['null', null];
    if (typeof value === 'boolean') return ['boolean', value];

    // Typed object with type info
    if (value && value.type && value.type.name) {
        const { type: decoded } = TypeDecoder.decode(value);
        const amqpType = TypeDecoder.inferType(value);
        return [amqpType, TypeDecoder.decode(value).value];
    }

    if (Buffer.isBuffer(value)) return ['binary', value.toString('hex')];
    if (value instanceof Date) return ['timestamp', value.getTime()];
    if (typeof value === 'string') return ['string', value];
    if (typeof value === 'number') return ['long', value];

    return ['string', String(value)];
}

// Check if a Typed object is a complex AMQP type
function isComplexType(typed) {
    if (!typed || !typed.type || !typed.type.name) return false;
    const name = typed.type.name;
    if (name === 'Array8' || name === 'Array32') return true;
    if (name === 'List0' || name === 'List8' || name === 'List32') return true;
    if (name === 'Map8' || name === 'Map32') return true;
    if (typed.descriptor) return true;
    return false;
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
                return rhea.types.CharUTF32(parseInt(value));

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
            case 'null':
                return { type: 'null', value: null };

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
                if (Array.isArray(rawValue) && rawValue.length === 2) {
                    return { type: typeName, value: rawValue[0] * 4294967296 + rawValue[1] };
                }
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
                'Vbin8': 'binary',
                'Vbin32': 'binary',
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

// PRNG: glibc-style Linear Congruential Generator
function lcgGenerateBytes(seed, size) {
    let state = seed & 0x7FFFFFFF;
    const result = Buffer.alloc(size);
    for (let i = 0; i < size; i++) {
        state = (Math.imul(state, 1103515245) + 12345) & 0x7FFFFFFF;
        result[i] = (state >> 16) & 0xFF;
    }
    return result;
}

function lcgGenerateString(seed, size) {
    const raw = lcgGenerateBytes(seed, size);
    let s = '';
    for (let i = 0; i < size; i++) {
        s += String.fromCharCode(32 + (raw[i] % 95));
    }
    return s;
}

function generateCollectionElements(seed, count, elemSize) {
    const totalSize = count * elemSize;
    const fullString = lcgGenerateString(seed, totalSize);
    const result = [];
    for (let i = 0; i < count; i++) {
        result.push(fullString.substring(i * elemSize, (i + 1) * elemSize));
    }
    return result;
}

function generateMapKeys(count) {
    const keys = [];
    for (let i = 0; i < count; i++) {
        keys.push('key_' + String(i).padStart(4, '0'));
    }
    return keys;
}

// Send a single large content message
function sendLargeContent(options) {
    const { broker, queue } = options;
    const contentType = options['large-content'];
    const size = parseInt(options['size']) || 0;
    const seed = parseInt(options['seed']);
    const jmsMode = options['jms-mode'] !== undefined;
    const elementsCount = parseInt(options['elements']) || 0;
    const elemSize = parseInt(options['element-size']) || 0;

    let body;
    let jmsMsgType;
    if (contentType === 'binary') {
        body = rhea.types.wrap_binary(lcgGenerateBytes(seed, size));
        jmsMsgType = 3;  // JMS_BYTES_MESSAGE
    } else if (contentType === 'string') {
        body = lcgGenerateString(seed, size);
        jmsMsgType = 5;  // JMS_TEXT_MESSAGE
    } else if (contentType === 'list') {
        const elements = generateCollectionElements(seed, elementsCount, elemSize);
        body = elements;
        jmsMsgType = 4;  // JMS_STREAM_MESSAGE
    } else if (contentType === 'array') {
        const elements = generateCollectionElements(seed, elementsCount, elemSize);
        body = rhea.types.wrap_array(elements.map(e => rhea.types.wrap_string(e)), 0xb1);
        jmsMsgType = -1;
    } else if (contentType === 'map') {
        const elements = generateCollectionElements(seed, elementsCount, elemSize);
        const keys = generateMapKeys(elementsCount);
        const mapBody = {};
        for (let i = 0; i < elementsCount; i++) {
            mapBody[keys[i]] = elements[i];
        }
        body = mapBody;
        jmsMsgType = 2;  // JMS_MAP_MESSAGE
    } else if (contentType === 'described') {
        const types_mod = require('rhea/lib/types');
        const elements = generateCollectionElements(seed, elementsCount, elemSize);
        const listBody = elements.map(e => rhea.types.wrap_string(e));
        const innerList = types_mod.List32(listBody);
        const descriptor = rhea.types.wrap_symbol('test.large.described');
        types_mod.described_nc(descriptor, innerList);
        body = wrapDescribedAsBody(innerList);
        jmsMsgType = -1;
    } else {
        console.error('Unknown large-content type:', contentType);
        process.exit(1);
    }

    const message = { body: body };
    if (jmsMode && jmsMsgType >= 0) {
        message.message_annotations = {
            'x-opt-jms-msg-type': rhea.types.wrap_byte(jmsMsgType)
        };
    }

    // Parse broker URL
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
        context.sender.send(message);
    });

    connection.on('accepted', (context) => {
        let result;
        if (['list', 'array', 'map', 'described'].includes(contentType)) {
            result = { sent: true, elements: elementsCount, element_size: elemSize };
        } else {
            result = { sent: true, size: size };
        }
        console.log(JSON.stringify(result));
        context.connection.close();
        setTimeout(() => process.exit(0), 100);
    });

    connection.on('error', (error) => {
        console.error('Connection error:', error);
        process.exit(1);
    });

    setTimeout(() => {
        console.error('Timeout: message not confirmed');
        process.exit(1);
    }, 30000);
}

// Receive a single large content message and verify
function receiveLargeContent(options) {
    const { broker, queue, timeout = 30 } = options;
    const contentType = options['large-content'];
    const size = parseInt(options['size']) || 0;
    const seed = parseInt(options['seed']);
    const elementsCount = parseInt(options['elements']) || 0;
    const elemSize = parseInt(options['element-size']) || 0;

    // Parse broker URL
    const brokerUrl = broker.replace(/^amqp:\/\//, '');
    const [host, port] = brokerUrl.split(':');

    const connection = rhea.connect({
        host: host || 'localhost',
        port: parseInt(port) || 5672,
        reconnect: false
    });

    connection.on('connection_open', (context) => {
        context.connection.open_receiver({ source: queue });
    });

    connection.on('message', (context) => {
        const body = context.message.body;

        if (contentType === 'binary') {
            const expected = lcgGenerateBytes(seed, size);
            let data = body;
            if (data !== null && data !== undefined && data.content !== undefined) {
                data = data.content;
            }
            const received = Buffer.isBuffer(data) ? data : Buffer.from(data);

            const result = { size: received.length, expected_size: size };
            if (received.length !== expected.length) {
                result.match = false;
            } else if (received.equals(expected)) {
                result.match = true;
            } else {
                result.match = false;
                for (let i = 0; i < expected.length; i++) {
                    if (received[i] !== expected[i]) {
                        result.first_mismatch_offset = i;
                        break;
                    }
                }
            }
            console.log(JSON.stringify(result));
            context.connection.close();
            setTimeout(() => process.exit(result.match ? 0 : 1), 100);
        } else if (contentType === 'string') {
            const expected = lcgGenerateString(seed, size);
            const received = (body !== null && body !== undefined) ? String(body) : '';

            const result = { size: received.length, expected_size: size };
            if (received.length !== expected.length) {
                result.match = false;
            } else if (received === expected) {
                result.match = true;
            } else {
                result.match = false;
                for (let i = 0; i < expected.length; i++) {
                    if (received[i] !== expected[i]) {
                        result.first_mismatch_offset = i;
                        break;
                    }
                }
            }
            console.log(JSON.stringify(result));
            context.connection.close();
            setTimeout(() => process.exit(result.match ? 0 : 1), 100);
        } else if (['list', 'array', 'map', 'described'].includes(contentType)) {
            const expectedElements = generateCollectionElements(seed, elementsCount, elemSize);
            let receivedElements = [];

            try {
                if (contentType === 'list') {
                    // Body should be an array (Rhea might deliver as array or wrapped)
                    let listData = body;
                    if (listData && listData.content !== undefined) {
                        listData = listData.content;
                    }
                    if (Array.isArray(listData)) {
                        receivedElements = listData.map(e => String(e));
                    } else {
                        console.log(JSON.stringify({ match: false, error: 'expected list, got ' + typeof listData }));
                        context.connection.close();
                        setTimeout(() => process.exit(1), 100);
                        return;
                    }
                } else if (contentType === 'array') {
                    // Body may be an array or typed array object
                    let arrData = body;
                    if (arrData && arrData.content !== undefined) {
                        arrData = arrData.content;
                    }
                    if (Array.isArray(arrData)) {
                        receivedElements = arrData.map(e => String(e));
                    } else if (arrData && typeof arrData === 'object') {
                        // Typed array: may have numeric keys or be iterable
                        const values = Object.values(arrData);
                        receivedElements = values.map(e => String(e));
                    } else {
                        console.log(JSON.stringify({ match: false, error: 'expected array, got ' + typeof arrData }));
                        context.connection.close();
                        setTimeout(() => process.exit(1), 100);
                        return;
                    }
                } else if (contentType === 'map') {
                    // Body should be a JS object
                    if (body && typeof body === 'object' && !Array.isArray(body)) {
                        const keys = generateMapKeys(elementsCount);
                        receivedElements = keys.map(k => String(body[k] || ''));
                    } else {
                        console.log(JSON.stringify({ match: false, error: 'expected map, got ' + typeof body }));
                        context.connection.close();
                        setTimeout(() => process.exit(1), 100);
                        return;
                    }
                } else if (contentType === 'described') {
                    // Body should have descriptor and value, or be an array with described wrapper
                    let inner = body;
                    if (body && body.described_value !== undefined) {
                        inner = body.described_value;
                    } else if (body && body.value !== undefined && body.descriptor !== undefined) {
                        inner = body.value;
                    }
                    // Inner could be wrapped
                    if (inner && inner.content !== undefined) {
                        inner = inner.content;
                    }
                    if (Array.isArray(inner)) {
                        receivedElements = inner.map(e => String(e));
                    } else {
                        console.log(JSON.stringify({ match: false, error: 'expected described list, got ' + typeof inner }));
                        context.connection.close();
                        setTimeout(() => process.exit(1), 100);
                        return;
                    }
                }
            } catch (err) {
                console.log(JSON.stringify({ match: false, error: 'Failed to extract body: ' + err.message }));
                context.connection.close();
                setTimeout(() => process.exit(1), 100);
                return;
            }

            const result = { elements: receivedElements.length, element_size: elemSize };
            if (receivedElements.length !== elementsCount) {
                result.match = false;
            } else {
                result.match = true;
                for (let i = 0; i < elementsCount; i++) {
                    if (receivedElements[i] !== expectedElements[i]) {
                        result.match = false;
                        result.first_mismatch_element = i;
                        const exp = expectedElements[i];
                        const rcv = receivedElements[i];
                        for (let j = 0; j < Math.min(exp.length, rcv.length); j++) {
                            if (exp[j] !== rcv[j]) {
                                result.first_mismatch_offset = j;
                                break;
                            }
                        }
                        if (result.first_mismatch_offset === undefined) {
                            result.first_mismatch_offset = Math.min(exp.length, rcv.length);
                        }
                        break;
                    }
                }
            }
            console.log(JSON.stringify(result));
            context.connection.close();
            setTimeout(() => process.exit(result.match ? 0 : 1), 100);
        } else {
            console.log(JSON.stringify({ match: false, error: 'unknown type: ' + contentType }));
            context.connection.close();
            setTimeout(() => process.exit(1), 100);
        }
    });

    connection.on('error', (error) => {
        console.error('Connection error:', error);
        process.exit(1);
    });

    setTimeout(() => {
        console.log(JSON.stringify({ match: false, error: 'timeout' }));
        process.exit(1);
    }, parseInt(timeout) * 1000);
}

// Sender
function send(options) {
    const { broker, queue, type: amqpType, data, 'jms-mode': jmsMode, headers: headersJson, properties: propsJson } = options;
    const headers = headersJson ? JSON.parse(headersJson) : null;
    const properties = propsJson ? JSON.parse(propsJson) : null;
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

            if (jmsMode && amqpType === 'map') {
                const subType = msgData.type || 'string';
                const key = `${subType}_${String(msgData.index).padStart(3, '0')}`;
                const encodedValue = TypeEncoder.encode(subType, msgData.value);
                const mapObj = {};
                mapObj[key] = encodedValue;
                body = mapObj;
            } else if (jmsMode && amqpType === 'list') {
                const subType = msgData.type || 'string';
                const encodedValue = TypeEncoder.encode(subType, msgData.value);
                body = rhea_message.sequence_section([encodedValue]);
            } else if (['array', 'list', 'map', 'described'].includes(amqpType)) {
                body = encodeTypedElement(amqpType, msgData.value);
                if (amqpType === 'described') {
                    body = wrapDescribedAsBody(body);
                }
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
                    message.message_annotations = {
                        'x-opt-jms-msg-type': rhea.types.wrap_byte(jmsType)
                    };
                }
            }

            // Apply JMS headers
            if (headers) {
                if (headers.JMSCorrelationID) {
                    const h = headers.JMSCorrelationID;
                    if (h.type === 'string') {
                        message.correlation_id = h.value;
                    } else if (h.type === 'bytes') {
                        message.correlation_id = rhea.types.wrap_binary(Buffer.from(h.value, 'hex'));
                    }
                }
                if (headers.JMSReplyTo) {
                    const h = headers.JMSReplyTo;
                    message.reply_to = h.value;
                    if (!message.message_annotations) message.message_annotations = {};
                    message.message_annotations['x-opt-jms-reply-to'] = rhea.types.wrap_byte(h.type === 'topic' ? 1 : 0);
                }
                if (headers.JMSType) {
                    message.subject = headers.JMSType.value;
                }
            }

            // Apply JMS application properties
            if (properties) {
                const appProps = {};
                for (const [name, prop] of Object.entries(properties)) {
                    const ptype = prop.type;
                    const pval = prop.value;
                    if (ptype === 'boolean') {
                        appProps[name] = typeof pval === 'boolean' ? pval : pval === 'True';
                    } else if (ptype === 'byte') {
                        let v = typeof pval === 'string' ? parseInt(pval, 16) : pval;
                        if (v > 127) v -= 256;
                        appProps[name] = rhea.types.wrap_byte(v);
                    } else if (ptype === 'short') {
                        let v = typeof pval === 'string' ? parseInt(pval, 16) : pval;
                        if (v > 32767) v -= 65536;
                        appProps[name] = rhea.types.wrap_short(v);
                    } else if (ptype === 'int') {
                        let v = typeof pval === 'string' ? parseInt(pval, 16) : pval;
                        if (v > 0x7FFFFFFF) v -= 0x100000000;
                        appProps[name] = rhea.types.wrap_int(v);
                    } else if (ptype === 'long') {
                        const hex = typeof pval === 'string' ? pval.replace(/^0x/i, '') : pval.toString(16);
                        appProps[name] = rhea.types.wrap_long(Buffer.from(hex.padStart(16, '0'), 'hex'));
                    } else if (ptype === 'float') {
                        const bits = typeof pval === 'string' ? parseInt(pval, 16) : pval;
                        const buf = Buffer.alloc(4);
                        buf.writeUInt32BE(bits, 0);
                        appProps[name] = rhea.types.wrap_float(buf.readFloatBE(0));
                    } else if (ptype === 'double') {
                        const hex = typeof pval === 'string' ? pval.replace(/^0x/, '') : pval.toString(16);
                        const buf = Buffer.from(hex.padStart(16, '0'), 'hex');
                        appProps[name] = rhea.types.wrap_double(buf.readDoubleBE(0));
                    } else if (ptype === 'string') {
                        appProps[name] = String(pval);
                    }
                }
                message.application_properties = appProps;
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

    // Monkey-patch Reader.prototype.read to handle nested described types.
    // Rhea's reader collapses nested described constructors (e.g., AmqpValue wrapping
    // a custom described type), keeping only the outermost descriptor and discarding
    // inner ones. This patch builds a proper nested Typed chain so inner descriptors
    // survive through unwrap (which returns described types with leave_described=true).
    const types_mod = require('rhea/lib/types');
    const origReaderRead = types_mod.Reader.prototype.read;
    types_mod.Reader.prototype.read = function() {
        var constructor = this.read_constructor();
        var typeInfo = types_mod.by_code[constructor.typecode];
        if (!typeInfo) throw new Error('Unrecognised typecode: ' + constructor.typecode);
        var value = this.read_value(typeInfo);

        if (constructor.descriptors && constructor.descriptors.length > 1) {
            var Typed = value.constructor;
            var result = value;
            for (var i = constructor.descriptors.length - 1; i >= 0; i--) {
                var wrapperType = (i === 0)
                    ? { name: 'Described', typecode: 0 }
                    : (result.type || value.type);
                var wrapper = new Typed(wrapperType, result);
                wrapper.descriptor = constructor.descriptors[i];
                result = wrapper;
            }
            return result;
        }

        return constructor.descriptor ? types_mod.described_nc(constructor.descriptor, value) : value;
    };

    // Monkey-patch types.unwrap to capture Typed objects for message bodies
    const originalUnwrap = rhea.types.unwrap;
    let capturedTypedBodies = [];

    rhea.types.unwrap = function(o, leave_described) {
        if (o && o.type && o.type.name) {
            capturedTypedBodies.push({
                typeName: o.type.name,
                typeCode: o.type.typecode,
                value: o.value,
                typed: o
            });
        }
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
        } else if (body && body.type && body.type.name && body.descriptor) {
            // Body is a described Typed object (preserved by reader patch)
            const [type, value] = decodeTypedRecursive(body);
            decoded = { type, value };
        } else {
            // Search for the first complex Typed body in captured list
            let typedBody = null;
            for (let i = 0; i < capturedList.length; i++) {
                const cap = capturedList[i];
                if (isComplexType(cap.typed)) {
                    typedBody = cap.typed;
                    break;
                }
            }

            if (typedBody) {
                // Strip section descriptor (AmqpValue 0x70-0x78) applied by described_nc
                if (typedBody.descriptor) {
                    var dv = typedBody.descriptor.value;
                    if (typeof dv === 'number' && dv >= 0x70 && dv <= 0x78) {
                        delete typedBody.descriptor;
                    }
                }
                const [type, value] = decodeTypedRecursive(typedBody);
                decoded = { type, value };
            } else {
                // Fall back to value matching for primitives
                let primitiveTyped = null;
                for (let i = capturedList.length - 1; i >= 0; i--) {
                    const cap = capturedList[i];
                    if (cap.value === body || JSON.stringify(cap.value) === JSON.stringify(body)) {
                        primitiveTyped = cap.typed;
                        break;
                    }
                }
                decoded = primitiveTyped ? TypeDecoder.decode(primitiveTyped) : TypeDecoder.decode(body);
            }
        }

        const msgData = {
            index: messages.length,
            type: decoded.type,
            value: decoded.value
        };

        // Extract JMS headers
        const msgHeaders = {};
        if (context.message.correlation_id !== undefined && context.message.correlation_id !== null) {
            const cid = context.message.correlation_id;
            if (Buffer.isBuffer(cid)) {
                msgHeaders.JMSCorrelationID = { type: 'bytes', value: cid.toString('hex') };
            } else {
                msgHeaders.JMSCorrelationID = String(cid);
            }
        }
        if (context.message.reply_to !== undefined && context.message.reply_to !== null) {
            let replyType = 'queue';
            const annotations = context.message.message_annotations;
            if (annotations) {
                const rtKey = Object.keys(annotations).find(k =>
                    k === 'x-opt-jms-reply-to' || k.toString().includes('x-opt-jms-reply-to')
                );
                if (rtKey) {
                    const rtVal = annotations[rtKey];
                    const rtNum = typeof rtVal === 'object' && rtVal.value !== undefined ? rtVal.value : rtVal;
                    if (rtNum === 1) replyType = 'topic';
                }
            }
            let replyAddr = context.message.reply_to;
            if (replyAddr.startsWith('topic://')) {
                replyType = 'topic';
                replyAddr = replyAddr.substring(8);
            } else if (replyAddr.startsWith('queue://')) {
                replyAddr = replyAddr.substring(8);
            }
            msgHeaders.JMSReplyTo = { type: replyType, value: replyAddr };
        }
        if (context.message.subject !== undefined && context.message.subject !== null) {
            msgHeaders.JMSType = context.message.subject;
        }
        if (Object.keys(msgHeaders).length > 0) {
            msgData.headers = msgHeaders;
        }

        // Extract application properties
        const appProps = context.message.application_properties;
        if (appProps && Object.keys(appProps).length > 0) {
            const propsOut = {};
            for (const [name, value] of Object.entries(appProps)) {
                if (name.startsWith('JMS')) continue;
                const prop = {};
                if (typeof value === 'boolean') {
                    prop.type = 'boolean';
                    prop.value = value;
                } else if (value && value.typecode !== undefined) {
                    const tc = value.typecode;
                    const v = typeof value.valueOf === 'function' ? value.valueOf() : value;
                    if (tc === 0x51) {
                        prop.type = 'byte';
                        prop.value = '0x' + ((v & 0xFF) >>> 0).toString(16).padStart(2, '0');
                    } else if (tc === 0x61) {
                        prop.type = 'short';
                        prop.value = '0x' + ((v & 0xFFFF) >>> 0).toString(16).padStart(4, '0');
                    } else if (tc === 0x71 || tc === 0x54) {
                        prop.type = 'int';
                        prop.value = '0x' + ((v & 0xFFFFFFFF) >>> 0).toString(16).padStart(8, '0');
                    } else if (tc === 0x81 || tc === 0x55) {
                        prop.type = 'long';
                        if (Buffer.isBuffer(v)) {
                            prop.value = '0x' + v.toString('hex').padStart(16, '0');
                        } else {
                            const buf = Buffer.alloc(8);
                            buf.writeBigInt64BE(BigInt(v), 0);
                            prop.value = '0x' + buf.toString('hex');
                        }
                    } else if (tc === 0x72) {
                        prop.type = 'float';
                        const buf = Buffer.alloc(4);
                        buf.writeFloatBE(v, 0);
                        prop.value = '0x' + buf.toString('hex');
                    } else if (tc === 0x82) {
                        prop.type = 'double';
                        const buf = Buffer.alloc(8);
                        buf.writeDoubleBE(v, 0);
                        prop.value = '0x' + buf.toString('hex');
                    } else {
                        prop.type = 'string';
                        prop.value = String(v);
                    }
                } else if (typeof value === 'number') {
                    prop.type = 'double';
                    const buf = Buffer.alloc(8);
                    buf.writeDoubleBE(value, 0);
                    prop.value = '0x' + buf.toString('hex');
                } else if (typeof value === 'string') {
                    prop.type = 'string';
                    prop.value = value;
                } else {
                    prop.type = 'string';
                    prop.value = String(value);
                }
                propsOut[name] = prop;
            }
            if (Object.keys(propsOut).length > 0) {
                msgData.properties = propsOut;
            }
        }

        messages.push(msgData);

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
        if (options['large-content']) {
            sendLargeContent(options);
        } else {
            send(options);
        }
        break;

    case 'receive':
        if (options['large-content']) {
            receiveLargeContent(options);
        } else {
            receive(options);
        }
        break;

    default:
        console.error(`Unknown command: ${command}`);
        process.exit(1);
}
