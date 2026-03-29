# Releases · qdrant/qdrant · GitHub
v1.17.1
-------

Change log
----------

Improvements
------------

*   [milestone#46](https://github.com/qdrant/qdrant/milestone/46?closed=1) - Defer point updates, efficiently apply and optimize points with `prevent_unoptimized=true`
*   [#8188](https://github.com/qdrant/qdrant/pull/8188) - Make Gridstore flushes non-blocking to reduce search tail latencies
*   [#8235](https://github.com/qdrant/qdrant/pull/8235) - Improve performance of filtered search in case of singular payload value
*   [#8402](https://github.com/qdrant/qdrant/pull/8402) - Add request tracing ID into audit log
*   [#8460](https://github.com/qdrant/qdrant/pull/8460) - Propagate WAL errors instead of panicking during loading of shards
*   [#8301](https://github.com/qdrant/qdrant/pull/8301) - Allow peer to bootstrap with used URI if empty

Bug fixes
---------

*   [#8177](https://github.com/qdrant/qdrant/pull/8177) - GPU: fix raw Vulkan name pointer type
*   [#8193](https://github.com/qdrant/qdrant/pull/8193) - Fix creation of uninitialized shard key with replication factor > 1, fixing tiered multi-tenancy workflow
*   [#8217](https://github.com/qdrant/qdrant/pull/8217) - Prevent `min_should` panic on large amount of conditions
*   [#8179](https://github.com/qdrant/qdrant/pull/8179) - Fix for restore of cluster snapshots which creates unnecessary replicas in Partial state
*   [#8220](https://github.com/qdrant/qdrant/pull/8220) - Fix Server disconnected without sending a response error while performing concurrent ingestion using
*   [#8341](https://github.com/qdrant/qdrant/pull/8341) - Security patch to force snapshot recovery from snapshot directory only
*   [#8373](https://github.com/qdrant/qdrant/pull/8373) - Fix lock for collection-level operations during shard transfer
*   [#8438](https://github.com/qdrant/qdrant/pull/8438) - Do not fail on collection-level operations with dummy shard
*   [#8455](https://github.com/qdrant/qdrant/pull/8455) - Fix WAL reading issue introduced in 1.17.0
*   [#8454](https://github.com/qdrant/qdrant/pull/8454) - Fix another panic in WAL replay
*   [#8475](https://github.com/qdrant/qdrant/pull/8475) - Fix for WAL delta transfer: reject truncated recovery points before equal-pruning
*   [#8514](https://github.com/qdrant/qdrant/pull/8514) - Fix incorrect warning in geo-index
*   [#8374](https://github.com/qdrant/qdrant/pull/8374) - Prevent locking shard holder for a long time in slow stream records transfers
*   [#8480](https://github.com/qdrant/qdrant/pull/8480) - Fix panic in optimizer logging
*   [#8449](https://github.com/qdrant/qdrant/pull/8449) - Fix panic in chunked vector storage

Preview
-------

This features are not officially released yet, but available in the build:

*   [#8214](https://github.com/qdrant/qdrant/pull/8214) - Per-collection metrics in Prometheus
*   [#8498](https://github.com/qdrant/qdrant/pull/8498) - API for reading audit log entries
*   [#8469](https://github.com/qdrant/qdrant/pull/8469) - Maximum batch size config in strict mode

Edge
----

*   Rust Crate for Qdrant Edge v0.6.0 - [https://crates.io/crates/qdrant-edge](https://crates.io/crates/qdrant-edge)
*   Python Package for Qdrant Edge v0.6.0 - [https://pypi.org/project/qdrant-edge-py/](https://pypi.org/project/qdrant-edge-py/)

v1.17.0
-------

Change log
----------

Features 🏋️
------------

*   [milestone#38](https://github.com/qdrant/qdrant/milestone/38?closed=1) - Relevance Feedback ([docs](https://qdrant.tech/documentation/concepts/search-relevance/#relevance-feedback))
*   [milestone#44](https://github.com/qdrant/qdrant/milestone/44?closed=1) - API for detailed report on optimization progress and stages ([docs](https://qdrant.tech/documentation/concepts/optimizer/#optimization-monitoring))
*   [milestone#40](https://github.com/qdrant/qdrant/milestone/40?closed=1) - API for aggregated telemetry of the whole cluster ([docs](https://qdrant.tech/documentation/guides/monitoring/#cluster-wide-telemetry))
*   [milestone#43](https://github.com/qdrant/qdrant/milestone/43?closed=1) - Unlimited update queue to gracefully smooth update spikes ([docs](https://qdrant.tech/documentation/guides/low-latency-search/))
*   [#8071](https://github.com/qdrant/qdrant/pull/8071) - Add Audit Access Logging ([docs](https://qdrant.tech/documentation/guides/security/#audit-logging))
*   [#8063](https://github.com/qdrant/qdrant/pull/8063) - Add Weighted RRF ([docs](https://qdrant.tech/documentation/concepts/hybrid-queries/#reciprocal-rank-fusion-rrf))
*   [#7643](https://github.com/qdrant/qdrant/pull/7643) - Add config option to control update throughput and prevent unoptimized searches ([docs](https://qdrant.tech/documentation/guides/low-latency-search/))
*   [#7929](https://github.com/qdrant/qdrant/pull/7929) - Add configurable read fan-out delay for dealing with tail latency in distributed clusters ([docs](https://qdrant.tech/documentation/guides/low-latency-search/#use-delayed-fan-outs))
*   [#7963](https://github.com/qdrant/qdrant/pull/7963) - For upserts, add `update_mode` parameter to either `upsert`, `update` or `insert` ([docs](https://qdrant.tech/documentation/concepts/points/#update-mode))
*   [#7835](https://github.com/qdrant/qdrant/pull/7835) - Add secondary API key configuration for zero downtime key rotation in distributed clusters
*   [#7838](https://github.com/qdrant/qdrant/pull/7838) - Add dedicated HTTP port for `/metrics` endpoint for internal monitoring
*   [#7615](https://github.com/qdrant/qdrant/pull/7615) - Add API to list shard keys ([docs](https://qdrant.tech/documentation/guides/distributed_deployment/#user-defined-sharding))

Improvements 🤸
---------------

*   [#7802](https://github.com/qdrant/qdrant/pull/7802) - Improve timeout handling on read operations
*   [#7750](https://github.com/qdrant/qdrant/pull/7750) - Improve timeout handling in update operations, prevent shard failures in case of timed out updates after WAL
*   [#8025](https://github.com/qdrant/qdrant/pull/8025) - Recover snapshot without creating intermediate files, greatly improves recovery time and disk usage
*   [#8059](https://github.com/qdrant/qdrant/pull/8059) - Recover snapshots directly into target file system to avoid expensive file movements
*   [#7883](https://github.com/qdrant/qdrant/pull/7883) - Flush after snapshot unpack with `syncfs` to persist a large number of files much more efficiently
*   [#8072](https://github.com/qdrant/qdrant/pull/8072) - Don't lock shard holder structure during creation of a snapshot, previously blocking shard level operations
*   [#8166](https://github.com/qdrant/qdrant/pull/8166) - Add timeout to snapshot downloads, abort if connection gets stuck for more than a minute
*   [#8007](https://github.com/qdrant/qdrant/pull/8007), [#8056](https://github.com/qdrant/qdrant/pull/8056) - Improve segments locking approach to minimize lock contention
*   [#8105](https://github.com/qdrant/qdrant/pull/8105) - Limit number of parallel updates on a shard to 64 to prevent order tracking overhead
*   [#8169](https://github.com/qdrant/qdrant/pull/8169) - Reduce locking in Gridstore to lower search tail latencies
*   [#8164](https://github.com/qdrant/qdrant/pull/8164) - Actively free cache memory for closed WAL segments to reduce memory pressure
*   [#7952](https://github.com/qdrant/qdrant/pull/7952) - Disable in-place payload updates on unindexed fields, improve immutability guarantees of indexed segments improving partial snapshots
*   [#7887](https://github.com/qdrant/qdrant/pull/7887) - Add ability to disable extra HNSW links construction for specific payload indices ([docs](https://qdrant.tech/documentation/concepts/indexing/#disable-the-creation-of-extra-edges-for-payload-fields))
*   [#7971](https://github.com/qdrant/qdrant/pull/7971) - Enable missing option for vector storage to populate single-file mmap
*   [#7928](https://github.com/qdrant/qdrant/pull/7928) - Enable `io_uring` when reading batch of vectors
*   [#7919](https://github.com/qdrant/qdrant/pull/7919) - Improve error message for datetime parse failures
*   [#8053](https://github.com/qdrant/qdrant/pull/8053) - Allow to configure load concurrency for collections, shards and segments
*   [#7809](https://github.com/qdrant/qdrant/pull/7809) - Add more convenient way to provide API-keys for external inference providers ([docs](https://qdrant.tech/documentation/concepts/inference/#external-embedding-model-providers))
*   [#8093](https://github.com/qdrant/qdrant/pull/8093) - Don't lock WAL during serialization of new updates, which was costly for large operations
*   [#7834](https://github.com/qdrant/qdrant/pull/7834) - Extend WAL retention when replicas are dead, prevent full shard transfers in case of peer failures
*   [#7565](https://github.com/qdrant/qdrant/pull/7565) - Disable old shard key format deprecated in 1.15.0
*   [#8125](https://github.com/qdrant/qdrant/pull/8125) - Skip building extra HNSW links for deleted vectors
*   [#8163](https://github.com/qdrant/qdrant/pull/8163) - Improve search result processing to use less CPU with a high search limit
*   [#8175](https://github.com/qdrant/qdrant/pull/8175) - Use less allocations for HNSW plain filtered search

Bug Fixes 🤹
------------

*   [#7850](https://github.com/qdrant/qdrant/pull/7850) - Fix flush ordering to follow segment dependencies, prevents dataloss by CoW on flush interruption
*   [#8103](https://github.com/qdrant/qdrant/pull/8103) - Fix data race in stream records transfer potentially missing ongoing updates
*   [#7983](https://github.com/qdrant/qdrant/pull/7983) - Fix interlocking problem on creation of payload index
*   [#7999](https://github.com/qdrant/qdrant/pull/7999) - Fix interlocking problem on collection-level update operations
*   [#8131](https://github.com/qdrant/qdrant/pull/8131) - Fix deadlock during snapshot with concurrent updates
*   [#8128](https://github.com/qdrant/qdrant/pull/8128) - Fix gRPC/HTTP2 `too_many_internal_resets` error due to how we internally cancel ongoing requests
*   [#8019](https://github.com/qdrant/qdrant/pull/8019) - Improve handling of HTTP2 channels closing in connection pool
*   [#8104](https://github.com/qdrant/qdrant/pull/8104) - Fix data race in WAL and shard clocks snapshot, ensure they remain consistent
*   [#7961](https://github.com/qdrant/qdrant/pull/7961) - Fix using incorrect versions in partial snapshot manifest construction
*   [#8095](https://github.com/qdrant/qdrant/pull/8095) - Fix incorrect internal protocol usage for shard snapshot transfers
*   [#7950](https://github.com/qdrant/qdrant/pull/7950) - Fix integer overflow in query batch when using high limits
*   [#7972](https://github.com/qdrant/qdrant/pull/7972) - Fix search aggregator panic with limit 0
*   [#8100](https://github.com/qdrant/qdrant/pull/8100) - Fix round floats not used in integer index, JSON doesn't distinguish between integers and floats
*   [#8097](https://github.com/qdrant/qdrant/pull/8097) - Fix `score_threshold` not being used in score boosting queries
*   [#7877](https://github.com/qdrant/qdrant/pull/7877) - Fix `Corrupted ID tracker mapping storage` bug when disk is full
*   [#7944](https://github.com/qdrant/qdrant/pull/7944) - Fix gRPC API response status counting in telemetry and metrics
*   [#7857](https://github.com/qdrant/qdrant/pull/7857) - Fix total count in progress tracker for replicate points with filter
*   [#7856](https://github.com/qdrant/qdrant/pull/7856) - Fix creation of payload index in empty collection using user-defined sharding
*   [#8099](https://github.com/qdrant/qdrant/pull/8099) - Fix ignoring CA certs for internal requests if configured
*   [#8176](https://github.com/qdrant/qdrant/pull/8176) - Add missing timeout parameter to some endpoints

Web UI 🍱
---------

*   [qdrant/qdrant-web-ui#345](https://github.com/qdrant/qdrant-web-ui/pull/345) - Detailed visualization of optimization progress
*   [qdrant/qdrant-web-ui#334](https://github.com/qdrant/qdrant-web-ui/pull/334) - Create collection dialog now previews the exact command
*   [qdrant/qdrant-web-ui#341](https://github.com/qdrant/qdrant-web-ui/pull/341) - Buttons for resharding control
*   [qdrant/qdrant-web-ui#344](https://github.com/qdrant/qdrant-web-ui/pull/344) - Points filter and search bar restored and improved

Qdrant Edge 🔪
--------------

Qdrant Edge is an in-process version of Qdrant, which shares the same internals, storage format, and points API as the server version, but designed to work locally. Qdrant Edge is compatible with server version and it can read shard snapshots created by server version of Qdrant. More documentation available [here](https://qdrant.tech/documentation/edge/).

Deprecations ⚠️
---------------

*   Starting from v1.17.0 Qdrant changes response format for vector fields in gRPC interface. All official Qdrant clients should be already adopted to this change, so please make sure you upgrade your client libraries and check that you are not using deprecated fields. More info: [#7183](https://github.com/qdrant/qdrant/pull/7183)
    
*   Upcoming deprecations:
    
    *   In Qdrant v1.18.x all deprecated search methods will be completely removed and won't be available even from old client libraries.
    *   In Qdrant v1.17.x we will completely remove RocksDB support in favor of [gridstore](https://qdrant.tech/articles/gridstore-key-value-storage/), that means that direct upgrade from v1.15.x into v1.17.x won't be possible. Please follow [upgrade instructions](https://qdrant.tech/documentation/faq/qdrant-fundamentals/#how-do-i-avoid-issues-when-updating-to-the-latest-version) and upgrade one minor version at a time to avoid unsupported storage errors. Note that Qdrant Cloud infrastructure automatically generates a proper upgrade steps, so you don't have to worry about that.

v1.16.3
-------

Change log
----------

Improvements
------------

*   [#7755](https://github.com/qdrant/qdrant/pull/7755), [#7588](https://github.com/qdrant/qdrant/pull/7588) - Respect search and point retrieve timeout when trying to access segments
*   [#7685](https://github.com/qdrant/qdrant/pull/7685) - Respect telemetry timeout when fetching shard statistics
*   [#7715](https://github.com/qdrant/qdrant/pull/7715) - Log snapshot download duration and speed

Bug fixes
---------

*   [#7787](https://github.com/qdrant/qdrant/pull/7787), [#7791](https://github.com/qdrant/qdrant/pull/7791) - Fix WAL delta transfer corrupting replica after a previous full transfer was aborted
*   [#7801](https://github.com/qdrant/qdrant/pull/7801), [#7805](https://github.com/qdrant/qdrant/pull/7805) - Fix flush losing changes on transient disk IO errors, potentially corrupting data
*   [#7792](https://github.com/qdrant/qdrant/pull/7792) - Fix incorrectly aborting shard transfers when dropping unrelated shard
*   [#7741](https://github.com/qdrant/qdrant/pull/7741) - Fix flush error in Gridstore, potentially corrupting data when quickly alternating inserts/deletes
*   [#7702](https://github.com/qdrant/qdrant/pull/7702) - Fix flush data race in Gridstore, potentially corrupting data when storage is cleared in parallel
*   [#7759](https://github.com/qdrant/qdrant/pull/7759), [#7782](https://github.com/qdrant/qdrant/pull/7782) - Fix handling of collection names with weird characters, breaking snapshot transfers for example
*   [#7788](https://github.com/qdrant/qdrant/pull/7788) - Fix snapshot metrics not always reporting when zero (`snapshot_{creation,recovery}_running`, `snapshot_created_total`)
*   [#7783](https://github.com/qdrant/qdrant/pull/7783) - Fix incorrectly reporting optimization errors in telemetry on panic
*   [#7765](https://github.com/qdrant/qdrant/pull/7765) - Fix slow shutdown on SIGINT when optimizations are running
*   [#7690](https://github.com/qdrant/qdrant/pull/7690) - Fix Qdrant not building on Windows ARM64
*   [#7683](https://github.com/qdrant/qdrant/pull/7683) - Keep RocksDB support until 1.18.0 in development builds

v1.16.2
-------

Change log
----------

Improvements
------------

*   [#7607](https://github.com/qdrant/qdrant/pull/7607) - Improve request timeout handling for telemetry and metrics
*   [#7623](https://github.com/qdrant/qdrant/pull/7623) - Add user agent to HTTP requests sent by Qdrant server

Bug fixes
---------

*   [#7674](https://github.com/qdrant/qdrant/pull/7674) - Fix critical WAL bug that could break consensus or cause data corruption on restart
*   [#7684](https://github.com/qdrant/qdrant/pull/7684) - Fix consensus crash when applying consensus snapshot with non-replicated collection
*   [#7620](https://github.com/qdrant/qdrant/pull/7620) - Fix panic during search on segments with empty HNSW graph
*   [#7629](https://github.com/qdrant/qdrant/pull/7629), [#7640](https://github.com/qdrant/qdrant/pull/7640), [#7673](https://github.com/qdrant/qdrant/pull/7673) - Fix shard resource cleanup when shard is replaced, prevent deadlock on small CPUs
*   [#7621](https://github.com/qdrant/qdrant/pull/7621), [#7626](https://github.com/qdrant/qdrant/pull/7626) - Fix payload index storage still flushing after removal, fixing data corruption and IO errors on Windows
*   [#7624](https://github.com/qdrant/qdrant/pull/7624), [#7627](https://github.com/qdrant/qdrant/pull/7627) - Fix Gridstore storage still flushing after wipe, fixing data corruption and IO errors
*   [#7614](https://github.com/qdrant/qdrant/pull/7614), [#7618](https://github.com/qdrant/qdrant/pull/7618) - Fix Docker/WSL on Windows with bind mount corrupting storage
*   [#7678](https://github.com/qdrant/qdrant/pull/7678) - Fix `collections_vector_total` metric reporting -0.0 if there are no vectors
*   [#7649](https://github.com/qdrant/qdrant/pull/7649) - Also report `collection_indexed_only_excluded_points` metric if zero

v1.16.1
-------

Change log
----------

Improvements
------------

*   [#7514](https://github.com/qdrant/qdrant/pull/7514), [#7572](https://github.com/qdrant/qdrant/pull/7572) - Make batch queries up to 3 times faster on full scans by reading each point only once
*   [#7551](https://github.com/qdrant/qdrant/pull/7551) - Actively migrate vector, payload and payload index storage from RocksDB into Gridstore on startup for better and more predictable performance
*   [#7579](https://github.com/qdrant/qdrant/pull/7579) - Add 60s internal timeout for telemetry/metrics endpoints to prevent long hanging tasks
*   [#7557](https://github.com/qdrant/qdrant/pull/7557) - Add validation to restart shard transfer operation
*   [#7446](https://github.com/qdrant/qdrant/pull/7446) - Defer Gridstore flushing to make flushing behavior consistent with all other storage components
*   [#7580](https://github.com/qdrant/qdrant/pull/7580) - Improve consensus WAL compaction logging to aid debugging
*   [#7598](https://github.com/qdrant/qdrant/pull/7598) - Make timeout for inference requests user configurable

Bug fixes
---------

*   [#7564](https://github.com/qdrant/qdrant/pull/7564) - Fix panic at startup on old clusters with user defined sharding, if not updated to Qdrant 1.15.5 first
*   [#7577](https://github.com/qdrant/qdrant/pull/7577) - Fix breaking Raft by killing node at specific time during consensus snapshot, preventing potential crash loop
*   [#7587](https://github.com/qdrant/qdrant/pull/7587) - Fix corrupting WAL with broken flush edge case after WAL is cleared or truncated
*   [#7570](https://github.com/qdrant/qdrant/pull/7570) - Fix incorrect rescoring default on mutable segments when using binary quantization
*   [#7569](https://github.com/qdrant/qdrant/pull/7569), [#7575](https://github.com/qdrant/qdrant/pull/7575) - Spawn search/update tasks on the correct runtime, significantly reduce number of general/actix threads
*   [#7558](https://github.com/qdrant/qdrant/pull/7558) - Fix data race in shard transfers, wait on transfer to start before initializing shards
*   [#7556](https://github.com/qdrant/qdrant/pull/7556) - Fix incorrect log message when failing to read lock segment for some time

v1.16.0
-------

Change log
----------

Features 🌰
-----------

*   [https://github.com/qdrant/qdrant/milestone/33?closed=1](https://github.com/qdrant/qdrant/milestone/33?closed=1) - Inline Storage: Add option to inline vectors in HNSW graph for efficient IO usage ([docs](https://qdrant.tech/documentation/guides/optimize/#inline-storage-in-hnsw-index))
*   [https://github.com/qdrant/qdrant/milestone/37?closed=1](https://github.com/qdrant/qdrant/milestone/37?closed=1) - Tenant promotion mechanism for tiered multitenancy: ([docs](https://qdrant.tech/documentation/guides/multitenancy/#tiered-multitenancy))
    *   Add `ReplicatePoints` action to promote payload based tenant into dedicated shard key ([docs](https://qdrant.tech/documentation/guides/multitenancy/#promote-tenant-to-dedicated-shard))
    *   Add fallback shard key for intelligent routing to tenants that are or are not promoted to a dedicated shard ([docs](https://qdrant.tech/documentation/guides/multitenancy/#query-tiered-multitenant-collection))
    *   On shard key creation, allow to specify initial state of new replicas
*   [#7414](https://github.com/qdrant/qdrant/pull/7414) - Add ACORN-1 search method, accurate search over many filtered points at the cost of performance ([docs](https://qdrant.tech/documentation/concepts/search/#acorn-search-algorithm))
*   [#7408](https://github.com/qdrant/qdrant/pull/7408) - Add ASCII folding (normalization) to full text indices, fold diacritics into ASCII characters ([docs](https://qdrant.tech/documentation/concepts/indexing/#ascii-folding))
*   [#7006](https://github.com/qdrant/qdrant/pull/7006) - Add conditional update functionality, only apply update on points matching filter ([docs](https://qdrant.tech/documentation/concepts/points/#conditional-updates))
*   [#7100](https://github.com/qdrant/qdrant/pull/7100) - Add `text_any` full text filter to match any query term ([docs](https://qdrant.tech/documentation/guides/optimize/#inline-storage-in-hnsw-index))
*   [#7065](https://github.com/qdrant/qdrant/pull/7065) - Add option to customize RRF `k` parameter ([docs](https://qdrant.tech/documentation/concepts/hybrid-queries/#parametrized-rrf))
*   [#7222](https://github.com/qdrant/qdrant/pull/7222) - In strict mode, specify maximum number of payload indices per collection
*   [#7123](https://github.com/qdrant/qdrant/pull/7123) - Add custom key-value metadata to collections ([docs](https://qdrant.tech/documentation/concepts/collections/#collection-metadata))
*   [#7291](https://github.com/qdrant/qdrant/pull/7291) - Add profiler to log slow point update and read requests

Improvements 🏎️
----------------

*   [#7385](https://github.com/qdrant/qdrant/pull/7385) - When loading Gridstore, populate tracker data into memory for faster first access
*   [#7407](https://github.com/qdrant/qdrant/pull/7407), [#7405](https://github.com/qdrant/qdrant/pull/7405) - Spawn updates and flush workers task on updates runtime, use two system threads less for each local shard
*   [#7413](https://github.com/qdrant/qdrant/pull/7413) - Use system thread on demand in WAL, use one less system thread per local shard by default
*   [#7468](https://github.com/qdrant/qdrant/pull/7468) - Use atomic bit flags on HNSW construction to significantly increase indexing performance
*   [#7052](https://github.com/qdrant/qdrant/pull/7052), [#7471](https://github.com/qdrant/qdrant/pull/7471) - Implement AVX512 SIMD optimizations for binary quantization on modern x86\_64 CPUs
*   [#7433](https://github.com/qdrant/qdrant/pull/7433) - Switch new mutable payload indices and storage from RocksDB to Gridstore for better performance
*   [#7508](https://github.com/qdrant/qdrant/pull/7508) - Enable quantization in appendable segments by default, improving search performance
*   [#7347](https://github.com/qdrant/qdrant/pull/7347) - Change default score of query-less prefetch to 1.0 to ease score boosting
*   [#7369](https://github.com/qdrant/qdrant/pull/7369) - Don't explicitly disable strict mode by default
*   [#7345](https://github.com/qdrant/qdrant/pull/7345) - Simplify internal handling of copy-on-write segments, now write incoming updates to dedicated segments directly
*   [#7293](https://github.com/qdrant/qdrant/pull/7293), [#7523](https://github.com/qdrant/qdrant/pull/7523) - Add warnings field to collection info, report misconfiguration
*   [#7319](https://github.com/qdrant/qdrant/pull/7319), [#7401](https://github.com/qdrant/qdrant/pull/7401) - Report more helpful error messages on file IO errors
*   [#7377](https://github.com/qdrant/qdrant/pull/7377) - When using inference, propagate rate limit responses
*   [#7434](https://github.com/qdrant/qdrant/pull/7434) - Rate limit slow request warning to prevent spamming logs
*   [#7373](https://github.com/qdrant/qdrant/pull/7373) - Log shard transfers as a result of the consensus recovery procedure
*   [#7337](https://github.com/qdrant/qdrant/pull/7337) - Tone down optimizer logging to make it less verbose
*   [#7370](https://github.com/qdrant/qdrant/pull/7370) - Add `TARGET_CPU` and `JEMALLOC_SYS_WITH_LG_PAGE` build parameters to Docker image

Metrics 📈
----------

*   [#7302](https://github.com/qdrant/qdrant/pull/7302), [#7441](https://github.com/qdrant/qdrant/pull/7441) - In metrics, report point and vector counts per collection and vector name (`collection_{points,vectors}`)
*   [#7307](https://github.com/qdrant/qdrant/pull/7307) - In metrics, report number of points skipped in `indexed_only` search (`collection_indexed_only_excluded_points`)
*   [#7301](https://github.com/qdrant/qdrant/pull/7301) - In metrics, report global effective minimum and maximum shard replication count (`collection_active_replicas_{min,max}`)
*   [#7310](https://github.com/qdrant/qdrant/pull/7310), [#7516](https://github.com/qdrant/qdrant/pull/7516) - In metrics, report total number of non-active replicas (`collection_dead_replicas`)
*   [#7316](https://github.com/qdrant/qdrant/pull/7316), [#7480](https://github.com/qdrant/qdrant/pull/7480) - In metrics, expose `collection_running_optimizations` with number of optimizers running per collection
*   [#7497](https://github.com/qdrant/qdrant/pull/7497) - In metrics, report running, created and recovered number of snapshots (`snapshot_{creation,recovery}_running`, `snapshot_created_total`)
*   [#7484](https://github.com/qdrant/qdrant/pull/7484) - In metrics, report active thread count (`process_threads`)
*   [#7451](https://github.com/qdrant/qdrant/pull/7451) - In metrics, report number of open file descriptors and the limit (`process_{open,max}_fds`)
*   [#7487](https://github.com/qdrant/qdrant/pull/7487) - In metrics, report open mmaps and system limit (`process_open_mmaps`, `system_max_mmaps`)
*   [#7482](https://github.com/qdrant/qdrant/pull/7482) - In metrics, report total number of major and minor page faults (`process_{minor,major}_page_faults_total`)
*   [#7438](https://github.com/qdrant/qdrant/pull/7438) - In metrics, add configuration option to prefix all metrics with `qdrant_` or something else

Bug fixes 🕵️
-------------

*   [#7527](https://github.com/qdrant/qdrant/pull/7527) - Fix logger API allowing arbitrary file writes, now this can only be configured through configuration
*   [#7530](https://github.com/qdrant/qdrant/pull/7530) - Abort pending search tasks when search is cancelled, fixing optimizer instability under huge load
*   [#7533](https://github.com/qdrant/qdrant/pull/7533) - Abort other blocking tasks such as retrieve and snapshot prematurely if the caller gets cancelled
*   [#7531](https://github.com/qdrant/qdrant/pull/7531) - Cancel ongoing searches more aggressively if the search is cancelled
*   [#7517](https://github.com/qdrant/qdrant/pull/7517) - Fix resharding down panic if no shard key is provided on collection with custom sharding
*   [#7469](https://github.com/qdrant/qdrant/pull/7469) - Fix panic on certain queries with unknown vector name
*   [#7375](https://github.com/qdrant/qdrant/pull/7375) - Forbid peer to join cluster with URI that is already used, which could break a cluster
*   [#7400](https://github.com/qdrant/qdrant/pull/7400) - Fix corrupt segments on load if segment was partially flushed, prevent payload index corruption
*   [#7342](https://github.com/qdrant/qdrant/pull/7342), [#7404](https://github.com/qdrant/qdrant/pull/7404), [#7427](https://github.com/qdrant/qdrant/pull/7427) - Force flush all segments when taking snapshot to prevent data corruption
*   [#7381](https://github.com/qdrant/qdrant/pull/7381) - Fix flush ordering on segments currently being snapshotted, fixing data consistency on crash
*   [#7388](https://github.com/qdrant/qdrant/pull/7388), [#7416](https://github.com/qdrant/qdrant/pull/7416) - Fix flush ordering with concurrent flushes to ensure data consistency
*   [#7512](https://github.com/qdrant/qdrant/pull/7512), [#7521](https://github.com/qdrant/qdrant/pull/7521) - Fix dummy shards not allowing snapshot recovery

Web UI 🫂
---------

*   [https://github.com/qdrant/qdrant-web-ui/releases/tag/v0.2.0](https://github.com/qdrant/qdrant-web-ui/releases/tag/v0.2.0) - New web UI design to match Qdrant Cloud

Deprecations 🚧
---------------

*   [#7454](https://github.com/qdrant/qdrant/pull/7454) - Remove `init_from` collection API, deprecated since Qdrant 1.15
*   [#7449](https://github.com/qdrant/qdrant/pull/7449) - Remove lock API, deprecated since Qdrant 1.15
*   [#7047](https://github.com/qdrant/qdrant/pull/7047) - Remove old internal shard key format, deprecated and migrated away from in Qdrant 1.15
*   [#7450](https://github.com/qdrant/qdrant/pull/7450) - Remove payload filter from RBAC/JWT, deprecated since Qdrant 1.15, API keys using it are rejected
*   [#7183](https://github.com/qdrant/qdrant/pull/7183) - Deprecate old variant of vector output

v1.15.5
-------

Change log
----------

Improvements
------------

*   [#7157](https://github.com/qdrant/qdrant/pull/7157) - Acknowledge update/delete by filter operations on flush, preventing very slow restart
*   [#7217](https://github.com/qdrant/qdrant/pull/7217), [#7218](https://github.com/qdrant/qdrant/pull/7218), [#7219](https://github.com/qdrant/qdrant/pull/7219), [#7220](https://github.com/qdrant/qdrant/pull/7220), [#7221](https://github.com/qdrant/qdrant/pull/7221) - Add API validation to min\_should, filters, point update batch and others
*   [#7235](https://github.com/qdrant/qdrant/pull/7235) - Add timeout parameter to remove peer operation
*   [#7320](https://github.com/qdrant/qdrant/pull/7320) - Decrease internal update batch sizes to minimize search latency spikes on large user batches
*   [#7233](https://github.com/qdrant/qdrant/pull/7233) - Limit number of segments loaded in parallel, preventing potential OOM on large clusters
*   [#7222](https://github.com/qdrant/qdrant/pull/7222) - Add strict mode configuration to specify max number of payload indices
*   [#7240](https://github.com/qdrant/qdrant/pull/7240) - Improve error reporting on mutable ID tracker load errors
*   [#7151](https://github.com/qdrant/qdrant/pull/7151) - Improve error reporting on flush problems
*   [#7244](https://github.com/qdrant/qdrant/pull/7244) - Remove vector count field from collection info
*   [#7177](https://github.com/qdrant/qdrant/pull/7177) - Do not anonymize peer ID in telemetry data

Bug fixes
---------

*   [#7263](https://github.com/qdrant/qdrant/pull/7263) - Fix not flushing mutable ID tracker files after creation, potentially causing segment corruption
*   [#7248](https://github.com/qdrant/qdrant/pull/7248) - Fix data race at the end of snapshot creation causing missing points
*   [#7298](https://github.com/qdrant/qdrant/pull/7298), [#7306](https://github.com/qdrant/qdrant/pull/7306) - Fix data race during snapshots corrupting point data if a point is moved
*   [#7241](https://github.com/qdrant/qdrant/pull/7241), [#7265](https://github.com/qdrant/qdrant/pull/7265), [#7267](https://github.com/qdrant/qdrant/pull/7267), [#7269](https://github.com/qdrant/qdrant/pull/7269), [#7277](https://github.com/qdrant/qdrant/pull/7277) - Fix potential deadlock in REST runtime while streaming shard snapshot
*   [#7015](https://github.com/qdrant/qdrant/pull/7015) - Fix potential deadlock on REST server runtime
*   [#7172](https://github.com/qdrant/qdrant/pull/7172) - Fix potential recursive deadlock when fetching all vectors
*   [#7203](https://github.com/qdrant/qdrant/pull/7203) - Fix potential deadlock in scroll API
*   [#7303](https://github.com/qdrant/qdrant/pull/7303) - Fix incorrectly deleting old point versions from segments
*   [#7194](https://github.com/qdrant/qdrant/pull/7194) - Fix upsert operations with duplicate point IDs not being applied properly
*   [#7252](https://github.com/qdrant/qdrant/pull/7252) - Fix phrase matching ignoring unknown tokens
*   [#7264](https://github.com/qdrant/qdrant/pull/7264) - Fix strict mode validation on nested filters

v1.15.4
-------

Change log
----------

Improvements
------------

*   [#7005](https://github.com/qdrant/qdrant/pull/7005) - Reduce Docker image size by 10-40%
*   [#7073](https://github.com/qdrant/qdrant/pull/7073) - Adjust metrics histogram buckets, show empty buckets and remove small ones
*   [#7111](https://github.com/qdrant/qdrant/pull/7111) - Include SBOM in Docker image
*   [#7119](https://github.com/qdrant/qdrant/pull/7119) - Sign Docker images with cosign
*   [#7110](https://github.com/qdrant/qdrant/pull/7110) - Actively migrate away from old shard key format on disk to a more robust format
*   [#7120](https://github.com/qdrant/qdrant/pull/7120) - Measure segment size on disk more reliably for improved available disk space checks

Bug fixes
---------

*   [#7133](https://github.com/qdrant/qdrant/pull/7133) - Fix not loading some full text index types correctly, temporarily resulting in an empty index
*   [#7109](https://github.com/qdrant/qdrant/pull/7109) - Fix incorrectly reusing old deleted points in proxy segments
*   [#7106](https://github.com/qdrant/qdrant/pull/7106) - Preserve segment ID mapping when proxying all segments for a snapshot, potentially mixing up segments

v1.15.3
-------

Change log
----------

Improvements
------------

*   [#7002](https://github.com/qdrant/qdrant/pull/7002) - Optimize dot product calculation on AVX systems
*   [#7049](https://github.com/qdrant/qdrant/pull/7049) - In Nix package, use rustup for Rust version management

Bug fixes
---------

*   [#7056](https://github.com/qdrant/qdrant/pull/7056) - Fix local BM25 not working as expected due to default parameter differences

v1.15.2
-------

Change log
----------

Improvements
------------

*   [#6891](https://github.com/qdrant/qdrant/pull/6891) - Implement BM25 inference in Qdrant locally
*   [#6926](https://github.com/qdrant/qdrant/pull/6926) - Improve performance of mutable map index, used for full text, integers and more
*   [#6993](https://github.com/qdrant/qdrant/pull/6993) - Make log buffer size adjustable when logging to a file

Bug fixes
---------

*   [#6954](https://github.com/qdrant/qdrant/pull/6954) - Fix consistency problem in null index storage by deferring writes until flush
*   [#6977](https://github.com/qdrant/qdrant/pull/6977) - Fix consistency problem in boolean index storage by deferring writes until flush
*   [#6994](https://github.com/qdrant/qdrant/pull/6994) - Fix consistency problem for deleted vectors by deferring writes until flush
*   [#6966](https://github.com/qdrant/qdrant/pull/6966) - Fix flush logic in memory mapped bit flags structure, improving data consistency
*   [#6975](https://github.com/qdrant/qdrant/pull/6975) - Delete versionless points before WAL replay, fix incorrect use of corrupt points
*   [#6952](https://github.com/qdrant/qdrant/pull/6952) - Fix date time error in custom score boosting formula when having multiple nodes
*   [#6998](https://github.com/qdrant/qdrant/pull/6998) - In score boosting formula validation error, show each index type only once
*   [#6959](https://github.com/qdrant/qdrant/pull/6959) - Fix range bounds not being inclusive for linear decay function
*   [#6958](https://github.com/qdrant/qdrant/pull/6958) - Fix default storage path and missing web UI assets in Debian package

Web UI
------

*   [qdrant/qdrant-web-ui#299](https://github.com/qdrant/qdrant-web-ui/pull/299) - Show shard distribution of collection in cluster as replica/node matrix