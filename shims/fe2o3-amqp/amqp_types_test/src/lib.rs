use std::str::FromStr;

use anyhow::{anyhow, Ok, Result};
use fe2o3_amqp::types::primitives::{
    Binary, Byte, Dec128, Dec32, Dec64, Int, Long, Short, Symbol, Timestamp, UByte, UInt, ULong,
    UShort, Uuid, Value,
};
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
    List,
    Map,
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
            "list" => Ok(Self::List),
            "map" => Ok(Self::Map),
            _ => Err(anyhow!("Type not impelmented")),
        }
    }
}

macro_rules! parse_number {
    ($str:ident, $val_ty:ident) => {
        <$val_ty>::from_str_radix($str.replace("0x", "").as_str(), 16).map(|v| Value::$val_ty(v))
    };
}

fn parse_boolean(mut s: String) -> Result<bool> {
    let (head, tail) = s.split_at_mut(1);
    let s = format!("{}{}", head.to_lowercase(), tail);
    from_str(s.as_str()).map_err(Into::into)
}

pub fn parse_test_json(amqp_type: AmqpType, input: String) -> Result<Vec<Value>> {
    let jsons: Vec<String> = from_str(&input)?;

    match amqp_type {
        AmqpType::Null => jsons
            .into_iter()
            .map(|s| s.replace("None", "null"))
            .map(|s| from_str::<()>(s.as_str()).map(|_| Value::Null))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Bool => jsons
            .into_iter()
            .map(|s| parse_boolean(s).map(Value::Bool))
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

            jsons
                .into_iter()
                .map(|s| {
                    <[u8; 4]>::from_hex(s.replace("0x", ""))
                        .map(Dec32::from)
                        .map(Value::Decimal32)
                })
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        }
        AmqpType::Decimal64 => {
            use hex::FromHex;

            jsons
                .into_iter()
                .map(|s| {
                    <[u8; 8]>::from_hex(s.replace("0x", ""))
                        .map(Dec64::from)
                        .map(Value::Decimal64)
                })
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        }
        AmqpType::Decimal128 => {
            use hex::FromHex;

            jsons
                .into_iter()
                .map(|s| {
                    <[u8; 16]>::from_hex(s.replace("0x", ""))
                        .map(Dec128::from)
                        .map(Value::Decimal128)
                })
                .collect::<Result<Vec<Value>, _>>()
                .map_err(Into::into)
        }
        AmqpType::Char => jsons
            .into_iter()
            .map(|s| {
                if s.len() == 1 {
                    s.chars()
                        .next()
                        .map(Value::Char)
                        .ok_or(anyhow!("Not enough bytes"))
                } else {
                    u32::from_str_radix(s.replace("0x", "").as_str(), 16).map(|val| {
                        char::from_u32(val)
                            .ok_or(anyhow!("Only unicode scalar values are valid chars"))
                            .map(Value::Char)
                    })?
                }
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Timestamp => jsons
            .into_iter()
            .map(|s| {
                i64::from_str_radix(s.replace("0x", "").as_str(), 16)
                    .map(|v| Value::Timestamp(Timestamp::from(v)))
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Uuid => jsons
            .into_iter()
            .map(|s| {
                uuid::Uuid::from_str(s.as_str()).map(|v| Value::Uuid(Uuid::from(v.into_bytes())))
            })
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::Binary => jsons
            .into_iter()
            .map(|s| base64::decode(s).map(|v| Value::Binary(Binary::from(v))))
            .collect::<Result<Vec<Value>, _>>()
            .map_err(Into::into),
        AmqpType::String => Ok(jsons
            .into_iter()
            .map(|s| Value::String(s))
            .collect::<Vec<Value>>()),
        AmqpType::Symbol => Ok(jsons
            .into_iter()
            .map(|s| Value::Symbol(Symbol(s)))
            .collect::<Vec<Value>>()),
        AmqpType::List => unreachable!(),
        AmqpType::Map => unreachable!(),
    }
}

pub trait IntoTestJson {
    fn into_test_json(self) -> String;
}

macro_rules! format_signed {
    ($val:ident, $val_ty:ty) => {
        if $val < 0 {
            if $val == <$val_ty>::MIN {
                format!("-{:#x}", $val)
            } else {
                format!("-{:#x}", -$val)
            }
        } else {
            format!("{:#x}", $val)
        }
    };
}

impl IntoTestJson for Value {
    fn into_test_json(self) -> String {
        let s = match self {
            Value::Null => String::from("None"),
            Value::Bool(value) => match value {
                true => "True".to_string(),
                false => "False".to_string(),
            },
            Value::UByte(value) => format!("{:#x}", value),
            Value::UShort(value) => format!("{:#x}", value),
            Value::UInt(value) => format!("{:#x}", value),
            Value::ULong(value) => format!("{:#x}", value),
            Value::Byte(value) => format_signed!(value, Byte),
            Value::Short(value) => format_signed!(value, Short),
            Value::Int(value) => format_signed!(value, Int),
            Value::Long(value) => format_signed!(value, Long),
            Value::Float(value) => format!("{:#010x}", value.0.to_bits()),
            Value::Double(value) => format!("{:#018x}", value.0.to_bits()),
            Value::Decimal32(value) => {
                format!("0x{}", value.into_inner().encode_hex::<String>())
            }
            Value::Decimal64(value) => {
                format!("0x{}", value.into_inner().encode_hex::<String>())
            }
            Value::Decimal128(value) => {
                format!("0x{}", value.into_inner().encode_hex::<String>())
            }
            Value::Char(value) => {
                if value.is_ascii_graphic() || value.is_whitespace() {
                    value.to_string()
                } else {
                    let utf32 = u32::from(value);
                    format!("{:#x}", utf32)
                }
            }
            Value::Timestamp(value) => format!("{:#x}", value.into_inner()),
            Value::Uuid(value) => {
                let s = uuid::Uuid::from_bytes(value.into_inner())
                    .hyphenated()
                    .to_string();
                format!("{}", s)
            }
            Value::Binary(value) => {
                format!("{}", base64::encode(value.into_vec()))
            }
            Value::String(value) => value,
            Value::Symbol(value) => format!("{}", value.0),

            // The following types are not included in the test
            Value::List(_) => unreachable!(),
            Value::Map(_) => unreachable!(),
            Value::Array(_) => unreachable!(),
            Value::Described(_) => unreachable!(),
        };
        // Only Debug format is recognized
        format!("{:?}", s)
    }
}

impl IntoTestJson for Vec<Value> {
    fn into_test_json(self) -> String {
        let mut s = String::new();
        s.push('[');
        for (i, item) in self.into_iter().enumerate() {
            if i > 0 {
                s.push(',');
                s.push(' ');
            }
            s.push_str(&item.into_test_json())
        }
        s.push(']');
        s
    }
}

#[cfg(test)]
mod tests {
    use fe2o3_amqp::types::primitives::Value;

    use crate::IntoTestJson;

    #[test]
    fn test_char_output_format() {
        let input = [
            ' ',
            'A',
            'z',
            '0',
            '9',
            '}',
            '\u{0}',
            '\u{1}',
            '\u{7f}',
            '\u{80}',
            '\u{ff}',
            '\u{16b5}',
            '\u{10203}',
            '\u{10ffff}',
        ];

        let values: Vec<Value> = input.into_iter().map(Value::Char).collect();
        let expected = r#"[" ", "A", "z", "0", "9", "}", "0x0", "0x1", "0x7f", "0x80", "0xff", "0x16b5", "0x10203", "0x10ffff"]"#;
        assert_eq!(expected, values.into_test_json());
    }
}
