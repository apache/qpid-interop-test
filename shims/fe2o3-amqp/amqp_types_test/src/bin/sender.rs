use std::env;

use anyhow::{anyhow, bail};
use fe2o3_amqp::types::primitives::{
    Binary, Byte, Dec128, Dec32, Dec64, Int, Long, Short, Symbol, Timestamp,
    UByte, UInt, ULong, UShort, Uuid, Value,
};
use ordered_float::OrderedFloat;
use serde_json::from_str;

#[derive(Debug)]
enum AmqpType {
    Null,
    Bool,
    UByte,
    UShort,
    UInt,
    ULong,
    Byte,
    Short,
    Int,
    Long,
    Float,
    Double,
    Decimal32,
    Decimal64,
    Decimal128,
    Char,
    Timestamp,
    Uuid,
    Binary,
    String,
    Symbol,
}

impl<'a> TryFrom<&'a str> for AmqpType {
    type Error = anyhow::Error;

    fn try_from(value: &'a str) -> Result<Self, anyhow::Error> {
        let outcome = match value {
            "binary" => Self::Binary,
            "boolean" => Self::Bool,
            "byte" => Self::Byte,
            "char" => Self::Char,
            "decimal128" => Self::Decimal128,
            "decimal32" => Self::Decimal32,
            "decimal64" => Self::Decimal64,
            "double" => Self::Double,
            "float" => Self::Float,
            "int" => Self::Int,
            "long" => Self::Long,
            "null" => Self::Null,
            "short" => Self::Short,
            "string" => Self::String,
            "symbol" => Self::Symbol,
            "timestamp" => Self::Timestamp,
            "ubyte" => Self::UByte,
            "uint" => Self::UInt,
            "ulong" => Self::ULong,
            "ushort" => Self::UShort,
            "uuid" => Self::Uuid,
            _ => bail!("Invalid type name"),
        };
        Ok(outcome)
    }
}

