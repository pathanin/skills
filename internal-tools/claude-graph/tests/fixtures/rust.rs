pub fn connect_peer(a: &str) -> Result<()> {
    Ok(())
}
pub struct RelayConfig {
    pub port: u16,
}
impl RelayConfig {
    pub fn new() -> Self { Self { port: 0 } }
}
pub enum TransferState { Idle, Active }
pub trait Encoder { fn encode(&self); }
const MAX_RETRIES: u32 = 5;
pub type HookCallback = Box<dyn Fn() -> bool>;
pub(crate) const MAX_QUEUE: usize = 10;
pub(super) const RETRY_DELAY_MS: u64 = 100;
