use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

pub const MEGABYTE: usize = 1024 * 1024;

#[derive(Debug, Serialize, Deserialize)]
pub struct TotalAndChunks(pub usize, pub VecDeque<usize>);

#[derive(Debug, Serialize, Deserialize)]
pub enum MessageSizesInMb {
    Binary(VecDeque<usize>),
    String(VecDeque<usize>),
    Symbol(VecDeque<usize>),
    List(VecDeque<TotalAndChunks>),
    Map(VecDeque<TotalAndChunks>),
}

impl MessageSizesInMb {
    pub fn to_output_string(self) -> Result<String> {
        match self {
            MessageSizesInMb::Binary(value)
            | MessageSizesInMb::String(value)
            | MessageSizesInMb::Symbol(value) => serde_json::to_string(&value)
                .map(|s| s.replace(",", ", "))
                .map_err(Into::into),
            MessageSizesInMb::List(value) | MessageSizesInMb::Map(value) => {
                serde_json::to_string(&value)
                    .map(|s| s.replace(",", ", "))
                    .map_err(Into::into)
            }
        }
    }
}
