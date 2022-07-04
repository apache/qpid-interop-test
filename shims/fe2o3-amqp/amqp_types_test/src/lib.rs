use std::str::FromStr;

use anyhow::{anyhow, Result};
use fe2o3_amqp::types::primitives::{Byte, Int, Long, Short, UByte, UInt, ULong, UShort, Value, Dec32, Dec64, Dec128, Timestamp, Uuid};
use hex::ToHex;
use ordered_float::OrderedFloat;
use serde_json::from_str;

pub enum AmqpType {
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

impl TryFrom<String> for AmqpType {
    type Error = anyhow::Error;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        match value.as_str() {
            "binary" => Ok(Self::Binary),
            "boolean" => Ok(Self::Bool),
            "byte" => Ok(Self::Byte),
            "char" => Ok(Self::Char),
            "decimal128" => Ok(Self::Decimal128),
            "decimal32" => Ok(Self::Decimal32),
            "decimal64" => Ok(Self::Decimal64),
            "double" => Ok(Self::Double),
            "float" => Ok(Self::Float),
            "int" => Ok(Self::Int),
            "long" => Ok(Self::Long),
            "null" => Ok(Self::Null),
            "short" => Ok(Self::Short),
            "string" => Ok(Self::String),
            "symbol" => Ok(Self::Symbol),
            "timestamp" => Ok(Self::Timestamp),
            "ubyte" => Ok(Self::UByte),
            "uint" => Ok(Self::UInt),
            "ulong" => Ok(Self::ULong),
            "ushort" => Ok(Self::UShort),
            "uuid" => Ok(Self::Uuid),
            _ => Err(anyhow!("Type not impelmented")),
        }
    }
}

macro_rules! parse_number {
    ($str:ident, $val_ty:ident) => {
        <$val_ty>::from_str_radix($str.replace("0x", "").as_str(), 16).map(|v| Value::$val_ty(v))
    };
}

