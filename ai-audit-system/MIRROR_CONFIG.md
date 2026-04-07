# 国内镜像加速配置说明

## 已配置的镜像源

### 1. pip 镜像源 (backend)
- **镜像地址**: https://mirrors.aliyun.com/pypi/simple/
- **配置文件**: `backend/Dockerfile`
- **备用镜像**:
  - 清华: https://pypi.tuna.tsinghua.edu.cn/simple
  - 豆瓣: http://pypi.douban.com/simple/
  - 腾讯云: https://mirrors.cloud.tencent.com/pypi/simple

### 2. npm 镜像源 (frontend)
- **镜像地址**: https://registry.npmmirror.com (淘宝镜像)
- **配置文件**: `frontend/Dockerfile`

### 3. apt 镜像源 (Debian)
- **镜像地址**: mirrors.aliyun.com
- **配置文件**: `backend/Dockerfile`

## Docker Desktop 镜像加速 (推荐)

### 配置方法
1. 打开 Docker Desktop → Settings → Docker Engine
2. 添加以下 registry-mirrors:

```json
{
  "registry-mirrors": [
    "https://docker.1panel.live",
    "https://hub.rat.dev",
    "https://docker.m.daocloud.io",
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.nju.edu.cn",
    "https://ccr.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

3. 点击 Apply & Restart

## 构建加速命令

### 使用默认配置（已含国内镜像）
```bash
./start.sh
```

### 手动构建（强制不使用缓存）
```bash
# 清理旧镜像
docker compose down
docker compose build --no-cache

# 启动服务
docker compose up -d
```

### 使用 Docker Buildx 加速构建
```bash
# 创建 buildx 构建器
docker buildx create --name mybuilder --use
docker buildx inspect --bootstrap

# 使用 buildx 构建
docker buildx build --platform linux/amd64 -t ai-audit-backend:latest ./backend
```

## 临时使用国内镜像（不修改配置）

### pip 临时镜像
```bash
pip install -i https://mirrors.aliyun.com/pypi/simple/ <package>
```

### npm 临时镜像
```bash
npm install --registry=https://registry.npmmirror.com
```

### Docker 临时镜像
```bash
docker pull docker.1panel.live/library/postgres:15-alpine
```

## 验证镜像源是否生效

### pip 镜像验证
```bash
docker compose exec backend pip config list
# 应显示: global.index-url='https://mirrors.aliyun.com/pypi/simple/'
```

### npm 镜像验证
```bash
docker compose exec frontend npm config get registry
# 应显示: https://registry.npmmirror.com
```
