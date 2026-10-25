# newsletter

Subscriber-list import worker. When a customer uploads a CSV of addresses,
`newsletter.worker.run_import` merges it into their existing list.
Jobs that exceed `JOB_TIMEOUT_SECONDS` are failed and the customer sees
"Import timed out, try a smaller file".

The merged list keeps existing subscribers first, in their original order,
followed by new addresses in upload order. Addresses are compared after
normalisation (trimmed, lowercased); invalid ones are skipped.