pub fn parse_test_json(amqp_type: AmqpType, input: String) -> Result<Vec<Value>> {
    let jsons: Vec<String> = from_str(&input)?;

    match amqp_type {
        AmqpType::Null => jsons
            .into_iter()
            .map(|s| s.replace("None", "null"))
            .map(|s| from_str(s.as_str()))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Bool => jsons
            .into_iter()
            .map(|mut s| {
                let (head, tail) = s.split_at_mut(1);
                format!("{}{}", head.to_uppercase(), tail)
            })
            .map(|s| from_str(s.as_str()))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::UByte => jsons
            .into_iter()
            .map(|s| parse_number!(s, UByte))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::UShort => jsons
            .into_iter()
            .map(|s| parse_number!(s, UShort))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::UInt => jsons
            .into_iter()
            .map(|s| parse_number!(s, UInt))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::ULong => jsons
            .into_iter()
            .map(|s| parse_number!(s, ULong))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Byte => jsons
            .into_iter()
            .map(|s| parse_number!(s, Byte))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Short => jsons
            .into_iter()
            .map(|s| parse_number!(s, Short))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Int => jsons
            .into_iter()
            .map(|s| parse_number!(s, Int))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Long => jsons
            .into_iter()
            .map(|s| parse_number!(s, Long))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Float => jsons
            .into_iter()
            .map(|s| {
                u32::from_str_radix(s.replace("0x", "").as_str(), 16)
                    .map(|v| Value::Float(OrderedFloat::from(f32::from_bits(v))))
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Double => jsons
            .into_iter()
            .map(|s| {
                u64::from_str_radix(s.replace("0x", "").as_str(), 16)
                    .map(|v| Value::Double(OrderedFloat::from(f64::from_bits(v))))
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Decimal32 => {
            use hex::FromHex;

            jsons.into_iter()
                .map(|s| <[u8; 4]>::from_hex(s.replace("0x", "")).map(Dec32::from).map(Value::Decimal32))
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
        AmqpType::Decimal64 => {
            use hex::FromHex;

            jsons.into_iter()
                .map(|s| <[u8; 8]>::from_hex(s.replace("0x", "")).map(Dec64::from).map(Value::Decimal64))
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
        AmqpType::Decimal128 => {
            use hex::FromHex;

            jsons.into_iter()
                .map(|s| <[u8; 16]>::from_hex(s.replace("0x", "")).map(Dec128::from).map(Value::Decimal128))
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
        AmqpType::Char => {
            jsons.into_iter()
                .map(|s| if s.len() == 1 {
                    s.chars().next().map(Value::Char).ok_or(anyhow!("Not enough bytes"))
                } else {
                    match u32::from_str_radix(s.replace("0x", "").as_str(), 16) {
                        Ok(val) => char::from_u32(val).ok_or(anyhow!("Cannot parse char")),
                        Err(err) => Err(err.into()),
                    }
                    .map(Value::Char)
                })
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
        AmqpType::Timestamp => {
            jsons.into_iter()
                .map(|s| i64::from_str_radix(s.replace("0x", "").as_str(), 16).map(|v| Value::Timestamp(Timestamp::from(v))))
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
        AmqpType::Uuid => {
            jsons.into_iter()
                .map(|s| uuid::Uuid::from_str(s.as_str()).map(|v| Value::Uuid(Uuid::from(v.into_bytes()))))
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
        AmqpType::Binary => {
            jsons.into_iter()
                .map(|s| from_str(s.as_str()).map(Value::Binary))
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
        AmqpType::String => {
            jsons.into_iter()
                .map(|s| from_str(s.as_str()).map(Value::String))
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
        AmqpType::Symbol => {
            jsons.into_iter()
                .map(|s| from_str(s.as_str()).map(Value::Symbol))
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        },
    }
}

pub trait  IntoTestJson {
    fn into_test_json(self) -> Result<String>;
}

impl IntoTestJson for Value {
    fn into_test_json(self) -> Result<String> {
        match self {
            Value::Null => Ok(String::from("\"None\"")),
            Value::Bool(value) => match value {
                true => Ok("\"True\"".to_string()),
                false => Ok("\"False\"".to_string()),
            },
            Value::UByte(value) => Ok(format!("\"{:#x}\"", value)),
            Value::UShort(value) => Ok(format!("\"{:#x}\"", value)),
            Value::UInt(value) => Ok(format!("\"{:#x}\"", value)),
            Value::ULong(value) => Ok(format!("\"{:#x}\"", value)),
            Value::Byte(value) => if value < 0 {
                Ok(format!("\"-{:#x}\"", value))
            } else {
                Ok(format!("\"{:#x}\"", value))
            },
            Value::Short(value) => if value < 0 {
                Ok(format!("\"-{:#x}\"", value))
            } else {
                Ok(format!("\"{:#x}\"", value))
            },
            Value::Int(value) => if value < 0 {
                Ok(format!("\"-{:#x}\"", value))
            } else {
                Ok(format!("\"{:#x}\"", value))
            },
            Value::Long(value) => if value < 0 {
                Ok(format!("\"-{:#x}\"", value))
            } else {
                Ok(format!("\"{:#x}\"", value))
            },
            Value::Float(value) => {
                Ok(format!("\"{:#x}\"", value.0.to_bits()))
            },
            Value::Double(value) => {
                Ok(format!("\"{:#x}\"", value.0.to_bits()))
            },
            Value::Decimal32(value) => Ok(format!("\"0x{}\"", value.into_inner().encode_hex::<String>())),
            Value::Decimal64(value) => Ok(format!("\"0x{}\"", value.into_inner().encode_hex::<String>())),
            Value::Decimal128(value) => Ok(format!("\"0x{}\"", value.into_inner().encode_hex::<String>())),
            Value::Char(value) => todo!(),
            Value::Timestamp(value) => Ok(format!("\"{:#x}\"", value.into_inner())),
            Value::Uuid(value) => Ok(uuid::Uuid::from_bytes(value.into_inner()).hyphenated().to_string()),
            Value::Binary(value) => serde_json::to_string(&value).map_err(Into::into),
            Value::String(value) => Ok(value),
            Value::Symbol(value) => Ok(value.0),
            Value::Described(_) => todo!(),
            Value::List(_) => todo!(),
            Value::Map(_) => todo!(),
            Value::Array(_) => todo!(),
        }
    }
}

impl IntoTestJson for Vec<Value> {
    fn into_test_json(self) -> Result<String> {
        let mut s = String::new();
        s.push('[');
        for (i, item) in self.into_iter().enumerate() {
            if i > 0 {
                s.push_str(", ")
            }
            s.push_str(item.into_test_json()?.as_str())
        }
        s.push(']');
        Ok(s)
    }
}
