package com.example;
public class TransferManager {
    private int count;
    public void startTransfer(String id) { }
    public static TransferManager getInstance() { return null; }

    // Constants carry modifiers AND a type before the name.
    private static final int PING_INTERVAL = 30;
    static final Logger LOGGER = Logger.getLogger(TransferManager.class.getName());
    private static final Map<String, String> HEADER_DEFAULTS = new HashMap<>();

    public void close() throws IOException { }

    void register() {
        scanner.scan(base, new FileVisitor() {
            // An anonymous inner class puts real declarations past column 8.
            @Override
            public void beforeRequest(Map<String, List<String>> headers) { }

            @Override
            public void afterResponse(HandshakeResponse hr) {
                if (hr.shouldRetry(count)) { }
            }
        });
    }
}
interface PeerListener {
    void onConnect();
}
enum Phase { INIT, RUNNING }
