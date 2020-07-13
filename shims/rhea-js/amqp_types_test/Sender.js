#!/usr/bin/env node
/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */

"use strict";

var uuid = require("node-uuid");
var amqp_types = require('rhea/lib/types.js');

//Check if the environment is Node.js and if not log an error and exit.
if (typeof process !== 'object' || typeof require !== 'function') {
    console.error("Receiver.js should be run in Node.js");
    process.exit(-1);
}

var args = process.argv.slice(2);
if (args.length !== 4) {
    console.error("ERROR: Sender.js needs 4 arguments:");
    console.error(" 1. Broker address (ip-addr:port)");
    console.error(" 2. Queue name");
    console.error(" 3. AMQP type");
    console.error(" 4. JSON string containing test values");
    process.exit(-1);
}

var AmqpArrayTypes = {
    "boolean": 0x56,
    "ubyte":   0x50,
    "ushort":  0x60,
    "uint":    0x70,
    "ulong":   0x80,
    "byte":    0x51,
    "short":   0x61,
    "int":     0x71,
    "long":    0x81,
    "float":   0x72,
    "double":  0x82,
    "decimal32":  0x74,
    "decimal64":  0x84,
    "decimal128": 0x94,
    "char":       0x73,
    "timestamp":  0x83,
    "uuid":       0x98,
    "binary":     0xb0,
    "string":     0xb1,
    "symbol":     0xb3
};

