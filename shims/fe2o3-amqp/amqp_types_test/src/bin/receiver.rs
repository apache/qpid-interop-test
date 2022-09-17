use std::env;

use anyhow::{anyhow, Result};

use amqp_types_test::{AmqpType, IntoTestJson};
use fe2o3_amqp::{
    link::BodyError, types::primitives::Value, Connection, Delivery, Receiver, Session,
};

struct TestReceiver {
    ip_addr: String,
    source_addr: String,
    _amqp_type: AmqpType,
    n: usize,
}

impl TestReceiver {
    async fn run(self) -> Result<Vec<Value>> {
        let mut connection = Connection::open(
            "fe2o3-amqp-amqp-types-test-receiver-connection",
            format!("amqp://{}", self.ip_addr).as_str(),
        )
        .await?;
        let mut session = Session::begin(&mut connection).await?;
        let mut receiver = Receiver::attach(
            &mut session,
            "fe2o3-amqp-amqp-types-test-receiver",
            self.source_addr,
        )
        .await?;

        let mut v: Vec<Value> = Vec::with_capacity(self.n);
        for _ in 0..self.n {
            let delivery: Delivery<Value> = receiver.recv().await?;
            receiver.accept(&delivery).await?;
            v.push(delivery.try_into_value().or_else(|err| match err {
                BodyError::IsEmpty => Ok(Value::Null),
                _ => Err(err),
            })?);
        }

        receiver.close().await?;
        session.end().await?;
        connection.close().await?;

        Ok(v)
    }
}

impl TryFrom<Vec<String>> for TestReceiver {
    type Error = anyhow::Error;

    fn try_from(mut value: Vec<String>) -> Result<Self, Self::Error> {
        let mut drain = value.drain(1..);

        let ip_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let source_addr = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let type_name = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;
        let n_str = drain.next().ok_or(anyhow!("Wrong number of arguments"))?;

        let amqp_type = AmqpType::try_from(type_name)?;
        let n = n_str.parse()?;

        Ok(Self {
            ip_addr,
            source_addr,
            _amqp_type: amqp_type,
            n,
        })
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    let typename = args[3].clone();
    let test_receiver = TestReceiver::try_from(args)?;
    let values = test_receiver.run().await?;

    println!("{}", typename);
    println!("{}", values.into_test_json());
    Ok(())
}
