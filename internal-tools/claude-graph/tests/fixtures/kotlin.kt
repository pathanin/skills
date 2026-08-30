package app
class RelayClient(val host: String) {
    fun connect() { }
    companion object { fun create() = RelayClient("") }
}
interface Listener { fun onEvent() }
data class Config(val port: Int)
fun topLevelHelper() { }
object Registry { }
