use std::env;

use anyhow::{anyhow, Result};
use fe2o3_amqp::{Connection, Receiver, Session, Delivery, types::primitives::Value};

struct TestReceiver {
    broker_addr: String,
    source_addr: String,
    type_name: String,
    num_expected: usize,
}

impl TestReceiver {
    async fn run(self) -> Result<()> {
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

        for _ in 0..self.num_expected {
            let delivery: Delivery<Value> = receiver.recv().await?;
            receiver.accept(&delivery).await?;
            println!("received something");
        }

        receiver.close().await?;
        session.end().await?;
        connection.close().await?;

        Ok(())
    }
}

// async fn recv_binary(receiver: &mut Receiver) -> 

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
    println!("{:?}", args);
    let test_receiver = TestReceiver::try_from(args)?;
    tokio::time::timeout(std::time::Duration::from_secs(20), test_receiver.run()).await??;

    Ok(())
}
