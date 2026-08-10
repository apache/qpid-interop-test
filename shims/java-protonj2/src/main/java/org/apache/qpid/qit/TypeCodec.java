/**
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * QIT ProtonJ2 Shim - Type Codec
 * 
 * Handles encoding/decoding between JSON test values and AMQP types
 */
package org.apache.qpid.qit;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import org.apache.qpid.protonj2.types.Binary;
import org.apache.qpid.protonj2.types.DescribedType;
import org.apache.qpid.protonj2.types.Symbol;
import org.apache.qpid.protonj2.types.UnknownDescribedType;
import org.apache.qpid.protonj2.types.UnsignedByte;
import org.apache.qpid.protonj2.types.UnsignedInteger;
import org.apache.qpid.protonj2.types.UnsignedLong;
import org.apache.qpid.protonj2.types.UnsignedShort;

import java.lang.reflect.Array;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public class TypeCodec {

    /**
     * Encode JSON test value to AMQP type
     */
    public static Object encode(String amqpType, Object value) throws Exception {
        // Extract value from JsonElement if needed
        if (value instanceof JsonElement) {
            JsonElement jsonValue = (JsonElement) value;
            if (jsonValue.isJsonNull()) {
                return null;
            }
            if (jsonValue.isJsonPrimitive()) {
                JsonPrimitive prim = jsonValue.getAsJsonPrimitive();
                if (prim.isNumber()) {
                    value = prim.getAsLong();
                } else if (prim.isString()) {
                    value = prim.getAsString();
                } else if (prim.isBoolean()) {
                    value = prim.getAsBoolean();
                }
            }
        }

        switch (amqpType) {
            case "null":
                return null;

            case "boolean":
                if (value instanceof Boolean) return (Boolean) value;
                String strVal = value.toString();
                return "True".equalsIgnoreCase(strVal) || "true".equalsIgnoreCase(strVal);

            case "ubyte":
                return UnsignedByte.valueOf(parseLong(value).byteValue());

            case "ushort":
                return UnsignedShort.valueOf(parseLong(value).shortValue());

            case "uint":
                return UnsignedInteger.valueOf(parseLong(value));

            case "ulong":
                return UnsignedLong.valueOf(parseLong(value));

            case "byte":
                return parseLong(value).byteValue();

            case "short":
                return parseLong(value).shortValue();

            case "int":
                return parseLong(value).intValue();

            case "long":
                return parseLong(value);

            case "float":
                return parseFloat(value);

            case "double":
                return parseDouble(value);

            case "char":
                String strValue = value.toString();
                int codePoint;
                if (strValue.isEmpty() || strValue.equals("\\x00")) {
                    codePoint = 0;
                } else if (strValue.length() == 1) {
                    codePoint = strValue.charAt(0);
                } else {
                    codePoint = Integer.parseInt(strValue);
                }
                return (char) codePoint;

            case "timestamp":
                long millis = Long.parseLong(value.toString());
                return new Date(millis);

            case "uuid":
                String uuidStr = value.toString();
                return UUID.fromString(uuidStr);

            case "binary":
                String hexStr = value.toString();
                return new Binary(hexToBytes(hexStr));

            case "string":
                return value.toString();

            case "symbol":
                return Symbol.valueOf(value.toString());

            case "array":
            case "list":
            case "map":
            case "described":
                return encodeComplex(amqpType, value);

            default:
                throw new IllegalArgumentException("Unsupported AMQP type: " + amqpType);
        }
    }

    public static boolean isComplexType(String typeName) {
        return "array".equals(typeName) || "list".equals(typeName) ||
               "map".equals(typeName) || "described".equals(typeName);
    }

    public static Object encodeTypedElement(String elemType, Object value) throws Exception {
        if (isComplexType(elemType)) {
            return encodeComplex(elemType, value);
        }
        return encode(elemType, value);
    }

    public static Object encodeComplex(String amqpType, Object value) throws Exception {
        JsonElement json = (value instanceof JsonElement) ? (JsonElement) value : null;

        switch (amqpType) {
            case "array": {
                JsonObject obj = json != null ? json.getAsJsonObject() : null;
                if (obj == null) throw new IllegalArgumentException("Array value must be a JSON object");
                String elemType = obj.get("element_type").getAsString();
                JsonArray elements = obj.getAsJsonArray("elements");
                List<Object> encoded = new ArrayList<>();
                for (JsonElement e : elements) {
                    encoded.add(encodeTypedElement(elemType, e));
                }
                return createTypedArray(elemType, encoded);
            }

            case "list": {
                JsonArray arr = json != null ? json.getAsJsonArray() : null;
                if (arr == null) throw new IllegalArgumentException("List value must be a JSON array");
                List<Object> result = new ArrayList<>();
                for (JsonElement e : arr) {
                    JsonArray typed = e.getAsJsonArray();
                    String eType = typed.get(0).getAsString();
                    result.add(encodeTypedElement(eType, typed.get(1)));
                }
                return result;
            }

            case "map": {
                JsonArray arr = json != null ? json.getAsJsonArray() : null;
                if (arr == null) throw new IllegalArgumentException("Map value must be a JSON array");
                Map<Object, Object> result = new LinkedHashMap<>();
                for (JsonElement e : arr) {
                    JsonArray pair = e.getAsJsonArray();
                    JsonArray kArr = pair.get(0).getAsJsonArray();
                    JsonArray vArr = pair.get(1).getAsJsonArray();
                    Object k = encodeTypedElement(kArr.get(0).getAsString(), kArr.get(1));
                    Object v = encodeTypedElement(vArr.get(0).getAsString(), vArr.get(1));
                    result.put(k, v);
                }
                return result;
            }

            case "described": {
                JsonObject obj = json != null ? json.getAsJsonObject() : null;
                if (obj == null) throw new IllegalArgumentException("Described value must be a JSON object");
                JsonArray descArr = obj.getAsJsonArray("descriptor");
                JsonArray valArr = obj.getAsJsonArray("value");
                Object descriptor = encodeTypedElement(descArr.get(0).getAsString(), descArr.get(1));
                Object inner = encodeTypedElement(valArr.get(0).getAsString(), valArr.get(1));
                return new UnknownDescribedType(descriptor, inner);
            }

            default:
                throw new IllegalArgumentException("Unsupported complex type: " + amqpType);
        }
    }

    public static JsonArray decodeTypedElement(Object value) {
        DecodedMessage decoded = decode(value);
        JsonArray result = new JsonArray();
        result.add(decoded.type);
        result.add(decoded.value);
        return result;
    }

    /**
     * Decode AMQP value to JSON-compatible format
     */
    public static DecodedMessage decode(Object value) {
        DecodedMessage result = new DecodedMessage();

        if (value == null) {
            result.type = "null";
            result.value = com.google.gson.JsonNull.INSTANCE;
            return result;
        }

        String typeName = inferType(value);
        result.type = typeName;

        if (isComplexType(typeName)) {
            return decodeComplex(typeName, value);
        }

        switch (typeName) {
            case "null":
                result.value = com.google.gson.JsonNull.INSTANCE;
                break;

            case "boolean":
                result.value = new JsonPrimitive((Boolean) value);
                break;

            case "ubyte":
                result.value = new JsonPrimitive(((UnsignedByte) value).intValue());
                break;

            case "ushort":
                result.value = new JsonPrimitive(((UnsignedShort) value).intValue());
                break;

            case "uint":
                result.value = new JsonPrimitive(((UnsignedInteger) value).longValue());
                break;

            case "ulong":
                result.value = new JsonPrimitive(((UnsignedLong) value).longValue());
                break;

            case "byte":
                result.value = new JsonPrimitive((Byte) value);
                break;

            case "short":
                result.value = new JsonPrimitive((Short) value);
                break;

            case "int":
                result.value = new JsonPrimitive((Integer) value);
                break;

            case "long":
                result.value = new JsonPrimitive((Long) value);
                break;

            case "float":
                result.value = new JsonPrimitive(formatFloatAsHex((Float) value));
                break;

            case "double":
                result.value = new JsonPrimitive(formatDoubleAsHex((Double) value));
                break;

            case "char":
                result.value = new JsonPrimitive((int) (Character) value);
                break;

            case "timestamp":
                result.value = new JsonPrimitive(((Date) value).getTime());
                break;

            case "uuid":
                result.value = new JsonPrimitive(((UUID) value).toString());
                break;

            case "binary":
                result.value = new JsonPrimitive(bytesToHex(((Binary) value).asByteArray()));
                break;

            case "string":
                result.value = new JsonPrimitive((String) value);
                break;

            case "symbol":
                result.value = new JsonPrimitive(((Symbol) value).toString());
                break;

            default:
                result.value = new JsonPrimitive(value.toString());
                break;
        }

        return result;
    }

    /**
     * Infer AMQP type name from Java object
     */
    private static DecodedMessage decodeComplex(String typeName, Object value) {
        DecodedMessage result = new DecodedMessage();
        result.type = typeName;

        switch (typeName) {
            case "array": {
                int length = Array.getLength(value);
                String elemType = "unknown";
                Class<?> compType = value.getClass().getComponentType();
                if (compType != null && compType != Object.class) {
                    elemType = inferTypeFromClass(compType);
                }
                JsonArray elements = new JsonArray();
                for (int idx = 0; idx < length; idx++) {
                    Object item = Array.get(value, idx);
                    if ("unknown".equals(elemType) && item != null) {
                        elemType = inferType(item);
                    }
                    DecodedMessage decoded = decode(item);
                    elements.add(decoded.value);
                }
                JsonObject obj = new JsonObject();
                obj.addProperty("element_type", elemType);
                obj.add("elements", elements);
                result.value = obj;
                break;
            }

            case "list": {
                List<?> list = (List<?>) value;
                JsonArray elements = new JsonArray();
                for (Object item : list) {
                    elements.add(decodeTypedElement(item));
                }
                result.value = elements;
                break;
            }

            case "map": {
                Map<?, ?> map = (Map<?, ?>) value;
                JsonArray pairs = new JsonArray();
                for (Map.Entry<?, ?> entry : map.entrySet()) {
                    JsonArray pair = new JsonArray();
                    pair.add(decodeTypedElement(entry.getKey()));
                    pair.add(decodeTypedElement(entry.getValue()));
                    pairs.add(pair);
                }
                result.value = pairs;
                break;
            }

            case "described": {
                DescribedType desc = (DescribedType) value;
                JsonObject obj = new JsonObject();
                obj.add("descriptor", decodeTypedElement(desc.getDescriptor()));
                obj.add("value", decodeTypedElement(desc.getDescribed()));
                result.value = obj;
                break;
            }
        }

        return result;
    }

    private static String inferType(Object obj) {
        if (obj == null) return "null";

        // Complex types — check before primitives
        if (obj instanceof DescribedType) return "described";
        if (obj.getClass().isArray() && !(obj instanceof byte[])) return "array";
        if (obj instanceof Map) return "map";
        if (obj instanceof List) return "list";

        if (obj instanceof UnsignedByte) return "ubyte";
        if (obj instanceof UnsignedShort) return "ushort";
        if (obj instanceof UnsignedInteger) return "uint";
        if (obj instanceof UnsignedLong) return "ulong";
        if (obj instanceof Byte) return "byte";
        if (obj instanceof Short) return "short";
        if (obj instanceof Character) return "char";
        if (obj instanceof Integer) return "int";
        if (obj instanceof Long) return "long";
        if (obj instanceof Float) return "float";
        if (obj instanceof Double) return "double";
        if (obj instanceof Boolean) return "boolean";
        if (obj instanceof Date) return "timestamp";
        if (obj instanceof UUID) return "uuid";
        if (obj instanceof Binary) return "binary";
        if (obj instanceof String) return "string";
        if (obj instanceof Symbol) return "symbol";

        return "unknown";
    }

    private static String inferTypeFromClass(Class<?> clazz) {
        if (clazz == Boolean.class || clazz == boolean.class) return "boolean";
        if (clazz == UnsignedByte.class) return "ubyte";
        if (clazz == UnsignedShort.class) return "ushort";
        if (clazz == UnsignedInteger.class) return "uint";
        if (clazz == UnsignedLong.class) return "ulong";
        if (clazz == Byte.class) return "byte";
        if (clazz == Short.class || clazz == short.class) return "short";
        if (clazz == Integer.class || clazz == int.class) return "int";
        if (clazz == Long.class || clazz == long.class) return "long";
        if (clazz == Float.class || clazz == float.class) return "float";
        if (clazz == Double.class || clazz == double.class) return "double";
        if (clazz == Character.class || clazz == char.class) return "char";
        if (clazz == String.class) return "string";
        if (clazz == Symbol.class) return "symbol";
        if (clazz == UUID.class) return "uuid";
        if (clazz == Binary.class) return "binary";
        if (clazz == Date.class) return "timestamp";
        return "unknown";
    }

    private static Object createTypedArray(String elemType, List<Object> elements) {
        int n = elements.size();
        switch (elemType) {
            case "boolean": { boolean[] a = new boolean[n]; for (int i = 0; i < n; i++) a[i] = (Boolean) elements.get(i); return a; }
            case "ubyte": return elements.stream().map(x -> (UnsignedByte) x).toArray(UnsignedByte[]::new);
            case "ushort": return elements.stream().map(x -> (UnsignedShort) x).toArray(UnsignedShort[]::new);
            case "uint": return elements.stream().map(x -> (UnsignedInteger) x).toArray(UnsignedInteger[]::new);
            case "ulong": return elements.stream().map(x -> (UnsignedLong) x).toArray(UnsignedLong[]::new);
            case "byte": return elements.stream().map(x -> (Byte) x).toArray(Byte[]::new);
            case "short": { short[] a = new short[n]; for (int i = 0; i < n; i++) a[i] = (Short) elements.get(i); return a; }
            case "int": { int[] a = new int[n]; for (int i = 0; i < n; i++) a[i] = (Integer) elements.get(i); return a; }
            case "long": { long[] a = new long[n]; for (int i = 0; i < n; i++) a[i] = (Long) elements.get(i); return a; }
            case "float": { float[] a = new float[n]; for (int i = 0; i < n; i++) a[i] = (Float) elements.get(i); return a; }
            case "double": { double[] a = new double[n]; for (int i = 0; i < n; i++) a[i] = (Double) elements.get(i); return a; }
            case "char": { char[] a = new char[n]; for (int i = 0; i < n; i++) a[i] = (Character) elements.get(i); return a; }
            case "string": return elements.stream().map(x -> (String) x).toArray(String[]::new);
            case "symbol": return elements.stream().map(x -> (Symbol) x).toArray(Symbol[]::new);
            case "uuid": return elements.stream().map(x -> (UUID) x).toArray(UUID[]::new);
            case "binary": return elements.stream().map(x -> (Binary) x).toArray(Binary[]::new);
            case "timestamp": return elements.stream().map(x -> (Date) x).toArray(Date[]::new);
            default: return elements.toArray();
        }
    }

    // Helper methods

    private static Long parseLong(Object value) {
        if (value instanceof Long) return (Long) value;
        if (value instanceof Integer) return ((Integer) value).longValue();

        String str = value.toString();
        if (str.startsWith("-0x") || str.startsWith("-0X")) {
            return -Long.parseLong(str.substring(3), 16);
        }
        if (str.startsWith("0x") || str.startsWith("0X")) {
            return Long.parseLong(str.substring(2), 16);
        }
        return Long.parseLong(str);
    }

    private static Float parseFloat(Object value) {
        if (value instanceof Float) return (Float) value;

        String str = value.toString();
        if (str.startsWith("0x") || str.startsWith("0X")) {
            // Hex representation
            long intVal = Long.parseLong(str.substring(2), 16);
            return Float.intBitsToFloat((int) intVal);
        }
        return Float.parseFloat(str);
    }

    private static Double parseDouble(Object value) {
        if (value instanceof Double) return (Double) value;

        String str = value.toString();
        if (str.startsWith("0x") || str.startsWith("0X")) {
            // Hex representation - use parseUnsignedLong to handle values > Long.MAX_VALUE
            long longVal = Long.parseUnsignedLong(str.substring(2), 16);
            return Double.longBitsToDouble(longVal);
        }
        return Double.parseDouble(str);
    }

    private static String formatFloatAsHex(float value) {
        int bits = Float.floatToRawIntBits(value);
        return String.format("0x%08x", bits);
    }

    private static String formatDoubleAsHex(double value) {
        long bits = Double.doubleToRawLongBits(value);
        return String.format("0x%016x", bits);
    }

    private static byte[] hexToBytes(String hex) {
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                                + Character.digit(hex.charAt(i+1), 16));
        }
        return data;
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    /**
     * Decoded message result
     */
    public static class DecodedMessage {
        public String type;
        public JsonElement value;
    }
}
