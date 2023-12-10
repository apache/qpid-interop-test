use std::env;

use anyhow::{anyhow, Result};
use fe2o3_amqp::{types::primitives::Value, Connection, Sender, Session};

use amqp_types_test::{parse_test_json, AmqpType};

#[derive(Debug)]
struct TestSender {
    ip_addr: String,
    target_addr: String,
    values: Vec<Value>,
}

impl TestSender {
    async fn run(self) -> Result<()> {
        let mut connection = Connection::open(
            "fe2o3-amqp-amqp-types-test-sender-connection",
            format!("amqp://{}", self.ip_addr).as_str(),
        )
        .await?;
        let mut session = Session::begin(&mut connection).await?;
        let mut sender = Sender::attach(
            &mut session,
            "fe2o3-amqp-amqp-types-test-sender",
            self.target_addr,
        )
        .await?;

        for value in self.values {
            let _outcome = sender.send(value).await?;
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

        let ip_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let target_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let type_name = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let json = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;

        let amqp_type = AmqpType::try_from(type_name)?;
        let values = parse_test_json(amqp_type, json)?;

        Ok(Self {
            ip_addr,
            target_addr,
            values,
        })
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    let test_sender = TestSender::try_from(args)?;

    test_sender.run().await?;
    Ok(())
}