function Sender(brokerAddr, brokerPort, queueName, amqpType, testValues) {
    this.amqpType = amqpType;
    this.testValues = testValues;
    this.sent = 0;
    this.confirmed = 0;
    this.total = testValues.length;
    this.container = require('rhea');

    this.connection = this.container.connect({'host':brokerAddr, 'port':brokerPort, 'reconnect':false}); //.open_sender(queueName);
    this.connection.open_sender(queueName);

    this.createMessage = function(testValue) {
        //console.log("createMessage: amqpType=" + this.amqpType + "; testValue=" + testValue);
        switch(this.amqpType) {
        case "null": return {body: this.encodeNull(testValue)};
        case "boolean": return {body: amqp_types.wrap_boolean(this.encodeBoolean(testValue))};
        case "ubyte": return {body: amqp_types.wrap_ubyte(this.encodeUbyte(testValue))};
        case "ushort": return {body: amqp_types.wrap_ushort(this.encodeUshort(testValue))};
        case "uint": return {body: amqp_types.wrap_uint(this.encodeUint(testValue))};
        case "ulong": return {body: amqp_types.wrap_ulong(this.encodeUlong(testValue))};
        case "byte": return {body: amqp_types.wrap_byte(this.encodeByte(testValue))};
        case "short": return {body: amqp_types.wrap_short(this.encodeShort(testValue))};
        case "int": return {body: amqp_types.wrap_int(this.encodeInt(testValue))};
        case "long": return {body: amqp_types.wrap_long(this.encodeLong(testValue))};
        case "float": return {body: amqp_types.wrap_float(this.encodeFloat(testValue))};
        case "double": return {body: amqp_types.wrap_double(this.encodeDouble(testValue))};
        case "decimal32": return {body: new amqp_types.Decimal32(this.encodeDecimal32(testValue))};
        case "decimal64": return {body: new amqp_types.Decimal64(this.encodeDecimal64(testValue))};
        case "decimal128": return {body: new amqp_types.Decimal128(this.encodeDecimal128(testValue))};
        case "char": return {body: new amqp_types.CharUTF32(this.encodeChar(testValue))};
        case "timestamp": return {body: amqp_types.wrap_timestamp(this.encodeTimestamp(testValue))};
        case "uuid": return {body: new amqp_types.Uuid(this.encodeUuid(testValue))};
        case "binary": return {body: amqp_types.wrap_binary(this.encodeBinary(testValue))};
        case "string": return {body: amqp_types.wrap_string(this.encodeString(testValue))};
        case "symbol": return {body: amqp_types.wrap_symbol(this.encodeSymbol(testValue))};
        case "list":
        case "map":
        case "array": throw "Unsupported complex AMQP type: \"" + this.amqpType + "\"";
        default: throw "Unknown AMQP type: \"" + this.amqpType + "\"";
        }
    };

    // static
    this.encodeAmqpType = function(amqpType, testValue) {
        switch(amqpType) {
        case "null": return this.encodeNull(testValue);
        case "boolean": return this.encodeBoolean(testValue);
        case "ubyte": return this.encodeUbyte(testValue);
        case "ushort": return this.encodeUshort(testValue);
        case "uint": return this.encodeUint(testValue);
        case "ulong": return this.encodeUlong(testValue);
        case "byte": return this.encodeByte(testValue);
        case "short": return this.encodeShort(testValue);
        case "int": return this.encodeInt(testValue);
        case "long": return this.encodeLong(testValue);
        case "float": return this.encodeFloat(testValue);
        case "double": return this.encodeDouble(testValue);
        case "decimal32": return this.encodeDecimal32(testValue);
        case "decimal64": return this.encodeDecimal64(testValue);
        case "decimal128": return this.encodeDecimal128(testValue);
        case "char": return this.encodeChar(testValue);
        case "timestamp": return this.encodeTimestamp(testValue);
        case "uuid": return this.encodeUuid(testValue);
        case "binary": return this.encodeBinary(testValue);
        case "string": return this.encodeString(testValue);
        case "symbol": return this.encodeSymbol(testValue);
        case "list":
        case "map":
        case "array": throw "Unsupported complex AMQP type: \"" + this.amqpType + "\"";
        default: throw "Unknown AMQP type: \"" + this.amqpType + "\"";
        }
    };

    // These functions encode the incoming JSON string representation
    // of the test values into appropriate test values for the message
    // bodies.

    this.encodeNull = function(testValue) {
        if (testValue === "None") return null;
        this.handleEncodeError("null", testValue);
    };

    this.encodeBoolean = function(testValue) {
        if (testValue === "True") return true;
        if (testValue === "False") return false;
        this.handleEncodeError("boolean", testValue);
    };

    this.encodeUbyte = function(testValue) {
        try { return parseInt(testValue, 16); }
        catch (err) { this.handleEncodeError("ubyte", testValue); }
    };

    this.encodeUshort = function(testValue) {
        try { return parseInt(testValue, 16); }
        catch (err) { this.handleEncodeError("ushort", testValue); }
    };

    this.encodeUint = function(testValue) {
        try { return parseInt(testValue, 16); }
        catch (err) { this.handleEncodeError("uint", testValue); }
    };

    this.encodeUlong = function(testValue) {
        try { return new Buffer(this.hexString2ByteArray(testValue.slice(2), 8)); }
        catch (err) { this.handleEncodeError("ulong", testValue, err); }
    };

    this.encodeByte = function(testValue) {
        try { return parseInt(testValue, 16); }
        catch (err) { this.handleEncodeError("byte", testValue); }
    };

    this.encodeShort = function(testValue) {
        try { return parseInt(testValue, 16); }
        catch (err) { this.handleEncodeError("short", testValue); }
    };

    this.encodeInt = function(testValue) {
        try { return parseInt(testValue, 16); }
        catch (err) { this.handleEncodeError("int", testValue); }
    };

    this.encodeLong = function(testValue) {
        try {
            var negFlag = testValue.charAt(0) === "-";
            var ba = this.hexString2ByteArray(testValue.slice(negFlag ? 3 : 2), 8);
            if (negFlag) this.byteArray2sCompl(ba);
            return new Buffer(ba);
        }
        catch (err) { this.handleEncodeError("long", testValue); }
    };

    this.encodeFloat = function(testValue) {
        // NOTE: Buffer.readFloatBE() does not support -NaN (ignores sign)
//        var buf = new Buffer(testValue.substr(2), "hex");
//        return buf.readFloatBE(0);
        // This method gets the -NaN with sign onto the wire correctly.
        var dv = new DataView(new ArrayBuffer(4));
        dv.setUint32(0, parseInt(testValue.substr(2), 16));
        return dv.getFloat32(0);
    };

    this.encodeDouble = function(testValue) {
        // NOTE: Buffer.readDoubleBE() does not support -NaN (ignores sign)
//        var buf = new Buffer(testValue.substr(2), "hex");
//        return buf.readDoubleBE(0);
        // This method gets the -NaN with sign onto the wire correctly.
        var dv = new DataView(new ArrayBuffer(8));
        dv.setUint32(0, parseInt(testValue.substr(2, 8), 16));
        dv.setUint32(4, parseInt(testValue.substr(10), 16));
        return dv.getFloat64(0);
    };

    this.encodeDecimal32 = function(testValue) {
        try { return new Buffer(this.hexString2ByteArray(testValue.slice(2), 4)); }
        catch (err) { this.handleEncodeError("decimal32", testValue, err); }
    };

    this.encodeDecimal64 = function(testValue) {
        try { return new Buffer(this.hexString2ByteArray(testValue.slice(2), 8)); }
        catch (err) { this.handleEncodeError("decimal64", testValue, err); }
    };

    this.encodeDecimal128 = function(testValue) {
        try { return new Buffer(this.hexString2ByteArray(testValue.slice(2), 16)); }
        catch (err) { this.handleEncodeError("decimal128", testValue, err); }
    };

    this.encodeChar = function(testValue) {
        try {
            if (testValue.length === 1) { // Single char format 'a'
                return testValue.charCodeAt(0);
            } else { // Hex format '0xNNNN'
                return parseInt(testValue, 16);
            }
        }
        catch (err) { this.handleEncodeError("char", testValue); }
    };

    this.encodeTimestamp = function(testValue) {
        try { return parseInt(testValue, 16); }
        catch (err) { this.handleEncodeError("timestamp", testValue); }
    };

    this.encodeUuid = function(testValue) {
        var buff = new Buffer(16);
        try { uuid.parse(testValue, buff); }
        catch (err) { this.handleEncodeError("uuid", testValue); }
        return buff;
    };

    this.encodeBinary = function(testValue) {
        var buff = new Buffer(testValue, 'base64')
        return buff;
    };

    this.encodeString = function(testValue) {
        return testValue;
    };

    this.encodeSymbol = function(testValue) {
        return testValue;
    };

    this.handleEncodeError = function(amqpType, testValue, err) {
        var errStr = "Invalid string value for type " + amqpType + ": \"" + testValue + "\"";
        if (err) {
            errStr += " (" + err.message + ")";
        }
        throw new Error(errStr);
    };

    // NOTE: hexStr must not include '0x' prefix
    this.hexString2ByteArray = function(hexStr, len) {
        var result = [];
        var oddFlag = hexStr.length !== 2*Math.round(hexStr.length/2.0); // odd number of hex digits
        for (var i = len - 1; i >= 0; i--) {
            if (2 * i < hexStr.length) {
                var ssIndex = oddFlag ? 0 : hexStr.length - 2*(i+1);
                var ssLen = oddFlag ? 1 : 2;
                result.push(parseInt(hexStr.substr(ssIndex, ssLen), 16));
                oddFlag = false;
            } else {
                result.push(0); // leading zeros
            }
        }
        return result;
    };

    this.byteArray2sCompl = function(ba) {
        var carry = 1;
        for (var i=ba.length-1; i>=0; i--) {
            var val = (ba[i] ^ 0xff) + carry;
            ba[i] = val & 0xff;
            carry = val >> 8;
        }
    };

    this.container.on('sendable', function (context) {
        while (context.sender.sendable() && sender.sent < sender.total) {
            for (var i=0; i<sender.testValues.length; ++i) {
                context.sender.send(sender.createMessage(sender.testValues[i]));
                sender.sent++;
            }
        }
    });

    this.container.on('accepted', function (context) {
        if (++sender.confirmed === sender.total) {
            context.connection.close();
        }
    });

    this.container.on('disconnected', function (context) {
        sender.sent = sender.confirmed;
        console.error('Unable to connet to broker')
    });
}

var colonPos = args[0].indexOf(":");
var sender = new Sender(args[0].slice(0, colonPos), args[0].slice(colonPos+1), args[1], args[2], JSON.parse(args[3]));
