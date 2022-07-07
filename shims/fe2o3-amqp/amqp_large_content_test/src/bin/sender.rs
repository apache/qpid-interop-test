use std::{env, collections::VecDeque};

use amqp_large_content_test::MEGABYTE;
use anyhow::{anyhow, Result};
use fe2o3_amqp::{
    types::{
        messaging::Message,
        primitives::{Binary, Symbol, Value},
    },
    Connection, Sender, Session,
};
use serde::{Deserialize, Serialize};
use serde_json::from_str;

#[derive(Debug, Serialize, Deserialize)]
struct SizeInMb(usize, Vec<usize>);

#[derive(Debug)]
struct TestSender {
    broker_addr: String,
    target_addr: String,
    message_iter: MessageIter,
}

impl TestSender {
    async fn run(self) -> Result<()> {
        let mut connection = Connection::open(
            "fe2o3-amqp-amqp-large-content-test-sender-connection",
            format!("amqp://{}", self.broker_addr).as_str(),
        )
        .await?;
        let mut session = Session::begin(&mut connection).await?;
        let mut sender = Sender::attach(
            &mut session,
            "fe2o3-amqp-amqp-large-content-test-sender",
            self.target_addr,
        )
        .await?;

        for message in self.message_iter.into_iter() {
            // println!("sending new message");
            let _outcome = sender.send(message).await?;
        }

        sender.close().await?;
        session.end().await?;
        connection.close().await?;
        Ok(())
    }
}

impl TryFrom<Vec<String>> for TestSender {
    type Error = anyhow::Error;

    fn try_from(mut value: Vec<String>) -> Result<Self, Self::Error> {
        let mut drain = value.drain(1..);

        let broker_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let target_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let type_name = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let input = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;

        let message_iter = create_message_sizes(&type_name, &input)?;

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
    List { total_size: usize, num_elem: usize },
    Map { total_size: usize, num_elem: usize },
}

fn create_message_sizes(type_name: &str, input: &str) -> Result<MessageIter> {
    let sizes: VecDeque<MessageSizeInMb> = match type_name {
        "binary" => {
            let sizes: Vec<usize> = from_str(input)?;
            sizes
                .into_iter()
                .map(|s| MessageSizeInMb::Binary(s))
                .collect()
        }
        "string" => {
            let sizes: Vec<usize> = from_str(input)?;
            sizes
                .into_iter()
                .map(|s| MessageSizeInMb::String(s))
                .collect()
        }
        "symbol" => {
            let sizes: Vec<usize> = from_str(input)?;
            sizes
                .into_iter()
                .map(|s| MessageSizeInMb::Symbol(s))
                .collect()
        }

        "list" => {
            let sizes: Vec<SizeInMb> = from_str(input)?;
            sizes
                .into_iter()
                .map(|s| {
                    s.1.into_iter()
                        .map(|num_elem| MessageSizeInMb::List {
                            total_size: s.0,
                            num_elem,
                        })
                        .collect::<Vec<MessageSizeInMb>>()
                })
                .flatten()
                .collect()
        }
        "map" => {
            let sizes: Vec<SizeInMb> = from_str(input)?;
            sizes
                .into_iter()
                .map(|s| {
                    s.1.into_iter()
                        .map(|num_elem| MessageSizeInMb::Map {
                            total_size: s.0,
                            num_elem,
                        })
                        .collect::<Vec<MessageSizeInMb>>()
                })
                .flatten()
                .collect()
        }
        _ => unreachable!(),
    };

    Ok(MessageIter { sizes })
}

#[derive(Debug)]
struct MessageIter {
    sizes: VecDeque<MessageSizeInMb>,
}

impl Iterator for MessageIter {
    type Item = Message<Value>;

    fn next(&mut self) -> Option<Self::Item> {
        self.sizes.pop_front().map(|size| generate_message(size))
    }
}

fn generate_message(size: MessageSizeInMb) -> Message<Value> {
    match size {
        MessageSizeInMb::Binary(total_in_mb) => {
            let binary = Binary::from(vec![b'b'; total_in_mb * MEGABYTE]);
            Message::builder().value(Value::Binary(binary)).build()
        }
        MessageSizeInMb::String(total_in_mb) => {
            let buf = vec![b's'; total_in_mb * MEGABYTE];
            let s = String::from_utf8_lossy(&buf);
            Message::builder()
                .value(Value::String(s.to_string()))
                .build()
        }
        MessageSizeInMb::Symbol(total_in_mb) => {
            let buf = vec![b'y'; total_in_mb * MEGABYTE];
            let s = Symbol::new(String::from_utf8_lossy(&buf));
            Message::builder().value(Value::Symbol(s)).build()
        }
        MessageSizeInMb::List {
            total_size,
            num_elem,
        } => todo!(),
        MessageSizeInMb::Map {
            total_size,
            num_elem,
        } => todo!(),
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    let test_sender = TestSender::try_from(args)?;

    test_sender.run().await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use serde_json::{from_slice, to_string};

    use crate::{SizeInMb, create_message_sizes};

    #[test]
    fn test_deserialize_size_in_mb() {
        let buf = "[1, 10]";
        let sizes_in_mb: Vec<usize> = serde_json::from_str(buf).unwrap();

        let buf = "[[1, [1, 16, 256, 4096]], [10, [1, 16, 256, 4096]]]";
        let sizes_in_mb: Vec<SizeInMb> = serde_json::from_str(buf).unwrap();
        // println!("{:?}", buf);
    }

    #[test]
    fn test_generator() {
        let mut iter = create_message_sizes("binary", "[1]").unwrap();

        println!("{:?}", iter);

        let msg = iter.next();
        println!("{:?}", msg.is_some());

        let msg = iter.next();
        println!("{:?}", msg.is_some());
    }
}
