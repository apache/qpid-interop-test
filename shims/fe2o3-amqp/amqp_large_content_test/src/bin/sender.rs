use std::{env, collections::{VecDeque, BTreeMap}};

use amqp_large_content_test::{MEGABYTE, MessageSizesInMb, TotalAndChunks};
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

fn create_message_sizes(type_name: &str, input: &str) -> Result<MessageIter> {
    match type_name {
        "binary" => {
            let sizes: VecDeque<usize> = from_str(input)?;
            let sizes = MessageSizesInMb::Binary(sizes);
            Ok(MessageIter { sizes })
        }
        "string" => {
            let sizes: VecDeque<usize> = from_str(input)?;
            let sizes = MessageSizesInMb::String(sizes);
            Ok(MessageIter { sizes })
        }
        "symbol" => {
            let sizes: VecDeque<usize> = from_str(input)?;
            let sizes = MessageSizesInMb::Symbol(sizes);
            Ok(MessageIter { sizes })
        }

        "list" => {
            let sizes: VecDeque<TotalAndChunks> = from_str(input)?;
            let sizes = MessageSizesInMb::List(sizes);
            Ok(MessageIter { sizes })
        }
        "map" => {
            let sizes: VecDeque<TotalAndChunks> = from_str(input)?;
            let sizes = MessageSizesInMb::Map(sizes);
            Ok(MessageIter { sizes })
        }
        _ => unreachable!(),
    }
}

#[derive(Debug)]
struct MessageIter {
    sizes: MessageSizesInMb,
}

impl Iterator for MessageIter {
    type Item = Message<Value>;

    fn next(&mut self) -> Option<Self::Item> {
        match &mut self.sizes {
            MessageSizesInMb::Binary(sizes) => {
                sizes.pop_front().map(|size| {
                    let value = Value::Binary(Binary::from(vec![b'b'; size * MEGABYTE]));
                    Message::builder().value(value).build()
                })
            },
            MessageSizesInMb::String(sizes) => {
                sizes.pop_front().map(|size| {
                    let buf = vec![b's'; size * MEGABYTE];
                    let s = String::from_utf8_lossy(&buf);
                    let value = Value::String(s.to_string());
                    Message::builder().value(value).build()
                })
            },
            MessageSizesInMb::Symbol(sizes) => {
                sizes.pop_front().map(|size| {
                    let buf = vec![b'y'; size * MEGABYTE];
                    let s = Symbol::new(String::from_utf8_lossy(&buf));
                    let value = Value::Symbol(s);
                    Message::builder().value(value).build()
                })
            },
            MessageSizesInMb::List(sizes) => {
                match sizes.get_mut(0).map(|size| (size.total_in_mb, size.num_chunks.pop_front())) {
                    Some((total_in_mb, Some(num_chunks))) => {
                        let total_in_bytes = total_in_mb * MEGABYTE;
                        let size_per_chunk = total_in_bytes / num_chunks;
                        let chunk_buf = vec![b's'; size_per_chunk];
                        let chunk = String::from_utf8_lossy(&chunk_buf);
                        let list = vec![Value::String(chunk.to_string()); num_chunks];
                        let value = Value::List(list);
                        Some(Message::builder().value(value).build())
                    },
                    Some((_, None)) => {
                        let _ = sizes.pop_front();
                        self.next()
                    },
                    None => None,
                }
            },
            MessageSizesInMb::Map(sizes) => {
                match sizes.get_mut(0).map(|size| (size.total_in_mb, size.num_chunks.pop_front())) {
                    Some((total_in_mb, Some(num_chunks))) => {
                        let total_in_bytes = total_in_mb * MEGABYTE;
                        let size_per_chunk = total_in_bytes / num_chunks;
                        let chunk_buf = vec![b's'; size_per_chunk];
                        let chunk = String::from_utf8_lossy(&chunk_buf);
                        let mut map = BTreeMap::new();

                        for i in 0.. num_chunks {
                            let key = Value::String(i.to_string());
                            let value = Value::String(chunk.to_string());
                            map.insert(key, value);
                        }

                        Some(Message::builder().value(Value::Map(map)).build())
                    },
                    Some((_, None)) => {
                        let _ = sizes.pop_front();
                        self.next()
                    },
                    None => None,
                }
            },
        }
    }
}

// fn generate_message(size: MessageSizesInMb) -> Message<Value> {
//     match size {
//         MessageSizesInMb::Binary(total_in_mb) => {
//             let binary = Binary::from(vec![b'b'; total_in_mb * MEGABYTE]);
//             Message::builder().value(Value::Binary(binary)).build()
//         }
//         MessageSizesInMb::String(total_in_mb) => {
//             let buf = vec![b's'; total_in_mb * MEGABYTE];
//             let s = String::from_utf8_lossy(&buf);
//             Message::builder()
//                 .value(Value::String(s.to_string()))
//                 .build()
//         }
//         MessageSizesInMb::Symbol(total_in_mb) => {
//             let buf = vec![b'y'; total_in_mb * MEGABYTE];
//             let s = Symbol::new(String::from_utf8_lossy(&buf));
//             Message::builder().value(Value::Symbol(s)).build()
//         }
//         MessageSizesInMb::List {
//             total_size,
//             num_elem,
//         } => todo!(),
//         MessageSizesInMb::Map {
//             total_size,
//             num_elem,
//         } => todo!(),
//     }
// }

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
