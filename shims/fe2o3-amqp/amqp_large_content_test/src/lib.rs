use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

pub const MEGABYTE: usize = 1024 * 1024;

#[derive(Debug, Serialize, Deserialize)]
pub struct TotalAndChunks {
    pub total_in_mb: usize,
    pub num_chunks: VecDeque<usize>,
}

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

#[cfg(test)]
mod tests {
    use crate::MessageSizesInMb;

    #[test]
    fn it_works() {
        let value = MessageSizesInMb::Binary(vec![1, 2, 3].into_iter().collect());
        println!("{}", value.to_output_string().unwrap())
    }
}
