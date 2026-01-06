# 分层哈希校验实施计划

## 概述
本计划详细描述如何实现分片CRC校验和完整文件xxHash校验，包括后端和前端的具体修改步骤。

## 实施步骤

### 第一阶段：后端哈希类型注册
**目标**：在 `pkg/utils/hash.go` 中添加 CRC32、CRC64、XXH64 哈希类型。

**具体任务**：
1. 编辑 `pkg/utils/hash.go` 文件：
   - 导入 `hash/crc32`、`hash/crc64`、`github.com/cespare/xxhash/v2`。
   - 在 `var (` 块中注册新的哈希类型。
   - 确保 `RegisterHash` 函数正确使用。
2. 验证依赖：`go.mod` 中已存在 `github.com/cespare/xxhash/v2`，无需新增。
3. 编译测试：运行 `go build ./pkg/utils` 确保无错误。

**预期结果**：后端支持新的哈希类型，可通过 `utils.CRC32`、`utils.CRC64`、`utils.XXH64` 引用。

### 第二阶段：分片上传校验
**目标**：修改 `FsChunkUpload` 函数，验证每个分片的 CRC32。

**具体任务**：
1. 编辑 `server/handles/fsup.go` 中的 `FsChunkUpload` 函数：
   - 从请求头读取 `X-Chunk-CRC32`。
   - 在保存分片文件前，计算上传文件的 CRC32。
   - 比较计算值与请求头值，如果不匹配，返回 400 错误并包含详细消息。
   - 注意：计算 CRC32 需要读取整个分片数据，但 `c.SaveUploadedFile` 已经读取了数据，我们可以先保存到临时文件再计算，或者先计算再保存。为了性能，可以在保存前计算：使用 `file.Open()` 读取内容并计算哈希，然后保存。
2. 添加错误处理：如果 CRC 校验失败，删除已保存的分片文件（如果有）。
3. 添加日志记录校验结果。

**代码修改示例**：
```go
// 在 FsChunkUpload 中
crc32Header := c.GetHeader("X-Chunk-CRC32")
if crc32Header != "" {
    f, err := file.Open()
    if err != nil {
        common.ErrorResp(c, err, 500)
        return
    }
    defer f.Close()
    hasher := crc32.NewIEEE()
    if _, err := io.Copy(hasher, f); err != nil {
        common.ErrorResp(c, err, 500)
        return
    }
    computed := hex.EncodeToString(hasher.Sum(nil))
    if computed != crc32Header {
        common.ErrorStrResp(c, "chunk CRC32 mismatch", 400)
        return
    }
    // 重置文件指针到开头，以便后续保存
    if seeker, ok := f.(io.Seeker); ok {
        seeker.Seek(0, io.SeekStart)
    }
}
```

### 第三阶段：合并文件校验
**目标**：修改 `FsChunkMerge` 函数，计算完整文件的 xxHash64 和 CRC64，并返回哈希值。

**具体任务**：
1. 编辑 `server/handles/fsup.go` 中的 `FsChunkMerge` 函数：
   - 修改哈希计算部分，使用 `utils.NewMultiHasher([]*utils.HashType{utils.XXH64, utils.CRC64})`。
   - 保留原有的 MD5 计算（可选，可配置）。
   - 在合并循环中，将数据同时写入合并文件和哈希计算器。
   - 获取哈希结果并构建响应。
2. 添加日志输出：将计算出的哈希值打印到服务器控制台。
3. 修改响应结构：确保返回的哈希对象包含 `xxh64` 和 `crc64` 字段。

**代码修改示例**：
```go
// 替换原有的 hasher 初始化
hasher := utils.NewMultiHasher([]*utils.HashType{utils.XXH64, utils.CRC64})
multiWriter := io.MultiWriter(mergedFile, hasher)
// ... 合并循环
hashInfo := hasher.GetHashInfo()
hashMap := hashInfo.Export()
hashResponse := make(map[string]string)
for ht, hashValue := range hashMap {
    hashResponse[ht.Name] = hashValue
}
// 日志输出
log.Printf("[ChunkMerge] File %s xxh64: %s, crc64: %s", name, hashResponse["xxh64"], hashResponse["crc64"])
```

