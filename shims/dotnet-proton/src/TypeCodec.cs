/*
 * QIT .NET Apache Qpid Proton Shim - Type Codec
 *
 * Handles encoding/decoding between JSON test values and AMQP types
 */

using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Apache.Qpid.Proton.Types;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Qit.Shim
{
    public class DescribedValue : Apache.Qpid.Proton.Types.IDescribedType
    {
        public object Descriptor { get; }
        public object Described { get; }

        public DescribedValue(object descriptor, object described)
        {
            Descriptor = descriptor;
            Described = described;
        }
    }

    public static class TypeCodec
    {
        /// <summary>
        /// Encode JSON value to AMQP object
        /// </summary>
        public static object Encode(string amqpType, object value)
        {
            // Handle JToken input
            if (value is JToken jtoken)
            {
                if (jtoken.Type == JTokenType.Null || jtoken == null)
                {
                    return null!;
                }
                value = jtoken.ToObject<object>();
            }

            switch (amqpType)
            {
                case "null":
                    return null!;

                case "boolean":
                    if (value is bool bval) return bval;
                    var strVal = value?.ToString() ?? "false";
                    return strVal.Equals("True", StringComparison.OrdinalIgnoreCase) ||
                           strVal.Equals("true", StringComparison.OrdinalIgnoreCase);

                case "ubyte":
                    return (byte)ParseUInt(value);

                case "ushort":
                    return (ushort)ParseUInt(value);

                case "uint":
                    return (uint)ParseUInt(value);

                case "ulong":
                    return ParseUInt(value);

                case "byte":
                    return (sbyte)ParseInt(value);

                case "short":
                    return (short)ParseInt(value);

                case "int":
                    return (int)ParseInt(value);

                case "long":
                    return ParseInt(value);

                case "float":
                    return ParseFloat(value);

                case "double":
                    return ParseDouble(value);

                case "char":
                    var codePoint = Convert.ToInt32(value);
                    return (char)codePoint;

                case "timestamp":
                    var millis = Convert.ToInt64(value);
                    return new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc).AddMilliseconds(millis);

                case "uuid":
                    var uuidStr = value?.ToString() ?? "";
                    return UuidStringToAmqpGuid(uuidStr);

                case "binary":
                    var hexStr = value?.ToString() ?? "";
                    return HexToBytes(hexStr);

                case "string":
                    return value?.ToString() ?? "";

                case "symbol":
                    // Create a Symbol object to preserve type information
                    return Symbol.Lookup(value?.ToString() ?? "");

                case "array":
                case "list":
                case "map":
                case "described":
                    return EncodeComplex(amqpType, value);

                default:
                    throw new NotSupportedException($"Unsupported AMQP type: {amqpType}");
            }
        }

        public static bool IsComplexType(string typeName)
        {
            return typeName == "array" || typeName == "list" || typeName == "map" || typeName == "described";
        }

        public static object EncodeComplex(string amqpType, object value)
        {
            JObject? obj = value as JObject;
            JArray? arr = value as JArray;

            switch (amqpType)
            {
                case "array":
                {
                    if (obj == null)
                        obj = JObject.FromObject(value);
                    var elemType = obj["element_type"]!.ToString();
                    var elements = obj["elements"] as JArray ?? new JArray();
                    var result = new List<object>();
                    foreach (var e in elements)
                    {
                        if (IsComplexType(elemType))
                            result.Add(EncodeComplex(elemType, e!));
                        else
                            result.Add(Encode(elemType, e!));
                    }
                    return CreateTypedArray(elemType, result);
                }

                case "list":
                {
                    if (arr == null)
                        arr = JArray.FromObject(value);
                    var result = new List<object>();
                    foreach (var elem in arr)
                    {
                        var typedElem = elem as JArray;
                        if (typedElem == null || typedElem.Count != 2) continue;
                        var eType = typedElem[0]!.ToString();
                        result.Add(EncodeTypedElement(eType, typedElem[1]!));
                    }
                    return result;
                }

                case "map":
                {
                    if (arr == null)
                        arr = JArray.FromObject(value);
                    var result = new Dictionary<object, object>();
                    foreach (var pair in arr)
                    {
                        var pairArr = pair as JArray;
                        if (pairArr == null || pairArr.Count != 2) continue;
                        var kArr = pairArr[0] as JArray;
                        var vArr = pairArr[1] as JArray;
                        if (kArr == null || kArr.Count != 2 || vArr == null || vArr.Count != 2) continue;
                        var k = EncodeTypedElement(kArr[0]!.ToString(), kArr[1]!);
                        var v = EncodeTypedElement(vArr[0]!.ToString(), vArr[1]!);
                        result[k] = v;
                    }
                    return result;
                }

                case "described":
                {
                    if (obj == null)
                        obj = JObject.FromObject(value);
                    var descArr = obj["descriptor"] as JArray ?? new JArray();
                    var valArr = obj["value"] as JArray ?? new JArray();
                    var descriptor = EncodeTypedElement(descArr[0]!.ToString(), descArr[1]!);
                    var inner = EncodeTypedElement(valArr[0]!.ToString(), valArr[1]!);
                    return new DescribedValue(descriptor, inner);
                }

                default:
                    throw new NotSupportedException($"Unsupported complex type: {amqpType}");
            }
        }

        public static object EncodeTypedElement(string elemType, object value)
        {
            if (IsComplexType(elemType))
                return EncodeComplex(elemType, value);
            return Encode(elemType, value);
        }

        /// <summary>
        /// Decode AMQP object to typed result
        /// </summary>
        public static DecodedMessage Decode(object value, bool isAmqpValue = false)
        {
            if (value == null)
            {
                return new DecodedMessage { Type = "null", Value = null };
            }

            string qpiditType = InferType(value, isAmqpValue);

            if (IsComplexType(qpiditType))
            {
                return DecodeComplex(qpiditType, value);
            }

            object resultValue = qpiditType switch
            {
                "null" => null!,
                "boolean" => (bool)value,
                "ubyte" => (byte)value,
                "ushort" => (ushort)value,
                "uint" => (uint)value,
                "ulong" => (ulong)value,
                "byte" => (sbyte)value,
                "short" => (short)value,
                "int" => (int)value,
                "long" => (long)value,
                "float" => FormatFloatAsHex((float)value),
                "double" => FormatDoubleAsHex((double)value),
                "char" => (int)(char)value,
                "timestamp" => ConvertToEpochMillis((DateTime)value),
                "uuid" => AmqpGuidToUuidString((Guid)value),
                "binary" => ConvertBinaryToHex(value),
                "string" => (string)value,
                "symbol" => value.ToString()!,
                _ => value.ToString()!
            };

            return new DecodedMessage
            {
                Type = qpiditType,
                Value = resultValue
            };
        }

        public static object[] DecodeTypedElement(object value)
        {
            if (value == null)
                return new object[] { "null", null! };

            var decoded = Decode(value);
            return new object[] { decoded.Type, decoded.Value! };
        }

        private static DecodedMessage DecodeComplex(string typeName, object value)
        {
            switch (typeName)
            {
                case "array":
                {
                    if (value is Array arr)
                    {
                        string elemType = "unknown";
                        // For typed arrays, infer element type from C# type
                        var csElemType = arr.GetType().GetElementType();
                        if (csElemType != null && csElemType != typeof(object))
                            elemType = InferTypeFromClrType(csElemType);
                        var elements = new List<object>();
                        foreach (var item in arr)
                        {
                            if (elemType == "unknown" && item != null)
                                elemType = InferType(item);
                            var decoded = Decode(item);
                            elements.Add(decoded.Value!);
                        }
                        var result = new Dictionary<string, object>
                        {
                            { "element_type", elemType },
                            { "elements", elements }
                        };
                        return new DecodedMessage { Type = "array", Value = result };
                    }
                    break;
                }

                case "list":
                {
                    if (value is IList list)
                    {
                        var elements = new List<object[]>();
                        foreach (var item in list)
                        {
                            elements.Add(DecodeTypedElement(item));
                        }
                        return new DecodedMessage { Type = "list", Value = elements };
                    }
                    break;
                }

                case "map":
                {
                    if (value is IDictionary dict)
                    {
                        var pairs = new List<object[][]>();
                        foreach (DictionaryEntry entry in dict)
                        {
                            var k = DecodeTypedElement(entry.Key);
                            var v = DecodeTypedElement(entry.Value!);
                            pairs.Add(new[] { k, v });
                        }
                        return new DecodedMessage { Type = "map", Value = pairs };
                    }
                    break;
                }

                case "described":
                {
                    if (value is Apache.Qpid.Proton.Types.IDescribedType desc)
                    {
                        var result2 = new Dictionary<string, object>
                        {
                            { "descriptor", DecodeTypedElement(desc.Descriptor) },
                            { "value", DecodeTypedElement(desc.Described) }
                        };
                        return new DecodedMessage { Type = "described", Value = result2 };
                    }
                    break;
                }
            }

            return new DecodedMessage { Type = typeName, Value = value?.ToString() };
        }

        /// <summary>
        /// Infer AMQP type name from .NET object using reflection
        /// </summary>
        private static string InferType(object obj, bool isAmqpValue = false)
        {
            if (obj == null) return "null";

            var type = obj.GetType();
            var typeName = type.Name;

            // Complex types — check before primitive/symbol inference
            if (obj is Apache.Qpid.Proton.Types.IDescribedType)
                return "described";
            if (obj is byte[] || obj is Apache.Qpid.Proton.Buffer.IProtonBuffer)
                return "binary";

            // Symbol check (after byte[]/IProtonBuffer but before Array — Symbol[] is an array)
            if (type.Namespace?.Contains("Qpid.Proton") == true && !type.IsArray)
            {
                if (typeName.Contains("Symbol", StringComparison.OrdinalIgnoreCase))
                    return "symbol";
            }
            if (obj is Array)
            {
                var elemType = obj.GetType().GetElementType();
                if (elemType == typeof(object))
                {
                    var arr = (Array)obj;
                    if (arr.Length == 0)
                        return "list";
                    return isAmqpValue ? "array" : "list";
                }
                return "array";
            }
            if (obj is IDictionary)
                return "map";
            if (obj is IList)
                return "list";

            return typeName switch
            {
                "Boolean" => "boolean",
                "Byte" => "ubyte",
                "UInt16" => "ushort",
                "UInt32" => "uint",
                "UInt64" => "ulong",
                "SByte" => "byte",
                "Int16" => "short",
                "Int32" => "int",
                "Int64" => "long",
                "Single" => "float",
                "Double" => "double",
                "Char" => "char",
                "DateTime" => "timestamp",
                "Guid" => "uuid",
                "Byte[]" => "binary",
                "String" => "string",
                _ => "unknown"
            };
        }

        private static Guid UuidStringToAmqpGuid(string uuid)
        {
            var clean = uuid.Replace("-", "");
            var bytes = new byte[16];
            for (int i = 0; i < 16; i++)
                bytes[i] = byte.Parse(clean.Substring(i * 2, 2), NumberStyles.HexNumber);
            return new Guid(bytes);
        }

        private static string AmqpGuidToUuidString(Guid guid)
        {
            var b = guid.ToByteArray();
            return $"{b[0]:x2}{b[1]:x2}{b[2]:x2}{b[3]:x2}-{b[4]:x2}{b[5]:x2}-{b[6]:x2}{b[7]:x2}-{b[8]:x2}{b[9]:x2}-{b[10]:x2}{b[11]:x2}{b[12]:x2}{b[13]:x2}{b[14]:x2}{b[15]:x2}";
        }

        private static string InferTypeFromClrType(Type clrType)
        {
            if (clrType == typeof(bool)) return "boolean";
            if (clrType == typeof(byte)) return "ubyte";
            if (clrType == typeof(ushort)) return "ushort";
            if (clrType == typeof(uint)) return "uint";
            if (clrType == typeof(ulong)) return "ulong";
            if (clrType == typeof(sbyte)) return "byte";
            if (clrType == typeof(short)) return "short";
            if (clrType == typeof(int)) return "int";
            if (clrType == typeof(long)) return "long";
            if (clrType == typeof(float)) return "float";
            if (clrType == typeof(double)) return "double";
            if (clrType == typeof(char)) return "char";
            if (clrType == typeof(string)) return "string";
            if (clrType == typeof(Guid)) return "uuid";
            if (clrType == typeof(DateTime)) return "timestamp";
            if (clrType == typeof(byte[])) return "binary";
            if (clrType == typeof(Symbol)) return "symbol";
            return "unknown";
        }

        private static object CreateTypedArray(string elemType, List<object> elements)
        {
            switch (elemType)
            {
                case "boolean": return elements.Select(x => Convert.ToBoolean(x)).ToArray();
                case "ubyte": return elements.Select(x => Convert.ToByte(x)).ToArray();
                case "ushort": return elements.Select(x => Convert.ToUInt16(x)).ToArray();
                case "uint": return elements.Select(x => Convert.ToUInt32(x)).ToArray();
                case "ulong": return elements.Select(x => Convert.ToUInt64(x)).ToArray();
                case "byte": return elements.Select(x => Convert.ToSByte(x)).ToArray();
                case "short": return elements.Select(x => Convert.ToInt16(x)).ToArray();
                case "int": return elements.Select(x => Convert.ToInt32(x)).ToArray();
                case "long": return elements.Select(x => Convert.ToInt64(x)).ToArray();
                case "float": return elements.Select(x => Convert.ToSingle(x)).ToArray();
                case "double": return elements.Select(x => Convert.ToDouble(x)).ToArray();
                case "char": return elements.Select(x => Convert.ToChar(x)).ToArray();
                case "string": return elements.Select(x => x?.ToString() ?? "").ToArray();
                case "symbol": return elements.Select(x => (Symbol)x).ToArray();
                case "uuid": return elements.Select(x => (Guid)x).ToArray();
                case "binary": return elements.Select(x => (byte[])x).ToArray();
                case "timestamp": return elements.Select(x => (DateTime)x).ToArray();
                default: return elements.ToArray();
            }
        }

        // Helper methods

        private static ulong ParseUInt(object value)
        {
            if (value is ulong ul) return ul;
            if (value is long l) return (ulong)l;

            var str = value?.ToString() ?? "0";
            if (str.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                return ulong.Parse(str.Substring(2), NumberStyles.HexNumber);

            return ulong.Parse(str);
        }

        private static long ParseInt(object value)
        {
            if (value is long l) return l;
            if (value is int i) return i;

            var str = value?.ToString() ?? "0";
            if (str.StartsWith("-0x", StringComparison.OrdinalIgnoreCase))
                return -((long)ulong.Parse(str.Substring(3), NumberStyles.HexNumber));
            if (str.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                return (long)ulong.Parse(str.Substring(2), NumberStyles.HexNumber);

            return long.Parse(str);
        }

        private static float ParseFloat(object value)
        {
            if (value is float f) return f;

            var str = value?.ToString() ?? "0.0";
            if (str.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            {
                // Hex representation
                var intVal = uint.Parse(str.Substring(2), NumberStyles.HexNumber);
                var bytes = BitConverter.GetBytes(intVal);
                return BitConverter.ToSingle(bytes, 0);
            }

            return float.Parse(str, CultureInfo.InvariantCulture);
        }

        private static double ParseDouble(object value)
        {
            if (value is double d) return d;

            var str = value?.ToString() ?? "0.0";
            if (str.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            {
                // Hex representation
                var intVal = ulong.Parse(str.Substring(2), NumberStyles.HexNumber);
                var bytes = BitConverter.GetBytes(intVal);
                return BitConverter.ToDouble(bytes, 0);
            }

            return double.Parse(str, CultureInfo.InvariantCulture);
        }

        private static string FormatFloatAsHex(float value)
        {
            var bytes = BitConverter.GetBytes(value);
            var intVal = BitConverter.ToUInt32(bytes, 0);
            return $"0x{intVal:x8}";
        }

        private static string FormatDoubleAsHex(double value)
        {
            var bytes = BitConverter.GetBytes(value);
            var longVal = BitConverter.ToUInt64(bytes, 0);
            return $"0x{longVal:x16}";
        }

        private static long ConvertToEpochMillis(DateTime dt)
        {
            var epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            return (long)(dt.ToUniversalTime() - epoch).TotalMilliseconds;
        }

        private static byte[] HexToBytes(string hex)
        {
            var bytes = new byte[hex.Length / 2];
            for (int i = 0; i < bytes.Length; i++)
            {
                bytes[i] = byte.Parse(hex.Substring(i * 2, 2), NumberStyles.HexNumber);
            }
            return bytes;
        }

        private static string ConvertBinaryToHex(object value)
        {
            if (value is byte[] bytes)
                return BytesToHex(bytes);
            if (value is Apache.Qpid.Proton.Buffer.IProtonBuffer buf)
            {
                var data = new byte[buf.ReadableBytes];
                for (int i = 0; i < data.Length; i++)
                    data[i] = buf.ReadUnsignedByte();
                return BytesToHex(data);
            }
            return value?.ToString() ?? "";
        }

        private static string BytesToHex(byte[] bytes)
        {
            var sb = new StringBuilder();
            foreach (var b in bytes)
            {
                sb.Append(b.ToString("x2"));
            }
            return sb.ToString();
        }
    }

    public class DecodedMessage
    {
        [JsonProperty("type")]
        public string Type { get; set; } = "";

        [JsonProperty("value")]
        public object? Value { get; set; }
    }
}
