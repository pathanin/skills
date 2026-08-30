class PeerConnection {
  void connect(String host) { }
  static PeerConnection create() { }
}
abstract class Encoder {
  void encode();
}
enum State { idle, active }
void globalHelper() { }

// Top-level state. Dart declares most of it as `final`, not const/let/var.
final activityProvider = FutureProvider.autoDispose((ref) => ref.read(api));

// `const <Type> name` — the reverse of Go's `const Name Type`.
const bool mockDmDirectoryEnabled = false;
const String customEmojiSetDTag = 'buzz:custom-emoji';

// Nullable return type.
ReadStateBlob? decodeReadStateBlob(String plaintext) { }

// Expression body instead of a brace.
String threadContextKey(String rootId) => 'thread:$rootId';

// Trailing async before the brace.
Future<void> refreshChannels() async { }

// Named parameters put a brace inside the signature, over several lines.
void showEmojiPicker({
  required BuildContext context,
  required void Function(String emoji) onSelect,
}) { }

// A function-typed parameter nests parens inside the signature.
Future<void> processCapturedImage(
  XFile image,
  Future<void> Function(XFile image) onCapture,
) async { }

extension AppThemeExtension on BuildContext { }