### 第四阶段：前端适配
**目标**：前端计算分片 CRC32 并发送，解析服务器返回的哈希值。

**具体任务**：
1. 添加 CRC32 计算函数：
   - 使用现有的 `crc-32` npm 包或 WebAssembly 实现。
   - 在 `form.ts` 中引入或实现 `computeCRC32(blob: Blob): Promise<string>`。
2. 修改 `chunkedUpload` 函数：
   - 为每个分片计算 CRC32，并添加到请求头 `X-Chunk-CRC32`。
   - 注意：计算 CRC32 可能需要异步，确保在上传前完成。
3. 修改合并响应处理：
   - 改进哈希显示，将对象转换为可读字符串。
   - 可选：比较本地计算的完整文件哈希（xxHash64）与服务器返回的哈希。
4. 更新 `calculateHash` 函数（可选）：添加 xxHash64 计算支持。

**代码修改示例**：
```typescript
// 假设有 crc32 库
import { crc32 } from 'crc-32';

async function computeCRC32(blob: Blob): Promise<string> {
    const buffer = await blob.arrayBuffer();
    const hash = crc32(new Uint8Array(buffer));
    // 转换为无符号32位十六进制
    return (hash >>> 0).toString(16).padStart(8, '0');
}

// 在 chunkedUpload 循环中
const chunkCRC = await computeCRC32(chunks[i]);
headers["X-Chunk-CRC32"] = chunkCRC;
```

### 第五阶段：测试与验证
**目标**：确保功能正确且性能提升。

**具体任务**：
1. 单元测试：
   - 测试新的哈希类型计算是否正确。
   - 测试分片 CRC 校验逻辑。
2. 集成测试：
   - 上传一个大文件（> 分片阈值），验证分片校验和文件校验。
   - 模拟 CRC 不匹配的情况，确保错误处理正确。
3. 性能测试：
   - 比较优化前后的 CPU 使用率和上传时间。
   - 监控服务器日志，确认哈希计算时间减少。
4. 回归测试：
   - 确保现有分片上传功能不受影响（当不提供 CRC 头时）。
   - 确保其他上传方式（直接上传、流式上传）正常工作。

## 文件清单
需要修改的文件：
1. `pkg/utils/hash.go` - 添加哈希类型
2. `server/handles/fsup.go` - 修改分片上传和合并逻辑
3. `OpenList-Frontend-main/src/pages/home/uploads/form.ts` - 前端计算和发送 CRC32
4. `OpenList-Frontend-main/package.json` - 可能需要添加 crc-32 依赖（可选）

## 风险与缓解
- **前端 CRC32 计算性能**：计算每个分片的 CRC32 可能增加前端 CPU 使用，但分片数量有限，影响较小。可使用 WebWorker 异步计算。
- **后端 CRC32 计算增加延迟**：每个分片上传增加一次哈希计算，但 CRC32 极快，影响可忽略。
- **哈希类型兼容性**：新哈希类型可能在其他模块中未处理，但仅用于校验，不影响核心功能。

## 时间安排
- 第一阶段：30分钟
- 第二阶段：1小时
- 第三阶段：1小时
- 第四阶段：1.5小时
- 第五阶段：1小时
- 总计：约5小时

## 验收标准
1. 分片上传时，如果 CRC 不匹配，服务器返回错误。
2. 合并后，服务器返回 xxh64 和 crc64 哈希值，并在控制台打印。
3. 前端正确显示远程哈希值。
4. 上传大文件时，服务器 CPU 使用率显著降低（与之前相比）。
5. 现有功能不受影响。