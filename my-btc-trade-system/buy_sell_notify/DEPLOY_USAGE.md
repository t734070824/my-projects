# Docker 部署脚本使用说明

## 脚本功能增强

`docker_deploy_with_backup.sh` 脚本现在支持**分支选择**功能，可以灵活部署不同分支的代码。

## 使用方式

### 1. 默认部署（main 分支）
```bash
bash docker_deploy_with_backup.sh
```
- 使用默认的 `main` 分支
- 适用于生产环境部署

### 2. 指定分支部署
```bash
# 部署开发分支
bash docker_deploy_with_backup.sh develop

# 部署功能分支  
bash docker_deploy_with_backup.sh feature/new-notifications

# 部署热修复分支
bash docker_deploy_with_backup.sh hotfix/urgent-fix

# 部署任意分支
bash docker_deploy_with_backup.sh your-branch-name
```

## 脚本执行流程

脚本现在包含 **7 个步骤**：

1. **步骤 1/7**: 备份现有日志文件
   - 自动备份 `./logs` 目录下的现有日志
   - 使用 `backup_logs.py` 进行智能备份

2. **步骤 2/7**: Git 代码拉取和分支切换
   - 检查当前分支状态
   - 自动切换到目标分支（如果需要）
   - 处理本地分支和远程分支的各种情况
   - 拉取最新代码

3. **步骤 3/7**: 显示当前代码状态
   - 显示当前提交信息
   - 显示未提交的更改数量

4. **步骤 4/7**: 构建 Docker 镜像
   - 基于最新代码构建镜像

5. **步骤 5/7**: 清理旧容器
   - 停止并删除现有容器

6. **步骤 6/7**: 创建目录结构
   - 确保日志目录存在

7. **步骤 7/7**: 启动新容器
   - 挂载日志目录
   - 设置自动重启策略

## 分支处理逻辑

### 本地分支存在
```bash
# 如果本地已有目标分支，直接切换
git checkout target-branch
```

### 仅远程分支存在  
```bash
# 创建本地分支并跟踪远程分支
git checkout -b target-branch origin/target-branch
```

### 分支不存在
- 脚本会显示错误信息
- 列出所有可用分支
- 安全退出，不会影响现有部署

## 使用场景

### 🚀 生产环境
```bash
# 部署稳定的 main 分支
bash docker_deploy_with_backup.sh
```

### 🧪 测试环境
```bash  
# 测试开发分支
bash docker_deploy_with_backup.sh develop
```

### 🔧 功能测试
```bash
# 测试特定功能分支
bash docker_deploy_with_backup.sh feature/notification-system
```

### 🆘 紧急修复
```bash
# 快速部署热修复
bash docker_deploy_with_backup.sh hotfix/critical-bug
```

## 安全特性

- **错误中断**: 任何步骤失败都会安全退出
- **数据保护**: 自动备份日志，防止数据丢失
- **状态验证**: 每个步骤都有状态检查
- **回滚友好**: 失败时容器状态保持一致

## 输出信息

脚本执行后会显示：
- ✅ 部署结果状态
- 📊 容器运行信息  
- 📁 日志文件位置
- 🔍 常用查看命令
- 📚 使用说明和可用分支列表

## 故障排查

### 分支不存在
```
❌ 错误: 分支 xxx 不存在（本地和远程都没有）
可用的分支: [显示分支列表]
```

### 容器启动失败
```
❌ 容器启动失败，请检查Docker状态
[显示容器错误日志]
```

### Git 操作失败
检查网络连接和 Git 仓库状态

## 新增优势

1. **🔀 灵活分支管理**: 支持任意分支部署
2. **🛡️ 智能分支处理**: 自动处理本地/远程分支情况  
3. **📈 状态可见性**: 详细显示代码和部署状态
4. **⚡ 快速切换**: 开发/测试/生产环境快速切换
5. **🔒 安全可靠**: 完整的错误处理和状态验证

现在你可以轻松地在不同分支之间切换部署，非常适合多环境的开发和测试需求！