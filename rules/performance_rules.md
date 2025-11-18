# Performance Inspection Rules

## Overview
These rules focus on identifying performance bottlenecks and ensuring optimal code execution.

## Algorithmic Efficiency

### 1. Time Complexity
- Avoid O(n²) or higher complexity where O(n log n) is possible
- Use appropriate data structures for the use case
- Optimize hot paths and frequently called functions
- Consider caching for expensive computations

### 2. Space Complexity
- Avoid unnecessary data copies
- Use generators/iterators for large datasets
- Implement pagination for large result sets
- Clean up temporary objects promptly

### 3. Algorithm Selection
- Use built-in sorting algorithms
- Choose appropriate search algorithms
- Use hash tables for O(1) lookups
- Consider trade-offs between time and space

## Database Performance

### 1. Query Optimization
- Avoid N+1 query problems
- Use proper indexing
- Limit result sets with pagination
- Avoid SELECT * queries
- Use query explain plans to optimize

### 2. Connection Management
- Use connection pooling
- Close connections promptly
- Reuse connections when possible
- Set appropriate timeout values

### 3. Caching Strategies
- Implement query result caching
- Use Redis/Memcached for distributed caching
- Cache database metadata
- Implement cache invalidation strategies

## Network Performance

### 1. API Design
- Implement pagination for list endpoints
- Use compression (gzip, brotli)
- Minimize payload sizes
- Use HTTP/2 or HTTP/3 where possible

### 2. Request Optimization
- Batch API requests
- Implement request debouncing
- Use connection keep-alive
- Minimize round trips

### 3. Data Transfer
- Compress responses
- Use CDN for static assets
- Implement lazy loading
- Optimize image sizes

## Memory Management

### 1. Memory Usage
- Avoid memory leaks
- Release resources promptly
- Use weak references where appropriate
- Monitor memory consumption

### 2. Object Lifecycle
- Implement proper cleanup in destructors
- Use context managers (with statements)
- Avoid circular references
- Pool frequently allocated objects

### 3. Data Structures
- Choose appropriate data structures
- Use arrays instead of lists for fixed-size collections
- Consider memory overhead of data structures
- Use primitive types when possible

## I/O Operations

### 1. File Operations
- Use buffered I/O
- Batch file operations
- Avoid synchronous I/O in event loops
- Use memory-mapped files for large files

### 2. Asynchronous Operations
- Use async/await for I/O-bound operations
- Implement non-blocking I/O
- Use event-driven architecture
- Avoid blocking the main thread

### 3. Disk Usage
- Implement log rotation
- Clean up temporary files
- Use streaming for large files
- Monitor disk space

## Concurrency & Parallelism

### 1. Threading
- Use thread pools
- Avoid race conditions
- Implement proper locking mechanisms
- Minimize lock contention

### 2. Asynchronous Processing
- Use message queues for background tasks
- Implement worker pools
- Use async frameworks appropriately
- Handle backpressure

### 3. Parallel Processing
- Utilize multi-core processors
- Use process pools for CPU-bound tasks
- Avoid unnecessary serialization
- Balance workload distribution

## Caching

### 1. Application-Level Caching
- Cache expensive computations
- Implement LRU/LFU cache strategies
- Set appropriate TTL values
- Monitor cache hit rates

### 2. HTTP Caching
- Set proper Cache-Control headers
- Use ETags for validation
- Implement conditional requests
- Cache static resources

### 3. Distributed Caching
- Use Redis/Memcached effectively
- Implement cache warming strategies
- Handle cache failures gracefully
- Monitor cache performance

## Frontend Performance

### 1. Asset Optimization
- Minify JavaScript and CSS
- Optimize images (WebP, AVIF)
- Use lazy loading for images
- Implement code splitting

### 2. Rendering Performance
- Avoid layout thrashing
- Minimize DOM manipulations
- Use virtual scrolling for long lists
- Optimize animation performance

### 3. Bundle Size
- Tree shake unused code
- Split code by routes
- Use dynamic imports
- Monitor bundle sizes

## Server-Side Performance

### 1. Request Processing
- Minimize middleware overhead
- Use streaming responses
- Implement request timeouts
- Optimize serialization/deserialization

### 2. Resource Management
- Limit concurrent requests
- Implement rate limiting
- Use circuit breakers
- Monitor resource usage

### 3. Scaling
- Design for horizontal scaling
- Use load balancing
- Implement auto-scaling
- Monitor performance metrics

## Language-Specific Optimizations

### Python
- Use list comprehensions over loops
- Avoid global lookups in loops
- Use `__slots__` for classes with many instances
- Prefer built-in functions over custom implementations

### JavaScript/TypeScript
- Use const/let instead of var
- Avoid prototype pollution
- Use WeakMap/WeakSet for caching
- Minimize closures in loops

### Go
- Use goroutines efficiently
- Avoid goroutine leaks
- Use sync.Pool for temporary objects
- Optimize memory allocations

## Monitoring & Profiling

### 1. Performance Metrics
- Track response times
- Monitor throughput
- Measure resource utilization
- Set up alerts for degradation

### 2. Profiling
- Profile CPU usage
- Profile memory allocation
- Identify bottlenecks
- Use APM tools

### 3. Benchmarking
- Establish performance baselines
- Run load tests
- Test under various scenarios
- Monitor trends over time

## Common Anti-Patterns

### 1. Avoid
- Premature optimization
- String concatenation in loops
- Excessive logging in production
- Synchronous operations in async code
- Polling instead of event-driven design

### 2. Best Practices
- Measure before optimizing
- Optimize hot paths first
- Use appropriate data structures
- Implement caching strategically
- Design for scalability

## Performance Budgets

### 1. Response Times
- API endpoints: < 200ms (p95)
- Database queries: < 100ms (p95)
- Page load time: < 2s
- Time to interactive: < 3s

### 2. Resource Limits
- Memory usage: < 80% of available
- CPU usage: < 70% average
- Disk I/O: Monitor and optimize
- Network bandwidth: Optimize transfers

## Severity Classification

- **Critical**: Response time > 5s, memory leaks, deadlocks
- **High**: N+1 queries, inefficient algorithms, no caching
- **Medium**: Suboptimal data structures, missing indexes
- **Low**: Minor optimizations, code style for performance

## Scoring Impact

Performance issues impact based on severity:
- Critical: -15 points
- High: -8 points
- Medium: -4 points
- Low: -1 point

## Recommendations Format

When identifying performance issues, provide:
1. Current implementation and its complexity
2. Performance impact assessment
3. Recommended optimization
4. Expected improvement
