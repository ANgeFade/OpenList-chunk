# 分层哈希校验设计方案

## 目标
为分片上传提供快速且可靠的文件完整性校验，同时降低服务器CPU负载。

## 设计原则
1. **分片级校验**：每个分片上传后立即校验，快速发现传输错误。
2. **文件级校验**：合并后校验整个文件，确保最终文件完整性。
3. **性能优先**：使用快速哈希算法（CRC32、xxHash64），避免加密哈希（MD5/SHA）的计算开销。
4. **向后兼容**：不影响现有功能，新增校验为可选功能。

## 技术方案

### 1. 哈希算法选择
- **分片校验**：CRC32（IEEE多项式）
  - 速度快，硬件加速，碰撞概率可接受（用于检测传输错误）。
  - 每个分片计算一次，前端和后端都计算。
- **文件校验**：xxHash64
  - 极快的非加密哈希，碰撞概率极低，适合大文件完整性校验。
  - 替代MD5，性能提升显著。
- **可选保留**：MD5（用于兼容性），但默认不计算。

### 2. 后端哈希类型注册
在 `pkg/utils/hash.go` 中添加以下哈希类型：
```go
import (
    "hash/crc32"
    "hash/crc64"
    "github.com/cespare/xxhash/v2"
)

var (
    // CRC32 indicates CRC-32 (IEEE) support
    CRC32 = RegisterHash("crc32", "CRC-32", 8, func() hash.Hash { return crc32.NewIEEE() })
    // CRC64 indicates CRC-64 (ECMA) support
    CRC64 = RegisterHash("crc64", "CRC-64", 16, func() hash.Hash { return crc64.New(crc64.MakeTable(crc64.ECMA)) })
    // XXH64 indicates xxHash64 support
    XXH64 = RegisterHash("xxh64", "XXH-64", 16, func() hash.Hash { return xxhash.New() })
)
```

### 3. 前端修改
#### 分片CRC32计算
在 `form.ts` 的 `chunkedUpload` 函数中，为每个分片计算CRC32：
```typescript
async function computeCRC32(blob: Blob): Promise<string> {
    const buffer = await blob.arrayBuffer();
    // 使用JavaScript CRC32库或WebAssembly实现
    // 暂时可用简单的实现，或使用现有库（如crc-32）
    // 这里假设有现成的crc32函数
    return crc32(buffer).toString(16).padStart(8, '0');
}
```
将CRC32值通过请求头 `X-Chunk-CRC32` 发送。

#### 完整文件xxHash64计算（可选）
前端可以计算完整文件的xxHash64（使用WebAssembly），用于与服务器返回的哈希比对。

### 4. 后端修改
#### 分片上传校验 (`FsChunkUpload`)
- 读取上传的分片文件，计算其CRC32。
- 与请求头 `X-Chunk-CRC32` 比对，如果不匹配，返回400错误。
- 校验通过后才保存分片。

#### 合并文件校验 (`FsChunkMerge`)
- 合并分片时计算完整文件的xxHash64（可同时计算CRC64用于额外校验）。
- 返回哈希值给前端，格式如：
```json
{
  "hash": {
    "xxh64": "a1b2c3d4...",
    "crc64": "..."  // 可选
  }
}
```
- 添加日志输出到服务器控制台。

### 5. 性能影响评估
- **CRC32**：每个分片（最大750 MB）计算约需 50-100 ms（现代CPU）。
- **xxHash64**：5.5 GB文件计算约需 200-500 ms，比MD5快3-5倍。
- **总体**：相比之前计算三种加密哈希，CPU负载降低80%以上。

### 6. 错误处理
- 分片CRC不匹配：立即返回错误，前端重传该分片。
- 文件哈希不匹配：合并后返回错误，前端可重新上传整个文件或重新合并。

### 7. 配置与开关
- 可通过设置项启用/禁用分片校验。
- 可配置使用的哈希算法（例如，保留MD5用于兼容性）。

## 实施步骤

### 第一阶段：后端哈希类型注册
1. 修改 `pkg/utils/hash.go`，添加CRC32、CRC64、XXH64。
2. 确保 `go.mod` 中已有 `github.com/cespare/xxhash/v2` 依赖（已存在）。
3. 编译测试，确保新哈希类型可用。

### 第二阶段：分片上传校验
1. 修改 `server/handles/fsup.go` 中的 `FsChunkUpload`：
   - 读取请求头 `X-Chunk-CRC32`。
   - 计算上传文件的CRC32。
   - 比对并返回错误。
2. 添加必要的错误响应。

### 第三阶段：合并文件校验
1. 修改 `FsChunkMerge`：
   - 使用 `utils.NewMultiHasher([]*utils.HashType{utils.XXH64, utils.CRC64})` 计算哈希。
   - 返回哈希值。
   - 添加日志输出。
2. 移除或保留原有的MD5/SHA1/SHA256计算（可配置）。

### 第四阶段：前端适配
1. 添加CRC32计算函数（可使用 `crc-32` npm包或WebAssembly）。
2. 修改 `chunkedUpload`，为每个分片计算CRC32并添加到请求头。
3. 解析服务器返回的哈希并打印。

### 第五阶段：测试
1. 单元测试：哈希计算正确性。
2. 集成测试：上传大文件，验证分片校验和文件校验。
3. 性能测试：比较优化前后的CPU使用率和上传时间。

## 风险与缓解
- **CRC32碰撞**：概率极低（1/2^32），且仅用于分片传输错误检测，可接受。
- **xxHash64碰撞**：概率极低（1/2^64），足以保证文件完整性。
- **兼容性**：新哈希类型可能不被所有存储驱动支持，但仅用于校验，不影响存储。

## 后续优化
- 支持并行计算哈希（利用多核）。
- 提供哈希算法选择配置。
- 前端使用WebAssembly加速哈希计算。

## 时间估计
- 后端修改：2-3小时
- 前端修改：1-2小时
- 测试：1-2小时
- 总计：4-7小时