fn parse_test_json(amqp_type: &AmqpType, json: String) -> Result<Vec<Value>, anyhow::Error> {
    let jsons: Vec<String> = from_str(&json)?;
    match amqp_type {
        AmqpType::Null => jsons
            .into_iter()
            .map(|json| {
                match json.to_lowercase().as_str() {
                    "none" => from_str::<()>("null"), // JSON spec doesn't allow "None" or "none"
                    s @ _ => from_str::<()>(s)
                }
                .map(|_| Value::Null)
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Bool => jsons
            .into_iter()
            .map(|json| from_str(json.to_lowercase().as_str()).map(|b| Value::Bool(b)))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::UByte => jsons
            .into_iter()
            .map(|s| UByte::from_str_radix(s.trim_start_matches("0x"), 16).map(Value::UByte))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::UShort => jsons
            .into_iter()
            .map(|s| UShort::from_str_radix(s.trim_start_matches("0x"), 16).map(Value::UShort))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::UInt => jsons
            .into_iter()
            .map(|s| UInt::from_str_radix(s.trim_start_matches("0x"), 16).map(Value::UInt))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::ULong => jsons
            .into_iter()
            .map(|s| ULong::from_str_radix(s.trim_start_matches("0x"), 16).map(Value::ULong))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Byte => jsons
            .into_iter()
            .map(|s| Byte::from_str_radix(s.trim_start_matches("0x"), 16).map(Value::Byte))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Short => jsons
            .into_iter()
            .map(|s| Short::from_str_radix(s.trim_start_matches("0x"), 16).map(Value::Short))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Int => jsons
            .into_iter()
            .map(|s| Int::from_str_radix(s.trim_start_matches("0x"), 16).map(Value::Int))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Long => jsons
            .into_iter()
            .map(|s| Long::from_str_radix(s.trim_start_matches("0x"), 16).map(Value::Long))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Float => {
            let bits = jsons
                .into_iter()
                .map(|s| u32::from_str_radix(s.trim_start_matches("0x"), 16))
                .collect::<Result<Vec<u32>, _>>()?;
            let values = bits
                .into_iter()
                .map(|v| OrderedFloat::from(f32::from_bits(v)))
                .map(Value::Float)
                .collect();
            Ok(values)
        }
        AmqpType::Double => {
            let bits = jsons
                .into_iter()
                .map(|s| u64::from_str_radix(s.trim_start_matches("0x"), 16))
                .collect::<Result<Vec<u64>, _>>()?;
            let values = bits
                .into_iter()
                .map(|v| OrderedFloat::from(f64::from_bits(v)))
                .map(Value::Double)
                .collect();
            Ok(values)
        }
        AmqpType::Decimal32 => {
            use hex::FromHex;

            jsons
                .into_iter()
                .map(|s| {
                    <[u8; 4]>::from_hex(s.trim_start_matches("0x"))
                        .map(|b| Value::Decimal32(Dec32::from(b)))
                })
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        }
        AmqpType::Decimal64 => {
            use hex::FromHex;

            jsons
                .into_iter()
                .map(|s| {
                    <[u8; 8]>::from_hex(s.trim_start_matches("0x"))
                        .map(|b| Value::Decimal64(Dec64::from(b)))
                })
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        }
        AmqpType::Decimal128 => {
            use hex::FromHex;

            jsons
                .into_iter()
                .map(|s| {
                    <[u8; 16]>::from_hex(s.trim_start_matches("0x"))
                        .map(|b| Value::Decimal128(Dec128::from(b)))
                })
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        }
        AmqpType::Char => jsons
            .into_iter()
            .map(|s| {
                match s.len() {
                    0 => Err(anyhow!("A minimum length of 1 is expected for char")),
                    1 => s
                        .chars()
                        .next()
                        .ok_or(anyhow!("A minimum length of 1 is expected for char")),
                    _ => match u32::from_str_radix(s.trim_start_matches("0x"), 16) {
                        Ok(bits) => {
                            char::from_u32(bits).ok_or(anyhow!("Not all u32 are valid chars"))
                        }
                        Err(err) => Err(err.into()),
                    },
                }
                .map(Value::Char)
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Timestamp => jsons
            .into_iter()
            .map(|s| {
                i64::from_str_radix(s.trim_start_matches("0x"), 16)
                    .map(|v| Value::Timestamp(Timestamp::from(v)))
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Uuid => jsons
            .into_iter()
            .map(|s| {
                uuid::Uuid::try_parse(s.as_str())
                    .map(|u| Uuid::from(u.into_bytes()))
                    .map(Value::Uuid)
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Binary => {
            let vals: Vec<Binary> = from_str(&json)?;
            Ok(vals.into_iter().map(|val| Value::Binary(val)).collect())
        }
        AmqpType::String => {
            let vals: Vec<String> = from_str(&json)?;
            Ok(vals.into_iter().map(|val| Value::String(val)).collect())
        }
        AmqpType::Symbol => {
            let vals: Vec<Symbol> = from_str(&json)?;
            Ok(vals.into_iter().map(|val| Value::Symbol(val)).collect())
        }
    }
}

#[derive(Debug)]
struct TestSender {
    ip_addr: String,
    target_addr: String,
    amqp_type: AmqpType,
    values: Vec<Value>,
}

impl TestSender {}

impl TryFrom<Vec<String>> for TestSender {
    type Error = anyhow::Error;

    fn try_from(mut value: Vec<String>) -> Result<Self, Self::Error> {
        let mut drain = value.drain(1..5);

        let ip_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let target_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let type_name = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let json = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;

        let amqp_type = AmqpType::try_from(type_name.as_str())?;
        let values = parse_test_json(&amqp_type, json)?;

        Ok(Self {
            ip_addr,
            target_addr,
            amqp_type,
            values,
        })
    }
}

fn main() {
    println!("hello sender");

    let args: Vec<String> = env::args().collect();
    println!("{:?}", args);
    let test_sender = TestSender::try_from(args).unwrap();
    println!("{:?}", test_sender);
}
