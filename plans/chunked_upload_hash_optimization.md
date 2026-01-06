# 分片上传哈希计算优化方案

## 问题分析
1. **性能问题**：服务器在合并分片时同时计算 MD5、SHA1、SHA256 三种哈希，导致 CPU 负载高，上传大文件时速度下降甚至超时。
2. **哈希显示问题**：服务器返回的哈希对象在前端显示为 `[object Object]`，无法直观查看。
3. **网络错误**：之前出现的第5个分片上传失败可能是由于服务器计算哈希导致处理超时。

## 优化目标
- 减少服务器哈希计算负担，提升合并速度。
- 确保哈希校验仍然有效。
- 改进前端哈希显示。

## 解决方案

### 1. 哈希算法选择
- **当前**：同时计算 MD5、SHA1、SHA256。
- **优化后**：只计算 MD5。
  - MD5 速度相对较快，且已足够用于文件完整性校验。
  - 移除 SHA1 和 SHA256 可将计算量减少约 2/3。
- **替代方案**：如果未来需要更快的哈希，可考虑 xxHash，但需要修改 `utils` 包支持。

### 2. 后端修改 (`server/handles/fsup.go`)
- 修改 `FsChunkMerge` 函数中的哈希计算部分：
  ```go
  // 原代码
  hasher := utils.NewMultiHasher([]*utils.HashType{utils.MD5, utils.SHA1, utils.SHA256})
  // 改为
  hasher := utils.NewMultiHasher([]*utils.HashType{utils.MD5})
  ```
- 添加日志输出，将计算出的 MD5 哈希打印到服务器控制台：
  ```go
  log.Printf("[ChunkMerge] File %s MD5: %s", name, hashResponse["MD5"])
  ```
- 确保响应中只包含 MD5 哈希。

### 3. 前端修改 (`OpenList-Frontend-main/src/pages/home/uploads/form.ts`)
- 改进远程哈希的显示：
  ```typescript
  if (remoteHash) {
    // 如果 remoteHash 是对象，转换为字符串
    const hashStr = typeof remoteHash === 'object' ? JSON.stringify(remoteHash) : remoteHash;
    console.log(`[Chunked Upload] Remote file hash: ${hashStr}`);
  }
  ```
- 可选：添加本地哈希与远程哈希的比对逻辑，如果不匹配则报错。

### 4. 性能影响评估
- 只计算 MD5 相比计算三种哈希，CPU 使用率预计降低 60-70%。
- 对于 5.5 GB 文件，MD5 计算时间约 2-5 秒（取决于 CPU 性能），在可接受范围内。
- 减少哈希计算可能降低服务器负载，避免上传超时。

### 5. 实施步骤
1. 切换到 Code 模式修改后端代码。
2. 构建并测试后端。
3. 修改前端代码（如果需要）。
4. 重新构建前端。
5. 整体测试分片上传功能，验证哈希显示和性能。

### 6. 回退方案
如果只计算 MD5 仍导致性能问题，可考虑：
- 完全禁用服务器端哈希计算（仅依赖前端哈希）。
- 使用更快的哈希算法（如 CRC32），但需要评估碰撞风险。

## 预期结果
- 服务器合并分片时 CPU 使用率显著下降。
- 前端控制台正确显示远程哈希值。
- 分片上传成功率提高，避免因超时导致的连接重置。