# 分片上传功能改进计划

## 问题描述
1. **分片大小调整不生效** - 已通过修改 `internal/bootstrap/data/setting.go` 将 `chunked_upload_chunk_size` 设置为 `PUBLIC` 解决。
2. **速度显示不实时** - 当前分片上传只在每个分片完成后计算速度，需要实时显示上传速度和平均速度。
3. **缺少hash验证** - 需要在前端计算本地文件hash并在控制台打印，后端计算远程文件hash并返回。

## 修改方案

### 前端修改 (`OpenList-Frontend-main/src/pages/home/uploads/form.ts`)
1. **添加本地文件hash计算**
   - 使用现有的 `calculateHash` 函数计算 MD5、SHA1、SHA256
   - 异步计算，不阻塞上传流程
   - 在控制台打印本地hash值

2. **实时速度监控**
   - 为每个分片上传添加 `onUploadProgress` 回调
   - 计算瞬时速度（基于最近500ms的数据量变化）
   - 计算平均速度（总上传数据量 / 总时间）
   - 更新 `setUpload("speed", instantSpeed)` 显示实时速度
   - 在控制台同时打印瞬时速度和平均速度

3. **进度计算优化**
   - 基于每个分片的上传进度计算整体进度
   - 保留5%的进度用于合并阶段

4. **远程hash获取**
   - 修改合并请求的响应处理，检查是否有 `hash` 字段
   - 在控制台打印远程文件hash

### 后端修改 (`server/handles/fsup.go`)
1. **修改 `FsChunkMerge` 函数**
   - 在合并文件后计算合并后文件的hash（MD5、SHA1、SHA256）
   - 将hash值包含在响应中返回给前端
   - 确保响应格式兼容现有API

## 具体实现步骤

### 前端代码修改要点
```typescript
// 1. 添加hash计算
const hashPromise = calculateHash(file).then(({ md5, sha1, sha256 }) => {
  console.log(`[Chunked Upload] Local file hash - MD5: ${md5}, SHA1: ${sha1}, SHA256: ${sha256}`)
  return { md5, sha1, sha256 }
})

// 2. 在分片上传循环中添加onUploadProgress
onUploadProgress: (progressEvent) => {
  if (progressEvent.total) {
    // 更新总上传字节数
    totalUploadedBytes = i * chunkSize + progressEvent.loaded
    const now = Date.now()
    const duration = (now - lastTime) / 1000
    if (duration > 0.5) {
      const loadedDiff = totalUploadedBytes - lastLoaded
      instantSpeed = loadedDiff / duration
      averageSpeed = totalUploadedBytes / ((now - startTime) / 1000)
      setUpload("speed", instantSpeed)
      console.log(`[Chunked Upload] Instant: ${(instantSpeed / 1024 / 1024).toFixed(2)} MB/s, Average: ${(averageSpeed / 1024 / 1024).toFixed(2)} MB/s`)
      lastTime = now
      lastLoaded = totalUploadedBytes
    }
    // 更新进度
    const chunkProgress = (progressEvent.loaded / progressEvent.total) * (chunkSize / file.size) * 95
    const overallProgress = (i / totalChunks) * 95 + chunkProgress
    setUpload("progress", overallProgress)
  }
}

// 3. 处理合并响应
if (mergeResp.code === 200) {
  const remoteHash = mergeResp.hash
  if (remoteHash) {
    console.log(`[Chunked Upload] Remote file hash: ${remoteHash}`)
  }
}
```

### 后端代码修改要点
```go
// 在FsChunkMerge函数中，合并文件后计算hash
func FsChunkMerge(c *gin.Context) {
  // ... 现有合并逻辑 ...
  
  // 合并文件后，计算文件hash
  fileHash, err := calculateFileHash(finalFilePath)
  if err == nil {
    // 将hash添加到响应中
    resp["hash"] = fileHash
  }
  
  c.JSON(200, resp)
}
```

## 测试验证
1. 使用大文件进行分片上传测试
2. 观察控制台输出：
   - 本地文件hash打印
   - 实时速度和平均速度显示
   - 远程文件hash打印
3. 验证分片大小设置是否生效
4. 验证上传进度显示是否平滑

## 风险与注意事项
1. 前端hash计算可能影响性能，使用异步计算避免阻塞
2. 实时速度计算频率不宜过高，避免性能问题
3. 后端hash计算可能增加合并时间，考虑异步计算或可选
4. 确保API向后兼容，不影响现有功能

## 后续优化建议
1. 在前端界面显示平均速度
2. 添加hash验证失败的处理逻辑
3. 提供速度图表显示
4. 支持暂停/恢复分片上传