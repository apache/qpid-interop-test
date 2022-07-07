use std::env;

use fe2o3_amqp::types::primitives::Value;
use serde::{Deserialize, Serialize};
use serde_json::from_str;
use anyhow::{Result, anyhow};

#[derive(Debug, Serialize, Deserialize)]
struct SizeInMb(usize, Vec<usize>);

#[derive(Debug)]
struct TestSender {
    broker_addr: String,
    target_addr: String,
    message_iter: MessageIter,
}

impl TryFrom<Vec<String>> for TestSender {
    type Error = anyhow::Error;

    fn try_from(mut value: Vec<String>) -> Result<Self, Self::Error> {
        let mut drain = value.drain(1..);

        let broker_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let target_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let type_name = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let input = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;

        let message_iter = create_messages(&type_name, &input)?;

        Ok(Self {
            broker_addr,
            target_addr,
            message_iter,
        })
    }
}

#[derive(Debug)]
enum MessageSizeInMb {
    Binary(usize),
    String(usize),
    Symbol(usize),
    List {
        total_size: usize,
        num_elem: usize,
    },
    Map {
        total_size: usize,
        num_elem: usize,
    }
}

#[derive(Debug)]
struct MessageIter {
    sizes: Vec<MessageSizeInMb>
}

fn create_messages(type_name: &str, input: &str) -> Result<MessageIter> {
    let sizes: Vec<MessageSizeInMb> = match type_name {
        "binary" => {
            let sizes: Vec<usize> = from_str(input)?;
            sizes.into_iter().map(|s| MessageSizeInMb::Binary(s)).collect()
        },
        "string" => {
            let sizes: Vec<usize> = from_str(input)?;
            sizes.into_iter().map(|s| MessageSizeInMb::String(s)).collect()
        },
        "symbol" => {
            let sizes: Vec<usize> = from_str(input)?;
            sizes.into_iter().map(|s| MessageSizeInMb::Symbol(s)).collect()
        },

        "list" => {
            let sizes: Vec<SizeInMb> = from_str(input)?;
            sizes.into_iter().map(|s| {
                s.1.into_iter().map(|num_elem| MessageSizeInMb::List { total_size: s.0, num_elem }).collect::<Vec<MessageSizeInMb>>()
            }).flatten().collect()
        },
        "map" => {
            let sizes: Vec<SizeInMb> = from_str(input)?;
            sizes.into_iter().map(|s| {
                s.1.into_iter().map(|num_elem| MessageSizeInMb::Map { total_size: s.0, num_elem }).collect::<Vec<MessageSizeInMb>>()
            }).flatten().collect()
        },
        _ => unreachable!()
    };

    Ok(MessageIter { sizes })
}

#[tokio::main]
async fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    println!("{:?}", args);
    let test_sender = TestSender::try_from(args)?;
    println!("{:?}", test_sender);

    Ok(())
}

#[cfg(test)]
mod tests {
    use serde_json::{to_string, from_slice};

    use crate::SizeInMb;

    #[test]
    fn test_deserialize_size_in_mb() {
        let buf  = "[1, 10]";
        let sizes_in_mb: Vec<usize> = serde_json::from_str(buf).unwrap();

        let buf = "[[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]]]";
        let sizes_in_mb: Vec<SizeInMb> = serde_json::from_str(buf).unwrap();
        // println!("{:?}", buf);
    }
}