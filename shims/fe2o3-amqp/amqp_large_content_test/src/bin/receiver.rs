use std::{collections::VecDeque, env};

use amqp_large_content_test::{MessageSizesInMb, TotalAndChunks, MEGABYTE};
use anyhow::{anyhow, Ok, Result};
use fe2o3_amqp::{
    types::primitives::{Binary, OrderedMap, Symbol},
    Connection, Delivery, Receiver, Session,
};

struct TestReceiver {
    broker_addr: String,
    source_addr: String,
    type_name: String,
    num_expected: usize,
}

impl TestReceiver {
    async fn run(self) -> Result<MessageSizesInMb> {
        let mut connection = Connection::open(
            "fe2o3-amqp-amqp-large-content-test-receiver-connection",
            format!("amqp://{}", self.broker_addr).as_str(),
        )
        .await?;
        let mut session = Session::begin(&mut connection).await?;
        let mut receiver = Receiver::attach(
            &mut session,
            "fe2o3-amqp-amqp-large-content-test-receiver",
            self.source_addr,
        )
        .await?;

        let sizes = recv_and_count_size(&mut receiver, &self.type_name, self.num_expected).await?;

        receiver.close().await?;
        session.end().await?;
        connection.close().await?;

        Ok(sizes)
    }
}

async fn recv_and_count_size(
    receiver: &mut Receiver,
    type_name: &str,
    num_expected: usize,
) -> Result<MessageSizesInMb> {
    match type_name {
        "binary" => recv_binary(receiver, num_expected).await,
        "string" => recv_string(receiver, num_expected).await,
        "symbol" => recv_symbol(receiver, num_expected).await,
        "list" => recv_list(receiver, num_expected).await,
        "map" => recv_map(receiver, num_expected).await,
        _ => Err(anyhow!("type {} Not implemented", type_name)),
    }
}

async fn recv_binary(receiver: &mut Receiver, num_expected: usize) -> Result<MessageSizesInMb> {
    let mut v = VecDeque::new();
    for _ in 0..num_expected {
        let delivery: Delivery<Binary> = receiver.recv().await?;
        receiver.accept(&delivery).await?;

        let b = delivery.try_into_value()?;
        v.push_back(b.len() / MEGABYTE)
    }
    Ok(MessageSizesInMb::Binary(v))
}

async fn recv_string(receiver: &mut Receiver, num_expected: usize) -> Result<MessageSizesInMb> {
    let mut v = VecDeque::new();
    for _ in 0..num_expected {
        let delivery: Delivery<String> = receiver.recv().await?;
        receiver.accept(&delivery).await?;

        let s = delivery.try_as_value()?;
        v.push_back(s.len() / MEGABYTE)
    }
    Ok(MessageSizesInMb::String(v))
}

async fn recv_symbol(receiver: &mut Receiver, num_expected: usize) -> Result<MessageSizesInMb> {
    let mut v = VecDeque::new();
    for _ in 0..num_expected {
        let delivery: Delivery<Symbol> = receiver.recv().await?;
        receiver.accept(&delivery).await?;

        let s = delivery.try_into_value()?;
        v.push_back(s.0.len() / MEGABYTE)
    }
    Ok(MessageSizesInMb::Symbol(v))
}

// fn format_output(sizes: )

async fn recv_list(receiver: &mut Receiver, num_expected: usize) -> Result<MessageSizesInMb> {
    let mut v: VecDeque<TotalAndChunks> = VecDeque::new();
    for _ in 0..num_expected {
        let delivery: Delivery<Vec<String>> = receiver.recv().await?;
        receiver.accept(&delivery).await?;

        let s = delivery.try_into_value()?;

        let total_in_bytes: usize = s.iter().map(|e| e.len()).sum();
        let total_in_mb = total_in_bytes / MEGABYTE;
        let num_chunks = s.len();

        append_total_and_chunks(&mut v, total_in_mb, num_chunks);
    }
    Ok(MessageSizesInMb::List(v))
}

async fn recv_map(receiver: &mut Receiver, num_expected: usize) -> Result<MessageSizesInMb> {
    let mut v: VecDeque<TotalAndChunks> = VecDeque::new();
    for _ in 0..num_expected {
        let delivery: Delivery<OrderedMap<String, String>> = receiver.recv().await?;
        receiver.accept(&delivery).await?;

        let map = delivery.try_into_value()?;
        let num_chunks = map.len();
        let total_in_bytes: usize = map.values().map(|e| e.len()).sum();
        let total_in_mb = total_in_bytes / MEGABYTE;

        append_total_and_chunks(&mut v, total_in_mb, num_chunks);
    }
    Ok(MessageSizesInMb::Map(v))
}

fn append_total_and_chunks(
    v: &mut VecDeque<TotalAndChunks>,
    total_in_mb: usize,
    num_chunks: usize,
) {
    match v.back_mut() {
        Some(el) => {
            if total_in_mb == el.0 {
                el.1.push_back(num_chunks);
            } else {
                let el = TotalAndChunks(total_in_mb, vec![num_chunks].into_iter().collect());
                v.push_back(el)
            }
        }
        None => {
            let el = TotalAndChunks(total_in_mb, vec![num_chunks].into_iter().collect());
            v.push_back(el)
        }
    }
}

impl TryFrom<Vec<String>> for TestReceiver {
    type Error = anyhow::Error;

    fn try_from(mut value: Vec<String>) -> Result<Self, Self::Error> {
        let mut drain = value.drain(1..);

        let broker_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let source_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let type_name = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let num_expected = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let num_expected: usize = num_expected.parse()?;

        Ok(Self {
            broker_addr,
            source_addr,
            type_name,
            num_expected,
        })
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    let type_name = args[3].clone();
    let test_receiver = TestReceiver::try_from(args)?;
    // tokio::time::timeout(std::time::Duration::from_secs(20), test_receiver.run()).await??;
    let sizes = test_receiver.run().await?;

    println!("{}", type_name);
    println!("{}", sizes.to_output_string()?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use amqp_large_content_test::{MessageSizesInMb, TotalAndChunks};

    #[test]
    fn test_formatting_total_and_chunks() {
        let value = TotalAndChunks(1, vec![1, 2, 4].into_iter().collect());
        let value = MessageSizesInMb::List(vec![value].into_iter().collect());
        println!("{:?}", value.to_output_string())
    }
}
