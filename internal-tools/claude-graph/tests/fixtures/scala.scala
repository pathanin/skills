package app
class Transfer(path: String) {
  def send(): Unit = { }
}
object Transfer {
  def apply(p: String) = new Transfer(p)
}
trait Encoder {
  def encode(): Unit
}
case class Options(retries: Int)
