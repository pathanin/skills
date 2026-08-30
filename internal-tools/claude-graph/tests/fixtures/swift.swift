import Foundation
class PeerConnection {
    func connect(to host: String) { }
    static func shared() -> PeerConnection { }
}
struct TransferOptions {
    var retries: Int
}
enum State { case idle, active }
protocol Encodable2 { func encode() }
func globalHelper() { }
